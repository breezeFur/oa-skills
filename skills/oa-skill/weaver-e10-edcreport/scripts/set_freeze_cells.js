/**
 * set_freeze_cells.js —— 设置报表「冻结单元格」（冻结表头 / 锁定左侧列）
 *
 * 落点（源码级，见 references/layout-showlocation-freeze-guide.md）：
 *   1. **`cell.tag.fixed = true`** —— 唯一**服务端持久化**的标记。
 *      `EdcReportDevDesignServiceImpl` 保存时读 `cell.getTag().isFixed()` → `field.fixed = 1`；
 *      预览引擎 `AnalysisParams.analysisFrozenCell()` 取**第一个** `fixed==1` 的字段：
 *        frozenRowCount = 该字段 minCell.x    （冻结其上方各行）
 *        frozenColumnCount = 该字段 minCell.y （冻结其左侧各列）
 *   2. workbook 的 `sheet.frozenRowCount / frozenColCount` —— 设计区冻结线（保存侧不读，带上无害）。
 *   3. `sheet.tag.fixedCell = {x,y}` —— 设计器记忆锚点；**保存侧不持久化**，
 *      设计器加载时从「`fixed==1` 且 `cellText==='fixed-cell-tag'`」的字段重建。
 *
 * 关键结论：**锚点格不必是空格**。设计器只在锚点是空格时才补写 `cellText='fixed-cell-tag'`，
 *   占用格（数据字段所在格）由 `field.fixed=1` 独立生效 → 本脚本**只置 `tag.fixed`，不写 cellText**
 *   （写 cellText 会触发服务端把该格的边框/底色抹掉 —— 属于改动未点名的样式）。
 *
 * 覆盖式写入：`saveReportDevInfo` 只认整份 workbook，故从 `getReportDevInfo.fields[]` 反向重建
 *   （复用 fix_table_name_echo.js 已验证的重建函数）。默认 **dry-run**，必须 `--apply` 才落库。
 *
 * 用法:
 *   node set_freeze_cells.js --report-id <rid> [--app-id <aid>] [--anchor <x,y>] [--table-name "…"] \
 *        [--dump <out.json>] [--apply] [--json]
 *   --anchor 形如 `4,3`（x=行, y=列，均 0 基）。缺省自动取「首个数据行, 第0列」= 仅冻结表头。
 *   CLI: `edc-report fix freeze --report-id <rid> --app-id <aid> --anchor 4,3 [--apply]`
 */
const fs = require('fs');
const path = require('path');
const { request, apiHeaders, encodeWorkbook, saveReportDevInfo, getReportDevInfo } = require('./safe_report_save.js');
const { resolveE10Host } = require('./resolve_e10_host.js');
const { eteamsId } = require('./eb_auth.js');
const { buildWorkbook, coord, snap, diffSnap, CMP_KEYS } = require('./fix_table_name_echo.js');

function parseArgs() {
  const a = { reportId: '', appId: '', host: '', anchor: '', tableName: '', dump: '', apply: false, json: false };
  const v = process.argv.slice(2);
  for (let i = 0; i < v.length; i++) {
    if (v[i] === '--report-id') a.reportId = v[++i];
    else if (v[i] === '--app-id') a.appId = v[++i];
    else if (v[i] === '--host') a.host = v[++i];
    else if (v[i] === '--anchor') a.anchor = v[++i];
    else if (v[i] === '--table-name') a.tableName = v[++i];
    else if (v[i] === '--dump') a.dump = v[++i];
    else if (v[i] === '--apply') a.apply = true;
    else if (v[i] === '--json') a.json = true;
  }
  if (!a.reportId) throw new Error('--report-id is required');
  if (!a.host) a.host = resolveE10Host({});
  return a;
}

async function getJson(host, urlPath, reportId, appId) {
  const { json } = await request('GET', `${host}${urlPath}`, null, apiHeaders(host, eteamsId(), reportId, appId));
  return json || {};
}

/** 第一个数据行：优先「expandType=Vertical 的最小 x」，否则最大 x */
function guessAnchorX(fields) {
  const vx = fields.filter((f) => f.expandType === 'Vertical').map((f) => Number(f.x));
  if (vx.length) return Math.min(...vx);
  return Math.max(...fields.map((f) => Number(f.x)));
}

