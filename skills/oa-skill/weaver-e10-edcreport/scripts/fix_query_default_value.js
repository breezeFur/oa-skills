'use strict';
/**
 * fix_query_default_value — 补齐查询条件缺失的「默认值三件套」
 *
 * 背景（2026-09-14 事故）：
 *   用 API 建查询条件时若**只写 displayType/conditions**、不写 `defaultValueType`
 *   + `defaultValue`，设计器「编辑查询条件」弹窗会坏掉：
 *     · 「默认值类型」显示为 **请选择**
 *     · 「默认值」区把**所有**控件变体同时渲染（请输入/开始-结束日期/选择日期时间/
 *       请选择/选择日期/选择月份/选择年份…）→ 面板被顶高
 *     · 位于其后的「日期类型 / 显示位置 / 条件必填 / 查询条件」被挤出可视区，
 *       看起来像"整段消失"
 *   即用户看到的现象："查询条件样式被改了"。
 *
 * 数据模型（实测参照报表 1314938962594906121，人工配置的权威形态）：
 *   defaultValueType : 'default'（常规） | 'custom'（自定义）
 *   type1DefaultValue: 「常规」模式下保存的值
 *   type2DefaultValue: 「自定义」模式下保存的值
 *   defaultValue     : **当前生效**的值（= 对应模式那份）
 *   handleDefaultValue: 平台解析后的实际值（如 {yearmonth:-0} → "2026-09"）
 *   均为 **JSON 字符串**（不是对象/数组本身）。
 *
 *   设计器「新建条件」模板（前端 bundle `route_ReportDesigner.js` 实证）：
 *     defaultValue:["",""], defaultValueType:"default", dateType:"ymd",
 *     browserType:[{module:hrm,type:resource,id:2227541039890088895,name:人员}],
 *     filterParam:{showType:"tile",optionTile:{}}
 *
 * 用法：
 *   node fix_query_default_value.js --report-id <id> --app-id <appId>            # dry-run
 *   node fix_query_default_value.js --report-id <id> --app-id <appId> --apply
 *   node fix_query_default_value.js --report-id <id> --app-id <appId> \
 *        --set '年月=custom:["{yearmonth:-0}",""]' --apply                        # 单条指定
 *   node fix_query_default_value.js --report-id <id> --app-id <appId> \
 *        --set '部门=default:[[],""]' --id <itemId> --apply                      # 只处理某条
 *
 *   --set 语法：<条件文本|条件id>=<default|custom>:<JSON字符串值>
 *
 * 附加对齐（可选）：
 *   --show-order <n>   把处理到的条件的 `showOrder` 统一写成 n（设计器「新建条件」模板值 = 0；
 *                      人工配置的条件通常就是 0 = 未设。API 建条件时若自行填 1,2,3… 会与
 *                      参照报表在弹窗「排序」框上出现可见差异）
 *   --all              连同「三件套已配好」的条件一起处理（用于只做 --show-order 对齐）
 *
 * 安全闸：
 *   - 默认 dry-run；必须 --apply 才落库
 *   - 更新一律**带 id 原地更新**（不带 id 会变成新增 → 重复条件，坑见 pitfalls QUERY-6）
 *   - 只补**缺失**的键；已有非空 `defaultValueType` 的条件默认不动（除非 --force / --set 点名）
 *   - 落库后回读校验，仍有缺失则 exit 1
 */

const https = require('https');
const { resolveE10Host } = require('./resolve_e10_host');

function parseArgs(argv) {
  const o = { _: [], set: [], id: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const key = a.slice(2);
      const multi = key === 'set' || key === 'id';
      if (multi) o[key].push(argv[++i]);
      else if (i + 1 >= argv.length || String(argv[i + 1]).startsWith('--')) o[key] = true;
      else o[key] = argv[++i];
    } else o._.push(a);
  }
  return o;
}

