'use strict';
/**
 * fix_query_display_style — 清除查询条件上**用户未点名**的展示样式字段
 *
 * 背景（事故）：CLI 曾在保存查询条件时**无条件注入** `advancedSearchType='openCondition'`，
 * 把报表页查询区从「默认样式（右上角搜索图标）」改成「展开条件」——用户从未要求，
 * 属于擅自改动**展示格式**。后端判据见 `SheetServiceImpl`：
 *   取第一条高级搜索条件的 advancedSearchType，=='openCondition' → isOpenCondition=true。
 * 详见 `references/query-condition-api-guide.md` §2.1.8。
 *
 * 本脚本做两件事（都是最小侵入、只动点名项）：
 *   1) 把条件上的 `advancedSearchType` 清空（省略该键即落 NULL，实测有效）；
 *   2) 按 `--delete-id` **显式**删除误插入的重复条件行（用于修复"不带 id 保存 → 新增"的误操作）。
 *
 * 用法：
 *   node fix_query_display_style.js --report-id <id> --app-id <appId>                     # dry-run 打印计划
 *   node fix_query_display_style.js --report-id <id> --app-id <appId> --apply             # 执行
 *   node fix_query_display_style.js --report-id <id> --app-id <appId> \
 *        --delete-id 1314996798765645918 --apply                                          # 先删误插入行再清理
 *   node fix_query_display_style.js --report-id <id> --app-id <appId> --id <itemId> ...   # 只处理指定条件
 *
 * 安全闸：
 *   - 默认 dry-run；必须显式 --apply 才落库。
 *   - **删除只认 --delete-id 明确列出的 id**，绝不自动推断删除。
 *   - 更新一律带 `id` 原地更新（不带 id 会变成新增 → 重复条件！）。
 *   - 落库后回读校验，未清干净则 exit 1。
 */

const fs = require('fs');
const https = require('https');
const { resolveE10Host } = require('./resolve_e10_host');

function parseArgs(argv) {
  const o = { _: [], 'delete-id': [], id: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const key = a.slice(2);
      const multi = key === 'delete-id' || key === 'id';
      if (!multi && (i + 1 >= argv.length || String(argv[i + 1]).startsWith('--'))) o[key] = true;
      else if (multi) o[key].push(argv[++i]);
      else o[key] = argv[++i];
    } else o._.push(a);
  }
  return o;
}

function buildMultipart(fieldsObj) {
  const boundary = `----EdcFixStyle${Date.now()}`;
  const parts = [];
  for (const [k, v] of Object.entries(fieldsObj)) {
    parts.push(`--${boundary}\r\nContent-Disposition: form-data; name="${k}"\r\n\r\n${v}\r\n`);
  }
  parts.push(`--${boundary}--\r\n`);
  return { body: Buffer.from(parts.join(''), 'utf8'), contentType: `multipart/form-data; boundary=${boundary}` };
}

function request(method, url, body, headers) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const r = https.request(
      { method, hostname: u.hostname, port: u.port || 443, path: u.pathname + u.search, headers },
      (res) => {
        const chunks = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () => {
          const text = Buffer.concat(chunks).toString('utf8');
          let json = null;
          try { json = JSON.parse(text); } catch (e) { /* 非 JSON */ }
          resolve({ status: res.statusCode, json, text });
        });
      }
    );
    r.on('error', reject);
    if (body) r.write(body);
    r.end();
  });
}

function eteamsId() {
  return require('./eb_auth.js').eteamsId();
}

function headersFor(host, reportId, appId) {
  const et = eteamsId();
  return {
    eteamsid: et,
    ebBusinessId: appId,
    ebbusinessid: appId,
    Cookie: `langType=zh_CN; LOGIN_TYPE=pc_account; ETEAMSID=${et}`,
    Accept: 'application/json',
    'User-Agent': 'Mozilla/5.0 AgentType=WorkBuddy,IsAgent=true',
    Referer: `${host}/sp/edc/report/designer/${reportId}`,
  };
}

async function fetchItems(base, host, reportId, appId) {
  const { body, contentType } = buildMultipart({ reportId: String(reportId), query: '{}' });
  const res = await request('POST', `${host}/api/bs/edc/report/getQueryItemNew`, body, {
    ...base, 'Content-Type': contentType, 'Content-Length': body.length,
  });
  if (res.json?.code !== 200) throw new Error(`getQueryItemNew 失败 code=${res.json?.code} http=${res.status}`);
  return ((res.json || {}).data || {}).list || [];
}