(async () => {
  const A = parseArgs();
  const host = A.host;
  const log = (...m) => { if (!A.json) console.log(...m); };

  let appId = A.appId;
  const bi = await getJson(host, `/api/bs/edc/report/baseInfo?id=${A.reportId}&useTag=backend`, A.reportId, appId);
  const reportName = (bi.data && bi.data.name) || '';
  if (!appId) appId = String((bi.data && (bi.data.appId || bi.data.appid)) || '');
  if (!appId) throw new Error('未取到 appId，请显式传 --app-id');

  const dev = await getReportDevInfo(host, A.reportId, appId);
  const devData = dev.data || {};
  const designKey = devData.designKey || '';
  const before = devData.fields || [];
  if (!before.length) throw new Error('fields[] 为空 —— 该报表没有可重建的单元格');
  if (!designKey) throw new Error('未取到 designKey');

  // tableName（重建时必须保留，否则会打回历史事故）
  const dsJson = await getJson(host, `/api/bs/edc/dataset/list?hasField=true&reportId=${A.reportId}`, A.reportId, appId);
  const F0 = before.filter((f) => f.cellType === 'Field');
  const usedDs = F0.length ? String(F0[0].dataSetId) : '';
  const mainDs = (dsJson.data || []).find((d) => String(d.id) === usedDs) || (dsJson.data || [])[0] || {};
  let TABLE_NAME = A.tableName;
  if (!TABLE_NAME) {
    const fk = await getJson(host, `/api/bs/edc/dataset/fieldsAndOriginFields?datasetId=${mainDs.id}&hasField=true&isFront=true&reportId=${A.reportId}`, A.reportId, appId);
    const fkArr = (fk.data && fk.data.fieldsKey) || [];
    TABLE_NAME = ((F0[0] || {}).tableName) || (fkArr[0] && fkArr[0].datasetName) || mainDs.name || '';
  }
  if (!TABLE_NAME) throw new Error('无法确定 tableName，请用 --table-name 显式指定');

  const ax = A.anchor ? Number(String(A.anchor).split(',')[0]) : guessAnchorX(before);
  const ay = A.anchor ? Number(String(A.anchor).split(',')[1]) : 0;
  if (!Number.isFinite(ax) || !Number.isFinite(ay)) throw new Error(`--anchor 非法：${A.anchor}（应形如 4,3）`);

  const t0 = Date.now();
  const wb = buildWorkbook(devData, TABLE_NAME);
  const sh = wb.sheets.Sheet1;
  const dt = sh.data.dataTable;

  // ★ 重复坐标拦截：fields[] 同一 (x,y) 出现多条 → workbook 一个坐标只能放一格，
  //   重建必然丢一条（历史事故：设计器里把字段拖到表头格上，旧 Const 未被清掉）。
  const seenCoord = {};
  for (const f of before) (seenCoord[`${f.x},${f.y}`] = seenCoord[`${f.x},${f.y}`] || []).push(f);
  const dups = Object.entries(seenCoord).filter(([, v]) => v.length > 1);
  if (dups.length) {
    console.error('✗ 检测到重复坐标（同一格有多条记录），重建会丢失其中一条 —— 拒绝落库：');
    for (const [k, v] of dups) {
      console.error(`   ${coord(k)} (${k}) 共 ${v.length} 条：`);
      v.forEach((f) => console.error(`      id=${f.id} ${f.cellType} ${f.text || f.cellText || ''} xCount=${f.xCount} createTime=${f.createTime}`));
    }
    console.error('   → 请先在设计器里清理该冲突格（删掉多余的那条），或由用户确认取舍后再跑。');
    process.exitCode = 3;
    return;
  }

  // 目标锚点必须已有单元格（否则冻结区无意义 / 会被服务端忽略）
  if (!dt[String(ax)] || !dt[String(ax)][String(ay)]) {
    throw new Error(`锚点 (${ax},${ay}) = ${coord(`${ax},${ay}`)} 上没有单元格；请指定已有内容的格`);
  }

  // 原有 fixed 清理 + 新锚点置位
  const prevFixed = [];
  for (const r of Object.keys(dt)) {
    for (const c of Object.keys(dt[r])) {
      if (dt[r][c].tag && dt[r][c].tag.fixed) prevFixed.push(coord(`${r},${c}`));
      if (dt[r][c].tag) dt[r][c].tag.fixed = false;
    }
  }
  dt[String(ax)][String(ay)].tag.fixed = true;
  sh.frozenRowCount = ax;
  sh.frozenColCount = ay;
  sh.tag = { ...sh.tag, fixedCell: { x: ax, y: ay } };

  const ctype = dt[String(ax)][String(ay)].style.cellType;
  log(`报表 = ${reportName || A.reportId}  (appId=${appId})`);
  log(`fields=${before.length}  Const=${before.length - F0.length}  Field=${F0.length}`);
  log(`tableName = "${TABLE_NAME}"`);
  log(`原 fixed 锚点 = ${prevFixed.length ? prevFixed.join(' ') : '(无)'}`);
  log(`新锚点 = ${coord(`${ax},${ay}`)}  (x=${ax}, y=${ay})  格类型=${ctype.cellType}${ctype.text ? ' 文案=' + ctype.text : ''}${ctype.cellText ? ' cellText=' + ctype.cellText : ''}`);
  log(`→ 冻结 上方 ${ax} 行 (第1~${ax}行) + 左侧 ${ay} 列 (第1~${ay}列)`);

  // 保真自检：除 fixed 之外不得与线上 fields[] 有差异
  const built = new Map();
  for (const r of Object.keys(dt)) for (const c of Object.keys(dt[r])) built.set(`${r},${c}`, dt[r][c].style.cellType);
  let mismatch = 0;
  for (const f of before) {
    const ct = built.get(`${f.x},${f.y}`);
    if (!ct) { mismatch++; continue; }
    for (const key of CMP_KEYS) {
      if (['tableName', 'style', 'xCount', 'yCount'].includes(key)) continue;
      const norm = (v) => (v === undefined || v === null ? '' : (typeof v === 'object' ? JSON.stringify(v) : String(v)));
      if (norm(f[key]) !== norm(ct[key])) {
        if (mismatch < 8) log(`   ⚠ ${coord(`${f.x},${f.y}`)}.${key}: fields=${norm(f[key]).slice(0, 24)} built=${norm(ct[key]).slice(0, 24)}`);
        mismatch++;
      }
    }
  }
  log(`保真自检: 不一致键 ${mismatch} 处`);
  log(`单元格数 = ${[...Object.keys(dt)].reduce((n, r) => n + Object.keys(dt[r]).length, 0)} / fields ${before.length}`);
  if (mismatch) { console.error('✗ 重建保真度不足，拒绝保存'); process.exitCode = 2; return; }

  if (!A.apply) {
    log('\n[dry-run] 未落库。确认无误后加 --apply 执行。');
    if (A.dump) {
      const out = path.resolve(A.dump);
      fs.writeFileSync(out, JSON.stringify(wb));
      log(`（重建产物已写出：${out}）`);
    }
    return;
  }
  if (Date.now() - t0 > 60000) log('⚠ 重建耗时较久，designKey 可能已失效，将重新读取');

  const fresh = await getReportDevInfo(host, A.reportId, appId);
  const res = await saveReportDevInfo(host, {
    reportId: A.reportId, appId, name: reportName,
    designKey: fresh.data.designKey, workbookB64: encodeWorkbook(wb),
    et: fresh.et, groupId: (bi.data && bi.data.groupId) || '0', nameLabelId: (bi.data && bi.data.nameLabelId) || '-1',
  });
  if (!res.json || res.json.code !== 200) { console.error('✗ saveReportDevInfo 失败：', JSON.stringify(res.json || res.raw).slice(0, 200)); process.exitCode = 1; return; }

  const after = (await getReportDevInfo(host, A.reportId, appId)).data;
  const afterFields = after.fields || [];
  const fixedNow = afterFields.filter((f) => Number(f.fixed) === 1);
  const dd = diffSnap(snap(before), snap(afterFields));
  const unexpected = dd.filter((x) => !['tableName', '(新增)'].includes(x.key));
  log(`\n保存后: fields=${afterFields.length}  fixed=1 的格 = ${fixedNow.map((f) => coord(`${f.x},${f.y}`)).join(' ') || '(无)'}`);
  log(`快照 diff = ${dd.length} 处（tableName ${dd.filter((x) => x.key === 'tableName').length} / 新增 ${dd.filter((x) => x.key === '(新增)').length} / 其他 ${unexpected.length}）`);
  unexpected.slice(0, 10).forEach((x) => log(`   ⚠ ${coord(x.cell)}.${x.key}: ${x.a} -> ${x.b}`));
  const ok = unexpected.length === 0 && fixedNow.length === 1
    && Number(fixedNow[0].x) === ax && Number(fixedNow[0].y) === ay;
  log(ok ? `✅ 完成：冻结锚点 = ${coord(`${ax},${ay}`)}，其余零差异` : '⚠ 请核对上方差异');
  if (A.json) console.log(JSON.stringify({ ok, reportId: A.reportId, anchor: { x: ax, y: ay }, fixedCells: fixedNow.map((f) => `${f.x},${f.y}`), unexpected }));
  if (!ok) process.exitCode = 2;
})().catch((e) => { console.error('✗ ' + e.message); process.exitCode = 1; });