function buildMultipart(fieldsObj) {
  const boundary = `----EdcFixDefVal${Date.now()}`;
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

function eteamsId() { return require('./eb_auth.js').eteamsId(); }

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

async function fetchItems(base, host, reportId) {
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

/** 剥离派生/只读键；保留 id 以便原地更新；保留既有三件套（只覆盖要点名的键） */
function toSavePayload(row) {
  const out = {};
  for (const [k, v] of Object.entries(row)) {
    if (/_Str$/.test(k)) continue;
    if (k === 'updateTime' || k === 'conditionShowInfo') continue;
    out[k] = v;
  }
  return out;
}

/** 解析 --set 项：'年月=custom:["{yearmonth:-0}",""]' */
function parseSet(expr) {
  const eq = expr.indexOf('=');
  if (eq < 0) throw new Error(`--set 语法错误（缺 =）：${expr}`);
  const key = expr.slice(0, eq).trim();
  const rest = expr.slice(eq + 1);
  const colon = rest.indexOf(':');
  if (colon < 0) throw new Error(`--set 语法错误（缺 :）：${expr}`);
  const mode = rest.slice(0, colon).trim();
  const value = rest.slice(colon + 1).trim();
  if (mode !== 'default' && mode !== 'custom') throw new Error(`--set 模式只能是 default|custom：${expr}`);
  JSON.parse(value); // 必须是合法 JSON（字符串形式）
  return { key, mode, value };
}

/** 三件套赋值：mode 决定值落在 type1(常规)/type2(自定义)，defaultValue = 当前生效值 */
function applyTriplet(item, mode, value) {
  const before = {
    defaultValueType: item.defaultValueType ?? null,
    defaultValue: item.defaultValue ?? null,
    type1DefaultValue: item.type1DefaultValue ?? null,
    type2DefaultValue: item.type2DefaultValue ?? null,
    handleDefaultValue: item.handleDefaultValue ?? null,
  };
  item.defaultValueType = mode;
  item.defaultValue = value;
  if (mode === 'custom') {
    item.type2DefaultValue = value;
    if (item.type1DefaultValue == null) item.type1DefaultValue = '';
  } else {
    item.type1DefaultValue = value;
    if (item.type2DefaultValue == null) item.type2DefaultValue = '';
  }
  item.handleDefaultValue = value;
  return before;
}

(async () => {
  const args = parseArgs(process.argv.slice(2));
  const reportId = args['report-id'] || args.reportId;
  const appId = args['app-id'] || args.appId;
  if (!reportId || !appId) {
    console.error(
      'Usage: fix_query_default_value.js --report-id <id> --app-id <appId> ' +
      '[--set "<文本|id>=<default|custom>:<JSON值>"]... [--id <itemId>...] [--force] [--apply]'
    );
    process.exit(2);
  }
  const host = resolveE10Host({ host: args.host });
  const base = headersFor(host, reportId, appId);

  const sets = (args.set || []).map(parseSet);
  const onlyIds = (args.id || []).map(String);
  const wantOrder = args['show-order'] != null && args['show-order'] !== true ? Number(args['show-order']) : null;
  const all = !!args.all;

  const before = await fetchItems(base, host, reportId);
  const plan = [];
  const targets = [];

  for (const it of before) {
    if (onlyIds.length && !onlyIds.includes(String(it.id))) continue;
    const hit = sets.find((s) => s.key === String(it.id) || s.key === String(it.text).trim());
    const missing = !it.defaultValueType || it.defaultValueType === '';
    const orderDiff = wantOrder != null && Number(it.showOrder) !== wantOrder;
    if (!hit && !missing && !all) continue;               // 已配好且没被点名 → 不动
    if (!hit && !missing && all && !orderDiff) continue;  // --all 且无任何要改 → 跳过
    const mode = hit ? hit.mode : 'default';
    const value = hit ? hit.value : (it.defaultValue || '["",""]');
    plan.push({
      id: it.id, text: it.text,
      reason: hit ? 'set' : (missing ? 'missing' : 'order'),
      before: {
        defaultValueType: it.defaultValueType ?? null,
        defaultValue: it.defaultValue ?? null,
        type1DefaultValue: it.type1DefaultValue ?? null,
        type2DefaultValue: it.type2DefaultValue ?? null,
        showOrder: it.showOrder ?? null,
      },
      after: { defaultValueType: missing || hit ? mode : it.defaultValueType, defaultValue: missing || hit ? value : it.defaultValue, showOrder: wantOrder != null ? wantOrder : it.showOrder },
    });
    targets.push({ it, mode, value, fixTriplet: !!(hit || missing) });
  }

  console.log(JSON.stringify({
    reportId, appId, host, apply: !!args.apply,
    totalBefore: before.length, willFix: plan.length, plan,
  }, null, 2));

  if (!plan.length) { console.log('\n无需修复（所有条件的三件套均已存在）。'); process.exit(0); }
  if (!args.apply) { console.log('\n(dry-run) 未加 --apply，未写任何数据。'); process.exit(0); }

  for (const t of targets) {
    const payload = toSavePayload(t.it);
    if (!payload.id) { console.error(`条件「${t.it.text}」缺 id，拒绝保存（会变成新增）`); process.exit(2); }
    if (t.fixTriplet) applyTriplet(payload, t.mode, t.value);
    if (wantOrder != null) payload.showOrder = wantOrder;
    const r = await saveItem(base, host, reportId, payload);
    const ok = r.json?.code === 200;
    console.log(`FIX id=${t.it.id} 「${t.it.text}」` +
      (t.fixTriplet ? ` defaultValueType=${t.mode} defaultValue=${t.value}` : '') +
      (wantOrder != null ? ` showOrder=${wantOrder}` : '') +
      ` -> ${ok ? 'OK' : 'FAIL code=' + r.json?.code + ' ' + (r.json?.msg || '')}`);
    if (!ok) { console.error('保存失败，中止'); process.exit(2); }
  }

  // 回读校验
  const after = await fetchItems(base, host, reportId);
  const bad = after.filter((x) => !x.defaultValueType || String(x.defaultValueType) === '');
  const orderBad = wantOrder == null ? [] : after.filter((x) => Number(x.showOrder) !== wantOrder);
  console.log('\n== 回读校验 ==\n' + JSON.stringify({
    totalAfter: after.length,
    stillMissingDefaultValueType: bad.map((x) => ({ id: x.id, text: x.text })),
    stillShowOrderMismatch: orderBad.map((x) => ({ id: x.id, text: x.text, showOrder: x.showOrder })),
    rows: after.map((x) => ({
      text: x.text, showOrder: x.showOrder,
      defaultValueType: x.defaultValueType ?? null,
      defaultValue: x.defaultValue ?? null,
      type1DefaultValue: x.type1DefaultValue ?? null,
      type2DefaultValue: x.type2DefaultValue ?? null,
      handleDefaultValue: x.handleDefaultValue ?? null,
    })),
  }, null, 2));
  process.exit(bad.length === 0 && orderBad.length === 0 ? 0 : 1);
})().catch((e) => { console.error('FATAL ' + e.message); process.exit(1); });
