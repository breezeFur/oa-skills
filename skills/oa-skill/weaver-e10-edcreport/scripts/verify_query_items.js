'use strict';
/**
 * verify_query_items —— 查询条件**合规体检**（只读）+ 可选 --fix
 *
 * 把 2026-09-14 两次事故（「查询条件样式被改」「弹窗默认值区炸开」）的全部判据
 * 固化成一条命令，动手前 / 落库后都能一键自检。
 *
 * 检查项（每条条件）：
 *   Q1 queryType 是数组短码           → 否则 FAIL（设计器「显示方式」不勾选，QUERY-1）
 *   Q2 advancedSearchType 为空        → 否则 FAIL（未点名的展示样式残留，报表页被改成「展开条件」，QUERY-5）
 *   Q3 defaultValueType 有值          → 否则 FAIL（三件套缺失 → 弹窗默认值区炸开，QUERY-7）
 *   Q4 defaultValue 有值              → 否则 WARN
 *   Q5 type1/type2DefaultValue 随模式 → 否则 WARN
 *   Q6 id 存在 + asNameIndex 唯一     → 否则 FAIL（重复条件，QUERY-6）
 *   Q7 displayType=browser 时 browserType 非空 → 否则 FAIL（关联类型点不开，QUERY-3）
 *   Q8 filterParam.required / showType 在位 → 否则 WARN（弹窗后段字段）
 *   Q9 showOrder 与 asNameIndex 是否一致 → INFO（人工配置通常为 0）
 *   Q10 报表级 queryType 是否混杂     → WARN（可能被 updateQueryType 批量覆盖过，QUERY-2）
 *
 * 用法：
 *   node verify_query_items.js --report-id <id> --app-id <appId> [--json]      # 只读体检
 *   node verify_query_items.js --report-id <id> --app-id <appId> --fix         # 安全修复（幂等）
 *
 * exit: 0 = 全过（可能有 WARN/INFO）；1 = 有 FAIL；2 = 参数/接口错误
 *
 * --fix 只做三件**幂等安全**的事，绝不新增/删除条件：
 *   ① 清空 advancedSearchType；② 补 defaultValueType 三件套；③ queryType 规范为数组短码。
 *   （要删重复条件 → 用 fix query-style --delete-id <明确 id>）
 */

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
  const boundary = `----EdcVerifyQuery${Date.now()}`;
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