async function saveItem(base, host, reportId, item) {
  const { body, contentType } = buildMultipart({ reportId: String(reportId), queryItems: JSON.stringify(item) });
  return request('POST', `${host}/api/bs/edc/report/saveQueryItem`, body, {
    ...base, 'Content-Type': contentType, 'Content-Length': body.length,
  });
}

async function deleteItem(base, host, appId, id) {
  return request('GET', `${host}/api/bs/edc/report/delQueryItem?id=${encodeURIComponent(id)}`, null, base);
}

/** 剥离派生/只读键；保留 id 以便原地更新 */
function toSavePayload(row) {
  const out = {};
  for (const [k, v] of Object.entries(row)) {
    if (/_Str$/.test(k)) continue;
    if (k === 'handleDefaultValue' || k === 'updateTime') continue;
    if (k === 'advancedSearchType') continue; // ← 本脚本要清掉的就是它
    out[k] = v;
  }
  return out;
}

(async () => {
  const args = parseArgs(process.argv.slice(2));
  const reportId = args['report-id'] || args.reportId;
  const appId = args['app-id'] || args.appId;
  if (!reportId || !appId) {
    console.error('Usage: fix_query_display_style.js --report-id <id> --app-id <appId> [--id <itemId>...] [--delete-id <itemId>...] [--apply]');
    process.exit(2);
  }
  const host = resolveE10Host({ host: args.host });
  const base = headersFor(host, reportId, appId);

  const before = await fetchItems(base, host, reportId, appId);
  const byId = new Map(before.map((x) => [String(x.id), x]));

  const onlyIds = (args.id || []).map(String);
  const deleteIds = (args['delete-id'] || []).map(String);

  // 待清理 = advancedSearchType 非空的条件（可用 --id 收窄）
  const toClear = before.filter(
    (x) => String(x.advancedSearchType || '').trim() !== '' && (onlyIds.length === 0 || onlyIds.includes(String(x.id)))
  );

  // 待删除 = 显式列出的 id
  const missing = deleteIds.filter((d) => !byId.has(d));
  const toDelete = deleteIds.filter((d) => byId.has(d));

  const plan = {
    reportId,
    apply: !!args.apply,
    totalBefore: before.length,
    willDelete: toDelete.map((d) => ({ id: d, text: byId.get(d).text, showOrder: byId.get(d).showOrder })),
    willClearAdvancedSearchType: toClear.map((x) => ({
      id: x.id, text: x.text, showOrder: x.showOrder, was: x.advancedSearchType,
    })),
    unknownDeleteIds: missing,
    totalAfterExpected: before.length - toDelete.length,
  };
  console.log(JSON.stringify(plan, null, 2));

  if (!args.apply) {
    console.log('\n(dry-run) 未加 --apply，未写任何数据。');
    process.exit(0);
  }

  // 1) 显式删除
  for (const d of toDelete) {
    const r = await deleteItem(base, host, appId, d);
    console.log(`DELETE id=${d} text=${byId.get(d).text} -> http=${r.status} code=${r.json?.code} ${JSON.stringify(r.json?.msg || '')}`);
    if (r.json && r.json.code !== 200) { console.error('删除失败，中止'); process.exit(2); }
  }

  // 2) 原地清 advancedSearchType
  for (const x of toClear) {
    const payload = toSavePayload(x);
    if (!payload.id) { console.error(`条件 ${x.text} 缺 id，拒绝保存（会变成新增）`); process.exit(2); }
    const r = await saveItem(base, host, reportId, payload);
    const ok = r.json?.code === 200;
    console.log(`CLEAR id=${x.id} text=${x.text} advancedSearchType ${JSON.stringify(x.advancedSearchType)} -> (空) : ${ok ? 'OK' : 'FAIL code=' + r.json?.code}`);
    if (!ok) { console.error('保存失败，中止'); process.exit(2); }
  }

  // 3) 回读校验
  const after = await fetchItems(base, host, reportId, appId);
  const stale = after.filter((x) => String(x.advancedSearchType || '').trim() !== '');
  const result = {
    totalAfter: after.length,
    stillHasAdvancedSearchType: stale.map((x) => ({ id: x.id, text: x.text, advancedSearchType: x.advancedSearchType })),
    rows: after.map((x) => ({ id: x.id, text: x.text, showOrder: x.showOrder, queryType: x.queryType, advancedSearchType: x.advancedSearchType ?? null })),
  };
  console.log('\n== 回读校验 ==\n' + JSON.stringify(result, null, 2));
  process.exit(stale.length === 0 ? 0 : 1);
})().catch((e) => { console.error('FATAL ' + e.message); process.exit(1); });
