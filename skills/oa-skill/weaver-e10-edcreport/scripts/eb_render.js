'use strict';
/**
 * eb_render.js —— 渲染守卫（默认不渲染全量数据）
 *
 * 背景（本平台实测硬约束）：
 *   数据集不带过滤时约 2.4 万行；交叉表完整展开 87 列 ≈ 210 万格，
 *   而平台上限是 50,000 格（≈ 574 行 × 87 列）→ 必然 `code:555`。
 *   更糟的是平台「先算完再拒绝」：每次探测都要白烧 15~80s 才拿到 555。
 *
 * 因此本模块的规则：
 *   1. **默认直接拒绝渲染**，需要显式 EB_ALLOW_RENDER=1 才执行
 *   2. 即使允许，也强制硬超时（EB_RENDER_TIMEOUT_MS，默认 30000）
 *   3. pageRowCount 自动封顶（EB_MAX_PAGE_ROW_COUNT，默认 574 = 50000/87）
 *   4. **绝不重试**；命中 555 立即返回结论，不换参数再试
 *
 * 结论：**搭报表只要落库成功即可，不需要渲染全量数据。**
 *   验证优先用「结构回读」：getReportDevInfo.fields / dataset 元数据 / verify_field_bind.js
 *
 * 用法（模块）：
 *   const R = require('./eb_render.js');
 *   const r = await R.render(reportId, appId, { pageRowCount: 200 });
 *   if (r.skipped) console.log(r.hint);       // 默认不渲染时
 * 用法（命令行，仅诊断用）：
 *   EB_ALLOW_RENDER=1 node eb_render.js <reportId> [appId] [pageRowCount]
 */
const fs = require('fs');
const zlib = require('zlib');
const https = require('https');
const A = require('./eb_auth.js');

const ENABLED = /^(1|true|yes)$/i.test(String(process.env.EB_ALLOW_RENDER || ''));
const TIMEOUT_MS = Number(process.env.EB_RENDER_TIMEOUT_MS || 30000);
const MAX_PAGE_ROW = Number(process.env.EB_MAX_PAGE_ROW_COUNT || 574);
const CELL_LIMIT = 50000;

const AGENT = new https.Agent({ keepAlive: true, maxSockets: 2, rejectUnauthorized: false });

const DISABLED_HINT = [
  '已跳过渲染：默认不渲染全量数据（避免白等 15~80s 后只拿到 code:555）。',
  '  报表搭建只需落库成功，验证请用结构回读：',
  '    - getReportDevInfo 的 fields（单元格/字段绑定）',
  '    - verify_field_bind.js（Field 绑定校验）',
  '  确实需要看渲染规模时，显式放行：EB_ALLOW_RENDER=1（并建议同时限制 pageRowCount）',
].join('\n');

function multipart(fields) {
  const b = '----EbRender' + Math.random().toString(16).slice(2);
  const parts = [];
  for (const [k, v] of fields) {
    parts.push(`--${b}\r\nContent-Disposition: form-data; name="${k}"\r\n\r\n${v == null ? '' : String(v)}\r\n`);
  }
  parts.push(`--${b}--\r\n`);
  return { body: Buffer.from(parts.join(''), 'utf8'), ctype: `multipart/form-data; boundary=${b}` };
}

function req(method, urlStr, { headers, body, timeout = TIMEOUT_MS } = {}) {
  return new Promise((resolve, reject) => {
    const u = new URL(urlStr);
    const r = https.request(
      { method, hostname: u.hostname, port: u.port || 443, path: u.pathname + u.search,
        headers, agent: AGENT, rejectUnauthorized: false },
      (res) => {
        const chunks = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () => resolve({ status: res.statusCode, raw: Buffer.concat(chunks) }));
      }
    );
    r.setTimeout(timeout, () => r.destroy(new Error(`请求超时 ${timeout}ms（已放弃，不重试）`)));
    r.on('error', reject);
    if (body) r.write(body);
    r.end();
  });
}

function decodeJsonStr(raw) {
  const gunzip = (b) => { try { return zlib.gunzipSync(b).toString('utf8'); } catch (e) { return null; } };
  let txt = gunzip(raw);
  if (!txt) {
    try {
      const j = JSON.parse(raw.toString('utf8'));
      if (typeof j.data === 'string') {
        txt = gunzip(Buffer.from(j.data, 'base64')) || gunzip(Buffer.from(j.data, 'latin1'));
      }
    } catch (e) { /* ignore */ }
  }
  return txt;
}