function headersFor(host, reportId, appId) {
  const et = require('./eb_auth.js').eteamsId();
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

function isArrShortCode(v) {
  if (typeof v !== 'string') return false;
  const s = v.trim();
  if (!s.startsWith('[')) return false;
  try { return Array.isArray(JSON.parse(s)); } catch (e) { return false; }
}

function normShortCode(v) {
  const s = String(v || '').trim().toLowerCase();
  if (!s) return null;
  if (s.includes('filter') && !s.includes('advance')) return '["filter"]';
  return '["advance"]';
}

/** 剥离派生/只读键；保留 id 以便原地更新 */
function toSavePayload(row) {
  const out = {};
  for (const [k, v] of Object.entries(row)) {
    if (/_Str$/.test(k)) continue;
    if (k === 'handleDefaultValue' || k === 'updateTime' || k === 'conditionShowInfo') continue;
    out[k] = v;
  }
  return out;
}

/** 单条体检 → {fails[], warns[], infos[], fixNeeded} */
function inspect(it) {
  const fails = [];
  const warns = [];
  const infos = [];
  let fixNeeded = false;

  // Q1 queryType 数组短码
  if (!isArrShortCode(it.queryType)) {
    fails.push(`Q1 queryType 不是数组短码（现值 ${JSON.stringify(it.queryType ?? null)}）→ 设计器「显示方式」不会勾选`);
    fixNeeded = true;
  }
  // Q2 advancedSearchType 必须为空
  if (String(it.advancedSearchType || '').trim() !== '') {
    fails.push(`Q2 advancedSearchType=${JSON.stringify(it.advancedSearchType)} 非空 → 报表页查询区被改成「展开条件」（未点名的展示样式）`);
    fixNeeded = true;
  }
  // Q3/Q4/Q5 默认值三件套
  if (!it.defaultValueType || String(it.defaultValueType) === '') {
    fails.push('Q3 defaultValueType 缺失 → 设计器弹窗「默认值类型」=请选择，默认值区把全部控件变体炸开（QUERY-7）');
    fixNeeded = true;
  }
  if (it.defaultValue == null || String(it.defaultValue) === '') {
    warns.push('Q4 defaultValue 为空（建议写 JSON 字符串，如 "[[],\\"\\"]" 或 "[\\"{\\"yearmonth:-0}\\",\\"\\"]"）');
    fixNeeded = true;
  }
  if (it.defaultValueType === 'custom' && (it.type2DefaultValue == null || String(it.type2DefaultValue) === '')) {
    warns.push('Q5 模式=custom 但 type2DefaultValue 缺失（自定义模式对应值）');
    fixNeeded = true;
  }
  if (it.defaultValueType === 'default' && (it.type1DefaultValue == null)) {
    warns.push('Q5 模式=default 但 type1DefaultValue 缺失（常规模式对应值）');
    fixNeeded = true;
  }
  // Q6 id / asNameIndex
  if (!it.id) fails.push('Q6 缺 id → 保存会变成「新增」（重复条件，QUERY-6）');
  if (!it.asNameIndex || Number(it.asNameIndex) <= 0) {
    warns.push(`Q6 asNameIndex=${JSON.stringify(it.asNameIndex ?? null)}（应 >0 且唯一）`);
  }
  // Q7 browser 富对象
  if (String(it.displayType) === 'browser') {
    const bt = Array.isArray(it.browserType) ? it.browserType : [];
    const btOk = bt.length > 0 && bt.some((x) => x && (x.id || x.name));
    if (!btOk) {
      fails.push('Q7 displayType=browser 但 browserType 富对象为空 → 设计器「关联类型」为空 / 条件点不开（QUERY-3）');
      fixNeeded = true;
    } else if (!String(it.browserTypeStr || '').trim()) {
      warns.push('Q7 browserType 有富对象但 browserTypeStr 为空（应同步写入）');
      fixNeeded = true;
    }
  }
  // Q8 filterParam
  const fp = it.filterParam;
  if (!fp || typeof fp !== 'object') {
    warns.push('Q8 filterParam 缺失 → 「显示位置 / 条件必填」等弹窗后段字段可能为空');
  } else {
    if (fp.required === undefined || fp.required === null) warns.push('Q8 filterParam.required 缺失');
    if (fp.showType === undefined || fp.showType === null) warns.push('Q8 filterParam.showType 缺失');
  }
  // Q9 showOrder（信息性）
  if (it.showOrder !== undefined && it.showOrder !== null && Number(it.showOrder) !== 0) {
    infos.push(`Q9 showOrder=${it.showOrder}（设计器模板值为 0；人工配置通常也是 0）`);
  }
  return { fails, warns, infos, fixNeeded };
}

(async () => {
  const args = parseArgs(process.argv.slice(2));
  const reportId = args['report-id'] || args.reportId || args._[0];
  const appId = args['app-id'] || args.appId || args._[1];
  if (!reportId || !appId) {
    console.error('Usage: verify_query_items.js --report-id <id> --app-id <appId> [--json] [--fix]');
    process.exit(2);
  }
  const host = resolveE10Host({ host: args.host });
  const base = headersFor(host, reportId, appId);

  const before = await fetchItems(base, host, reportId);
  const allReportIds = before.map((x) => String(x.id));
  const idxSeen = new Map();
  for (const it of before) {
    const k = String(it.asNameIndex);
    idxSeen.set(k, (idxSeen.get(k) || 0) + 1);
  }

  // 报表级：queryType 是否混杂
  const qtSet = new Set(before.map((x) => String(x.queryType || '')));
  const mixed = qtSet.size > 1;

  const rows = before.map((it) => {
    const r = inspect(it);
    // Q6 唯一性补充
    if (idxSeen.get(String(it.asNameIndex)) > 1) {
      r.fails.push(`Q6 asNameIndex=${it.asNameIndex} 重复出现 ${idxSeen.get(String(it.asNameIndex))} 次 → 疑似重复条件`);
    }
    return { id: it.id, text: it.text, asNameIndex: it.asNameIndex, queryType: it.queryType, ...r };
  });

  const failN = rows.reduce((n, r) => n + r.fails.length, 0);
  const warnN = rows.reduce((n, r) => n + r.warns.length, 0);

  const report = {
    reportId,
    total: before.length,
    fail: failN,
    warn: warnN,
    mixedQueryType: mixed ? [...qtSet] : null,
    ok: failN === 0,
    rows,
  };

  if (args.json) {
    console.log(JSON.stringify(report, null, 2));
  } else {
    console.log(`\n=== 查询条件体检 · 报表 ${reportId} ===`);
    console.log(`条件数 ${before.length} | FAIL ${failN} | WARN ${warnN}`);
    if (mixed) {
      console.log(`  ⚠ 报表级 queryType 混杂：${[...qtSet].map((s) => JSON.stringify(s)).join(' / ')} → 曾被 updateQueryType 批量覆盖过？（QUERY-2）`);
    }
    for (const r of rows) {
      const tag = r.fails.length ? 'FAIL' : r.warns.length ? 'WARN' : 'OK  ';
      console.log(`\n[${tag}] #${r.asNameIndex} ${r.text}  (id=${r.id})`);
      console.log(`        queryType=${JSON.stringify(r.queryType)}`);
      for (const f of r.fails) console.log('        ✗ ' + f);
      for (const w of r.warns) console.log('        ! ' + w);
      for (const i of r.infos) console.log('        · ' + i);
    }
    if (failN === 0) console.log('\n✓ 全部条件通过合规体检');
  }

  if (!args.fix) {
    if (!args.json) console.log('\n（只读）如需自动修复安全项：加 --fix');
    process.exit(failN === 0 ? 0 : 1);
  }

  // ---- --fix：幂等安全修复 ----
  const fixes = [];
  for (const it of before) {
    const insp = inspect(it);
    if (!insp.fixNeeded) continue;
    const payload = toSavePayload(it);
    if (!payload.id) { console.error(`条件「${it.text}」缺 id，拒绝保存（会变成新增）`); process.exit(2); }
    const changes = [];
    // ① 清 advancedSearchType
    if (String(it.advancedSearchType || '').trim() !== '') { delete payload.advancedSearchType; changes.push('清 advancedSearchType'); }
    else delete payload.advancedSearchType;
    // ② 补三件套
    if (!payload.defaultValueType || String(payload.defaultValueType) === '') {
      payload.defaultValueType = 'default';
      changes.push('defaultValueType=default');
    }
    if (payload.defaultValue == null || String(payload.defaultValue) === '') {
      payload.defaultValue = payload.defaultValueType === 'custom' ? '["",""]' : '[[],""]';
      changes.push(`defaultValue=${JSON.stringify(payload.defaultValue)}`);
    }
    if (payload.type1DefaultValue == null) { payload.type1DefaultValue = payload.defaultValueType === 'default' ? payload.defaultValue : ''; changes.push('type1DefaultValue'); }
    if (payload.type2DefaultValue == null) { payload.type2DefaultValue = payload.defaultValueType === 'custom' ? payload.defaultValue : ''; changes.push('type2DefaultValue'); }
    // ③ queryType 短码化
    if (!isArrShortCode(payload.queryType)) {
      const sc = normShortCode(payload.queryType) || '["advance"]';
      payload.queryType = sc;
      changes.push(`queryType→${sc}`);
    }
    // ④ browser 富对象缺失 → 拒绝（需人工，不猜富对象）
    if (String(it.displayType) === 'browser') {
      const bt = Array.isArray(it.browserType) ? it.browserType : [];
      if (!bt.length) {
        console.log(`SKIP 「${it.text}」displayType=browser 但缺富对象 → 需人工补 browserType（见 query-condition-api-guide §2.1.2）`);
        continue;
      }
    }
    if (!changes.length) continue;
    const r = await saveItem(base, host, reportId, payload);
    const ok = r.json?.code === 200;
    fixes.push({ id: it.id, text: it.text, changes, ok, code: r.json?.code });
    console.log(`FIX id=${it.id} 「${it.text}」${changes.join(' ; ')} -> ${ok ? 'OK' : 'FAIL code=' + r.json?.code}`);
    if (!ok) { console.error('保存失败，中止'); process.exit(2); }
  }

  const after = await fetchItems(base, host, reportId);
  const recheck = after.map((it) => ({ text: it.text, ...inspect(it) }));
  const remain = recheck.filter((r) => r.fails.length);
  console.log('\n== 修复后回读校验 ==');
  console.log(JSON.stringify({
    totalAfter: after.length,
    fixed: fixes.length,
    stillFail: remain.map((r) => ({ text: r.text, fails: r.fails })),
  }, null, 2));
  process.exit(remain.length === 0 ? 0 : 1);
})().catch((e) => { console.error('FATAL ' + e.message); process.exit(1); });
