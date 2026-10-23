'use strict';
/**
 * check_cell_limit.js —— 渲染规模预检（5 万格上限）
 *
 * 背景（PERF-1/PERF-2/PERF-5）：平台单次渲染上限 50,000 单元格；交叉表一旦全量展开，
 *   行数 × 列数必然超限 → 前端一直转圈、接口最终 `code:555`，且平台「先算完再拒绝」，
 *   每次探测白烧 15~80s。**搭报表不需要渲染，但需要知道会不会超限。**
 *
 * 本命令**不渲染**，只做算术 + 结构回读：
 *   报表设计列数（自 getReportDevInfo.fields 求 max(y)+1）
 *   × 数据集行数（--rows 显式给，或尝试 dataset preview 的 total）
 *   → 与 50000 比较，给出结论与建议（pageRowCount 上限 / 是否必须加查询条件）
 *
 * 用法：
 *   node check_cell_limit.js --report-id <rid> [--app-id <aid>]
 *        [--rows N]            # 数据集行数（不给则尝试自动探测）
 *        [--cols N]            # 直接指定展开后总列数（覆盖自动推算）
 *        [--date-values N]     # 日期维度取值个数（交叉表：cols = 固定列 + N × blockWidth）
 *        [--block-width 3]     # 每个日期块占几列（默认 3）
 *        [--json]
 *
 * 退出码：0 = 安全；1 = 超限（或无法判定）。
 */
const https = require('https');
const A = require('./eb_auth.js');

const CELL_LIMIT = 50000;

function parseArgs(v) {
  const a = { blockWidth: 3 };
  for (let i = 0; i < v.length; i++) {
    const k = v[i];
    if (k === '--report-id') a.reportId = v[++i];
    else if (k === '--app-id') a.appId = v[++i];
    else if (k === '--rows') a.rows = Number(v[++i]);
    else if (k === '--cols') a.cols = Number(v[++i]);
    else if (k === '--date-values') a.dateValues = Number(v[++i]);
    else if (k === '--block-width') a.blockWidth = Number(v[++i]);
    else if (k === '--json') a.json = true;
    else if (k === '-h' || k === '--help') a.help = true;
  }
  return a;
}

function request(method, urlPath, { appId, reportId, query } = {}) {
  const base = A.baseUrl();
  const u = new URL(base + urlPath);
  if (query) for (const [k, v] of Object.entries(query)) if (v != null) u.searchParams.set(k, String(v));
  const headers = {
    accept: 'application/json, text/plain, */*',
    eteamsid: A.eteamsId(),
    Cookie: A.cookieHeader(),
    'User-Agent': 'Mozilla/5.0 AgentType=WorkBuddy,IsAgent=true',
    Referer: `${base}/sp/edc/report/designer/${reportId || ''}`,
  };
  if (appId) { headers.ebBusinessId = appId; headers.ebbusinessid = appId; }
  return new Promise((resolve, reject) => {
    const r = https.request(
      { method, hostname: u.hostname, port: u.port || 443, path: u.pathname + u.search,
        headers, rejectUnauthorized: false, timeout: 20000 },
      (res) => {
        const ch = [];
        res.on('data', (c) => ch.push(c));
        res.on('end', () => {
          const raw = Buffer.concat(ch).toString('utf8');
          let json = null;
          try { json = JSON.parse(raw); } catch (e) { /* ignore */ }
          resolve({ status: res.statusCode, json, raw });
        });
      }
    );
    r.setTimeout(20000, () => r.destroy(new Error('请求超时 20s')));
    r.on('error', reject);
    r.end();
  });
}