/** pageRowCount 自动封顶：超过「上限/列数」就压回来，避免必然触 555 */
function capPageRowCount(n, cols = 87) {
  const safe = Math.max(1, Math.floor(CELL_LIMIT / Math.max(1, cols)));
  const want = Number(n) || safe;
  return { value: Math.min(want, MAX_PAGE_ROW, safe), capped: want > Math.min(MAX_PAGE_ROW, safe), safeMax: Math.min(MAX_PAGE_ROW, safe) };
}

/**
 * 渲染报表（默认被守卫拦截）。
 * @returns {Promise<{ok:boolean, skipped?:boolean, code?:number, msg?:string,
 *                    colCount?:number, rowCount?:number, total?:number, ms:number}>}
 */
async function render(reportId, appId, opts = {}) {
  const t0 = Date.now();
  if (!ENABLED && !opts.force) {
    return { ok: false, skipped: true, reason: 'render_disabled', hint: DISABLED_HINT, ms: Date.now() - t0 };
  }
  const cap = capPageRowCount(opts.pageRowCount);
  const base = A.baseUrl();
  const referer = `${base}/sp/edc/report/view/${reportId}`;
  const headers = {
    accept: 'application/json, text/plain, */*',
    eteamsid: A.eteamsId(),
    ebBusinessId: appId,
    ebbusinessid: appId,
    Cookie: A.cookieHeader(),
    'User-Agent': 'Mozilla/5.0 AgentType=WorkBuddy,IsAgent=true',
    Referer: referer,
  };

  const fields = [
    ['sheetId', reportId], ['dataId', ''], ['from', 'undefined'],
    ['pageFilter', JSON.stringify({ filterIsNull: true, isOverrideFilter: false })],
    ['id', reportId], ['uniqueId', reportId], ['autoPrint', 'false'], ['singlePageView', 'true'],
    ['sheetIndex', '0'], ['sheetName', 'Sheet1'], ['dynamicValue', ''], ['dynamicField', ''],
    ['realSheetIndex', '0'], ['pageNum', '1'], ['condition', opts.condition || '{}'],
    ['isMobile', 'false'], ['searchType', 'and'], ['prefetchCount', 'null'],
    ['uniqueRequestId', String(Date.now()).slice(-12)], ['scrollPage', '0'],
  ];
  const mp = multipart(fields);
  const r4 = await req('POST', `${base}/api/edc/report/view/analysis`, {
    headers: { ...headers, 'Content-Type': mp.ctype, 'content-length': mp.body.length },
    body: mp.body, timeout: opts.timeout || TIMEOUT_MS,
  });
  const j = JSON.parse(r4.raw.toString('utf8'));

  if (!(j && j.data && j.data.json)) {
    // 555 等失败：直接返回结论，不换参数重试
    return {
      ok: false, code: j && j.code, msg: j && j.msg,
      cappedPageRowCount: cap.capped ? cap.value : undefined,
      hint: j && j.code === 555
        ? `渲染超限（>${CELL_LIMIT} 单元格）。数据集行数 × 列数超限，凑一次全量是无解的；请用查询条件（年月/部门/人员）收敛行数。`
        : '渲染未返回可解析结果',
      ms: Date.now() - t0,
    };
  }

  const raw = await req('GET', `${base}/api/edc/report/view/getJsonStr?sessionKey=${j.data.json[0]}`, {
    headers, timeout: opts.timeout || TIMEOUT_MS,
  });
  const txt = decodeJsonStr(raw.raw);
  if (!txt) return { ok: false, msg: '渲染结果解码失败', ms: Date.now() - t0 };

  const w = JSON.parse(txt);
  const sh = w.sheets[Object.keys(w.sheets)[0]];
  return {
    ok: true,
    colCount: sh && sh.columnCount,
    rowCount: sh && sh.rowCount,
    total: j.data.total,
    pageRowCount: cap.value,
    ms: Date.now() - t0,
  };
}

if (require.main === module) {
  const [reportId, appId, pageRowCount] = process.argv.slice(2);
  if (!reportId) {
    console.error('Usage: EB_ALLOW_RENDER=1 node eb_render.js <reportId> [appId] [pageRowCount]');
    process.exit(2);
  }
  render(reportId, appId, { pageRowCount }).then((r) => {
    console.log(JSON.stringify(r, null, 2));
    process.exit(r.ok ? 0 : 1);
  }).catch((e) => {
    console.error(e.message || e);
    process.exit(1);
  });
}

module.exports = { render, capPageRowCount, DISABLED_HINT, ENABLED, CELL_LIMIT };