async function main() {
  const a = parseArgs(process.argv.slice(2));
  if (a.help) {
    console.log(`Usage: node check_cell_limit.js --report-id <rid> [--app-id <aid>] [--rows N] [--cols N] [--date-values N] [--block-width 3] [--json]`);
    return;
  }
  if (!a.reportId) throw new Error('--report-id is required');

  const notes = [];
  const dev = await request('GET', '/api/bs/edc/report/getReportDevInfo', {
    appId: a.appId, reportId: a.reportId, query: { reportId: a.reportId },
  });
  const d = (dev.json && dev.json.data) || {};
  const fields = d.fields || [];
  if (!fields.length) notes.push('未读到 fields（报表可能不存在或权限不足）');
  const appId = a.appId || d.appId;

  // 设计列数
  const maxY = fields.reduce((m, f) => Math.max(m, Number(f.y) || 0), 0);
  const designedCols = fields.length ? maxY + 1 : 0;
  const fieldCount = fields.filter((f) => f.cellType === 'Field').length;

  // 展开列数
  let cols = a.cols;
  let colsSource = 'explicit(--cols)';
  if (!cols) {
    if (a.dateValues && Number.isFinite(a.dateValues)) {
      const staticCols = Math.max(0, designedCols - a.blockWidth);
      cols = staticCols + a.dateValues * a.blockWidth;
      colsSource = `固定 ${staticCols} + ${a.dateValues} 个日期值 × ${a.blockWidth} 列`;
    } else {
      cols = designedCols;
      colsSource = `设计列数 max(y)+1 = ${designedCols}（未给 --date-values，未做日期展开）`;
      if (designedCols) notes.push('交叉表请补 --date-values <日期取值个数> 才能算出真正的展开列数');
    }
  }

  // 行数
  let rows = a.rows;
  let rowsSource = 'explicit(--rows)';
  if (!Number.isFinite(rows)) {
    // 尝试 dataset 预览的 total
    try {
      const dl = await request('GET', '/api/bs/edc/dataset/list', {
        appId, reportId: a.reportId, query: { hasField: 'true', reportId: a.reportId },
      });
      const arr = (dl.json && dl.json.data) || [];
      for (const ds of arr) {
        const pv = await request('GET', '/api/bs/edc/dataset/getPreviewData', {
          appId, reportId: a.reportId, query: { dataSetId: ds.id, isFront: 'true' },
        });
        const p = (pv.json && pv.json.data) || {};
        const t = [p.total, p.totalCount, p.records, p.totalNum, p.count].find((x) => Number.isFinite(Number(x)));
        if (t != null) { rows = Number(t); rowsSource = `dataset「${ds.name || ds.id}」preview 的 total`; break; }
      }
      if (!Number.isFinite(rows)) notes.push('数据集 preview 未返回总量字段，请用 --rows 显式给行数');
    } catch (e) {
      notes.push(`自动探测行数失败（${e.message}），请用 --rows 显式给`);
    }
  }

  const cells = Number.isFinite(rows) && Number.isFinite(cols) ? rows * cols : null;
  const over = cells != null && cells > CELL_LIMIT;
  const safeRows = Number.isFinite(cols) && cols > 0 ? Math.floor(CELL_LIMIT / cols) : null;
  const ratio = cells != null ? +(cells / CELL_LIMIT).toFixed(2) : null;

  const advice = [];
  if (cells == null) {
    advice.push('无法判定：缺行数或列数。补 --rows / --cols 后重跑。');
  } else if (over) {
    advice.push(`超限：预计 ${cells.toLocaleString('en-US')} 格 = 上限的 ${ratio} 倍 → 全量渲染必然 code:555，预览会一直转。`);
    advice.push(`本列数下安全行数上限 = ${safeRows} 行；base 分页 pageRowCount ≤ ${safeRows}。`);
    advice.push('收敛办法：给报表加查询条件（年月 / 部门 / 人员）并设默认值，让用户打开时自动过滤。');
    advice.push('**但注意**：搭报表本身不要求渲染全量 —— 落库成功即可，验收用 verify bind / verify all。');
  } else {
    advice.push(`安全：预计 ${cells.toLocaleString('en-US')} 格（上限的 ${ratio} 倍）。`);
  }
  if (cols && cols > 0) advice.push(`渲染守卫 pageRowCount 封顶 = ${Math.min(574, safeRows || 574)}`);

  const out = {
    ok: !over,
    reportId: a.reportId, appId: appId || null,
    cellLimit: CELL_LIMIT,
    designedColumns: designedCols,
    fieldCells: fieldCount,
    expandedColumns: cols || null,
    expandedColumnsSource: colsSource,
    rows: Number.isFinite(rows) ? rows : null,
    rowsSource: rowsSource,
    estimatedCells: cells,
    ratioToLimit: ratio,
    safeRowsForTheseCols: safeRows,
    verdict: cells == null ? 'unknown' : (over ? 'over_limit' : 'safe'),
    advice,
    notes,
  };

  if (a.json) {
    console.log(JSON.stringify(out, null, 2));
  } else {
    console.log(`\nedc-report verify limit —— 渲染规模预检\n`);
    console.log(`  报表        ${a.reportId}${appId ? ` (app ${appId})` : ''}`);
    console.log(`  设计列数    ${designedCols}  （字段格 ${fieldCount}）`);
    console.log(`  展开列数    ${cols == null ? '?' : cols}   ← ${colsSource}`);
    console.log(`  数据集行数  ${out.rows == null ? '?' : out.rows}   ← ${rowsSource}`);
    console.log(`  预计格数    ${cells == null ? '?' : cells.toLocaleString('en-US')}  /  上限 ${CELL_LIMIT.toLocaleString('en-US')}`);
    console.log(`  判定        ${cells == null ? '⚠️ 无法判定' : (over ? `❌ 超限（${ratio}×）` : `✅ 安全（${ratio}×）`)}\n`);
    for (const s of advice) console.log(`  · ${s}`);
    for (const n of notes) console.log(`  ℹ️  ${n}`);
    console.log('');
  }

  process.exitCode = over ? 1 : 0;
}

main().catch((e) => {
  console.error(JSON.stringify({ ok: false, error: String(e.message || e) }, null, 2));
  process.exit(1);
});
