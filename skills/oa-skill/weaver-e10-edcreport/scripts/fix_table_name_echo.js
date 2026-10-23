/**
 * fix_table_name_echo.js —— 批量补齐 Field 单元格的 `tableName`（修「单元格/属性面板不回显数据集名」）
 *
 * 现象：报表里所有 Field 单元格 `tableName` 为空 → 设计器不回显数据集名；
 *       典型是「某个人工手绑的单元格是对的，其余全错」，用户会点名该参照单元格。
 * 取值：`fieldsKey[].datasetName`（或用户点名的参照单元格 tableName）
 *       形态 A LOGIC → `xxx(业务模块)`；形态 B form → `xxx(表单)`；形态 C ETEAMS/sql → **无后缀**
 *
 * 为什么整份重建：`saveReportDevInfo` 只认整份 workbook（gzip+base64）且**整体替换**；
 *   而 `getReportDevInfo.workbookProps.sheets` 恒为 `{}` → 拿不到 dataTable。
 *   本脚本从 `getReportDevInfo.fields[]`（服务端逐单元格回读）反向重建 workbook。
 *   ⚠️ 这是**覆盖式**写入：默认 dry-run，必须显式 `--apply` 才落库。
 *
 * 实测踩坑（改脚本前必读 references/dataset-table-field-contract-guide.md §四点六）：
 *   1. fields[] 不回传 typeName/allowOverflow/editorType/groupType/isActiveParent/arrowType，
 *      但服务端保存**必须要 typeName** → 必须兜底，否则 500「报表内部错误」。
 *   2. dateTimeProps/highlightDatas/allNeedFields/fill* 是服务端保存时派生的，回写即 500。
 *   3. cellType.formatterType 设计器保存值是 []（不是 ['common']；['common'] 属 tag.formatterType）。
 *   4. designKey 每次 GET 都变（即时令牌）→ 读后需立即保存。
 *   5. fields[].width/height 可合法为 0（Excel 隐藏列）→ 不能用 `|| 默认值` 吞掉。
 *   6. 提交含合并区全部单元格时服务端只留左上角 → 重建时不要凭空补被覆盖的格子。
 *
 * 用法:
 *   node fix_table_name_echo.js --report-id <rid> [--app-id <aid>] [--host <url>] \
 *        [--table-name "<数据集名>"] [--restore-from <wb.json>] [--dump <out.json>] [--apply] [--json]
 *   不带 --apply 只做 dry-run（打印计划 + 重建保真自检，不落库）。
 *   --dump：dry-run 时把重建好的 workbook 写到指定文件（默认不写，保持目录干净）。
 *   --restore-from：把备份 workbook 中「线上已不存在」的单元格补回（例如被误删的手绑单元格）。
 *   CLI 入口：`edc-report fix table-name …`（落库）/ `edc-report verify contract <rid>`（只读体检）
 */
const fs = require('fs');
const path = require('path');
const { request, apiHeaders, encodeWorkbook, saveReportDevInfo, getReportDevInfo } = require('./safe_report_save.js');
const { resolveE10Host } = require('./resolve_e10_host.js');
const { eteamsId } = require('./eb_auth.js');

// ---------------- args ----------------
function parseArgs() {
  const a = { reportId: '', appId: '', host: '', tableName: '', restoreFrom: '', apply: false, json: false };
  const v = process.argv.slice(2);
  for (let i = 0; i < v.length; i++) {
    if (v[i] === '--report-id') a.reportId = v[++i];
    else if (v[i] === '--app-id') a.appId = v[++i];
    else if (v[i] === '--host') a.host = v[++i];
    else if (v[i] === '--table-name') a.tableName = v[++i];
    else if (v[i] === '--restore-from') a.restoreFrom = v[++i];
    else if (v[i] === '--dump') a.dump = v[++i];
    else if (v[i] === '--apply') a.apply = true;
    else if (v[i] === '--json') a.json = true;
  }
  if (!a.reportId) throw new Error('--report-id is required');
  if (!a.host) a.host = resolveE10Host({});
  return a;
}

// ---------------- cellType 键序（= 设计器真实保存键序） ----------------
const FIELD_ORDER = [
  'allowOverflow', 'typeName', 'editorType', 'name', 'nameIndex', 'text', 'dataSetId',
  'leftX', 'leftY', 'topX', 'topY', 'refX', 'refY', 'expandType', 'displayType',
  'cellType', 'sheetIndex', 'cellText', 'transType', 'transSelectOptions', 'browserType',
  'thumbnail', 'isHtml', 'prefixAndSuffix', 'inheritParent', 'valueCompletion',
  'groupCountConfig', 'conditionRule', 'leftFilterField', 'customFilterField',
  'dataFilterField', 'topFilterField', 'countType', 'groupType', 'qrcodeType', 'qrcodelink',
  'hiddenContext', 'orderType', 'pcHreflink', 'h5Hreflink', 'openType', 'formatterType',
  'subordination', 'fieldKey', 'tableName', 'isActiveParent', 'arrowType', 'textDirection',
];
const CONST_ORDER = [
  'allowOverflow', 'typeName', 'editorType', 'dataSetId',
  'leftX', 'leftY', 'topX', 'topY', 'refX', 'refY', 'expandType', 'displayType',
  'cellType', 'sheetIndex', 'cellText', 'transSelectOptions', 'browserType',
  'thumbnail', 'prefixAndSuffix', 'inheritParent', 'valueCompletion',
  'groupCountConfig', 'conditionRule', 'leftFilterField', 'customFilterField',
  'dataFilterField', 'topFilterField', 'countType', 'groupType',
  'hiddenContext', 'orderType', 'pcHreflink', 'h5Hreflink', 'openType', 'formatterType',
  'subordination', 'isActiveParent', 'arrowType', 'textDirection',
];
// fields[] 里属「位置/尺寸/台账/服务端派生」的键 —— 不得写回 cellType
const NON_CELL_KEYS = new Set(['id', 'createTime', 'updateTime', 'creator', 'deleteType', 'tenantKey',
  'reportId', 'showOrder', 'style', 'width', 'height', 'x', 'y', 'xCount', 'yCount',
  'colVisible', 'rowVisible', 'formatterTypeStr', 'formattertype', 'fixed',
  'dateTimeProps', 'highlightDatas', 'allNeedFields',
  'fillDtIndex', 'fillShow', 'fillAddLine', 'fillDelLine', 'fillMergeShow', 'fillSelectId', 'fillTextLength']);
const JSON_ARR_KEYS = new Set(['transSelectOptions', 'leftFilterField', 'topFilterField', 'customFilterField',
  'prefixAndSuffix', 'dataFilterField', 'browserType', 'subordination', 'highlightDatas', 'formatterType']);
const JSON_OBJ_KEYS = new Set(['groupCountConfig', 'valueCompletion', 'conditionRule', 'dateTimeProps', 'sheetConfig', 'columnConfig']);
const NUM_KEYS = new Set(['leftX', 'leftY', 'topX', 'topY', 'refX', 'refY', 'sheetIndex', 'showOrder', 'width', 'height']);

function parseMaybe(v) {
  if (typeof v !== 'string') return v;
  const s = v.trim();
  if (!s) return v;
  if ((s.startsWith('[') && s.endsWith(']')) || (s.startsWith('{') && s.endsWith('}'))) {
    try { return JSON.parse(s); } catch (e) { return v; }
  }
  return v;
}
function coerce(key, v) {
  if (v === undefined || v === null) return undefined;
  if (JSON_ARR_KEYS.has(key) || JSON_OBJ_KEYS.has(key)) return parseMaybe(v);
  if (NUM_KEYS.has(key)) return Number(v);
  if (key === 'allowOverflow') return typeof v === 'boolean' ? v : v === 'true';
  return v;
}

function assemble(f, tableName) {
  const isField = f.cellType === 'Field';
  const order = isField ? FIELD_ORDER : CONST_ORDER;
  const ct = {};
  for (const k of order) {
    if (isField && k === 'tableName') continue;
    if (!(k in f)) continue;
    const v = coerce(k, f[k]);
    if (v !== undefined) ct[k] = v;
  }
  // ★ 结构必填兜底（fields[] 不回传，缺失必 500）
  if (ct.allowOverflow === undefined) ct.allowOverflow = true;
  ct.typeName = isField ? 'FieldCellType' : 'ConstCellType';
  ct.editorType = 1;
  ct.formatterType = [];                                   // 设计器保存值 = []
  if (ct.groupType === undefined) ct.groupType = null;
  if (ct.arrowType === undefined) {
    ct.arrowType = ct.expandType === 'Vertical' ? 'Vertical' : (ct.expandType === 'Horizontal' ? 'Horizontal' : 'None');
  }
  if (ct.isActiveParent === undefined) {
    ct.isActiveParent = isField && Number(ct.leftX) === -1 && Number(ct.topX) === -1
      && (ct.expandType === 'Vertical' || ct.expandType === 'Horizontal');
  }
  if (isField) ct.tableName = tableName === null ? (f.tableName || '') : (tableName || '');
  for (const k of Object.keys(f)) {
    if (NON_CELL_KEYS.has(k) || k in ct || order.includes(k)) continue;
    const v = coerce(k, f[k]);
    if (v !== undefined) ct[k] = v;
  }
  const out = {};
  for (const k of order) if (k in ct) out[k] = ct[k];
  for (const k of Object.keys(ct)) if (!(k in out)) out[k] = ct[k];
  return out;
}

function buildWorkbook(dev, tableName, extraCells) {
  const fields = dev.fields || [];
  const sp = (dev.sheetProps || [])[0] || {};
  const wbp = dev.workbookProps || {};
  const dt = {};
  const rowSize = {}, colSize = {}, spans = [], seen = new Set();
  let maxX = 0, maxY = 0;
  const numOr = (v, fb) => (v === undefined || v === null || v === '' ? fb : Number(v));

  const put = (f) => {
    const x = Number(f.x), y = Number(f.y);
    if (seen.has(`${x},${y}`)) return;
    seen.add(`${x},${y}`);
    maxX = Math.max(maxX, x); maxY = Math.max(maxY, y);
    if (rowSize[x] === undefined) rowSize[x] = numOr(f.height, 20);
    if (colSize[y] === undefined) colSize[y] = numOr(f.width, 40);
    const styleObj = parseMaybe(f.style);
    if (!styleObj || typeof styleObj !== 'object' || Array.isArray(styleObj)) return;
    dt[String(x)] = dt[String(x)] || {};
    dt[String(x)][String(y)] = {
      style: { ...styleObj, cellType: assemble(f, tableName) },
      tag: { fixed: !!f.fixed, formatterType: ['common'] },
    };
    const xc = Math.max(1, Number(f.xCount) || 1), yc = Math.max(1, Number(f.yCount) || 1);
    if (xc > 1 || yc > 1) spans.push({ row: x, col: y, rowCount: xc, colCount: yc });
  };
  fields.forEach(put);
  (extraCells || []).forEach((c) => { if (!seen.has(`${c.x},${c.y}`)) put(c); });

  const sk = new Set(), spans2 = [];
  spans.forEach((s) => { const k = `${s.row},${s.col},${s.rowCount},${s.colCount}`; if (!sk.has(k)) { sk.add(k); spans2.push(s); } });

  const maxSpanCol = spans2.length ? Math.max(...spans2.map((s) => s.col + s.colCount - 1)) : maxY;
  const columnCount = Math.max(maxY + 1 + 6, 30);
  const columns = []; let lastColSize = 40;
  for (let c = 0; c < columnCount; c++) {
    if (colSize[c] !== undefined) { lastColSize = colSize[c]; columns.push({ size: colSize[c] }); }
    else columns.push({ size: c <= maxSpanCol ? lastColSize : 40 });
  }
  const rows = [];
  for (let r = 0; r <= maxX; r++) rows.push({ size: rowSize[r] || 20 });

  return {
    version: wbp.version || '11.1.0',
    __scrollbarShowMax: !!wbp.__scrollbarShowMax,
    __excelSheet: !!wbp.__excelSheet,
    workbookConfig: {},
    sheets: {
      Sheet1: {
        name: sp.name || 'Sheet1', index: 0, theme: 'Office',
        activeRow: maxX, activeCol: 0,
        __rowColHeaderVisible: sp.rowHeaderVisible || 0,
        __gridline: sp.gridLine || 0,
        __printLineVisible: !!sp.printLineVisible,
        rowCount: 200, columnCount, rows, columns, spans: spans2,
        selections: { 0: { row: 0, rowCount: 1, col: 0, colCount: 1 }, length: 1 },
        tag: {
          childMerge: sp.childMerge || 0,
          showLocation: sp.showLocation === undefined ? 1 : sp.showLocation,
          filterSheet: sp.filterSheet || 0,
          tableNameSuffix: sp.tableNameSuffix || 0,
          columnConfig: parseMaybe(sp.columnConfig) || {},
          sheetConfig: parseMaybe(sp.sheetConfig) || { dataPreAgg: true, simpleList: false },
        },
        data: { dataTable: dt, defaultDataNode: { style: { themeFont: 'Body' } } },
        colHeaderData: { defaultDataNode: { style: { themeFont: 'Body' } } },
        rowHeaderData: { defaultDataNode: { style: { themeFont: 'Body' } } },
      },
    },
  };
}

// ---------------- snapshot diff ----------------
const CMP_KEYS = ['cellType', 'name', 'text', 'cellText', 'nameIndex', 'dataSetId', 'expandType', 'displayType',
  'countType', 'leftX', 'leftY', 'topX', 'topY', 'xCount', 'yCount', 'fieldKey', 'tableName', 'orderType',
  'openType', 'inheritParent', 'hiddenContext', 'textDirection', 'isHtml', 'qrcodeType', 'style'];
const snap = (fields) => new Map(fields.map((f) => [`${f.x},${f.y}`, f]));
const norm = (v) => (v === undefined || v === null ? '' : (typeof v === 'object' ? JSON.stringify(v) : String(v)));
function diffSnap(a, b) {
  const out = [];
  for (const k of new Set([...a.keys(), ...b.keys()])) {
    const fa = a.get(k), fb = b.get(k);
    if (!fa) { out.push({ cell: k, key: '(新增)', a: '-', b: fb.cellType }); continue; }
    if (!fb) { out.push({ cell: k, key: '(丢失)', a: fa.cellType, b: '-' }); continue; }
    for (const key of CMP_KEYS) {
      let va = fa[key], vb = fb[key];
      if (key === 'style' && va && vb) { va = String(va).toLowerCase(); vb = String(vb).toLowerCase(); }
      if (norm(va) !== norm(vb)) out.push({ cell: k, key, a: norm(va).slice(0, 50), b: norm(vb).slice(0, 50) });
    }
  }
  return out;
}
function coord(s) {
  const m = /^(\d+),(\d+)$/.exec(s);
  if (!m) return s;
  const x = Number(m[1]); let y = Number(m[2]); let t = '';
  while (y >= 0) { t = String.fromCharCode(65 + (y % 26)) + t; y = Math.floor(y / 26) - 1; }
  return t + (x + 1);
}

async function getJson(host, urlPath, reportId, appId) {
  const { json } = await request('GET', `${host}${urlPath}`, null, apiHeaders(host, eteamsId(), reportId, appId));
  return json || {};
}

async function main() {
  const A = parseArgs();
  const host = A.host;
  const log = (...m) => { if (!A.json) console.log(...m); };

  // appId 兜底：baseInfo
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

  // 数据集显示名：优先 --table-name，其次 fieldsKey[].datasetName，最后 dataset/list[].name
  const dsJson = await getJson(host, `/api/bs/edc/dataset/list?hasField=true&reportId=${A.reportId}`, A.reportId, appId);
  const dsList = dsJson.data || [];
  const F0 = before.filter((f) => f.cellType === 'Field');
  const usedDs = F0.length ? String(F0[0].dataSetId) : '';
  const mainDs = dsList.find((d) => String(d.id) === usedDs) || dsList[0] || {};
  let TABLE_NAME = A.tableName;
  if (!TABLE_NAME) {
    const fk = await getJson(host, `/api/bs/edc/dataset/fieldsAndOriginFields?datasetId=${mainDs.id}&hasField=true&isFront=true&reportId=${A.reportId}`, A.reportId, appId);
    const fkArr = (fk.data && fk.data.fieldsKey) || [];
    TABLE_NAME = (fkArr[0] && fkArr[0].datasetName) || mainDs.name || '';
  }
  if (!TABLE_NAME) throw new Error('无法确定 tableName，请用 --table-name 显式指定');

  // 从备份补回线上已不存在的单元格
  const extraCells = [];
  if (A.restoreFrom) {
    const bw = JSON.parse(fs.readFileSync(A.restoreFrom, 'utf8'));
    const bsh = bw.sheets[Object.keys(bw.sheets)[0]];
    const bdt = bsh.data.dataTable;
    const live = new Set(before.map((f) => `${f.x},${f.y}`));
    for (const r of Object.keys(bdt)) {
      for (const c of Object.keys(bdt[r])) {
        if (live.has(`${r},${c}`)) continue;
        const cell = bdt[r][c];
        const ct = cell.style.cellType;
        const styleObj = {};
        for (const k of Object.keys(cell.style)) if (k !== 'cellType') styleObj[k] = cell.style[k];
        extraCells.push({
          ...ct, x: Number(r), y: Number(c), style: JSON.stringify(styleObj),
          width: bsh.columns[Number(c)] ? bsh.columns[Number(c)].size : 40,
          height: bsh.rows[Number(r)] ? bsh.rows[Number(r)].size : 20,
          xCount: 1, yCount: 1,
        });
      }
    }
  }

  log(`报表 = ${reportName || A.reportId}  (appId=${appId})`);
  log(`fields=${before.length}  Const=${before.length - F0.length}  Field=${F0.length}`);
  log(`dataset = ${mainDs.name || '(?)'} (id=${mainDs.id || '?'}, ${mainDs.sourceType || '?'}/${mainDs.sourceGroup || '?'})`);
  log(`tableName 取值 = "${TABLE_NAME}"`);
  log(`Field 中 tableName 缺失 = ${F0.filter((f) => !f.tableName).length} / ${F0.length}`);
  const refCell = F0.find((f) => f.tableName);
  if (refCell) log(`参照单元格 = ${coord(`${refCell.x},${refCell.y}`)} (tableName="${refCell.tableName}")`);
  if (extraCells.length) log(`从备份补回 = ${extraCells.map((e) => coord(`${e.x},${e.y}`)).join(' ')}`);

  const t0 = Date.now();
  const wb = buildWorkbook(devData, TABLE_NAME, extraCells);
  const sh = wb.sheets.Sheet1;
  let cells = 0;
  for (const r of Object.keys(sh.data.dataTable)) cells += Object.keys(sh.data.dataTable[r]).length;
  log(`\n重建 workbook: cells=${cells} (期望 ${before.length + extraCells.length})  rows=${sh.rows.length}  columns=${sh.columnCount}  spans=${sh.spans.length}`);

  // 保真自检
  const built = new Map();
  for (const r of Object.keys(sh.data.dataTable)) for (const c of Object.keys(sh.data.dataTable[r])) {
    built.set(`${r},${c}`, sh.data.dataTable[r][c].style.cellType);
  }
  let mismatch = 0;
  for (const f of before) {
    const ct = built.get(`${f.x},${f.y}`);
    if (!ct) { mismatch++; continue; }
    for (const key of CMP_KEYS) {
      if (['tableName', 'style', 'xCount', 'yCount'].includes(key)) continue;
      if (norm(f[key]) !== norm(ct[key])) { if (mismatch < 8) log(`   ⚠ ${coord(`${f.x},${f.y}`)}.${key}: fields=${norm(f[key]).slice(0, 24)} built=${norm(ct[key]).slice(0, 24)}`); mismatch++; }
    }
  }
  const tnOk = [...built.values()].filter((c) => c.cellType === 'Field' && c.tableName === TABLE_NAME).length;
  log(`保真自检: 不一致键 ${mismatch} 处   重建后带 tableName 的 Field = ${tnOk}`);
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

  // ★ designKey 是即时令牌：重新读一次，紧邻保存
  const fresh = await getReportDevInfo(host, A.reportId, appId);
  const wb64 = encodeWorkbook(wb);
  const res = await saveReportDevInfo(host, {
    reportId: A.reportId, appId, name: reportName,
    designKey: fresh.data.designKey, workbookB64: wb64,
    et: fresh.et, groupId: (bi.data && bi.data.groupId) || '0', nameLabelId: (bi.data && bi.data.nameLabelId) || '-1',
  });
  if (!res.json || res.json.code !== 200) { console.error('✗ saveReportDevInfo 失败：', JSON.stringify(res.json || res.raw).slice(0, 200)); process.exitCode = 1; return; }

  const after = (await getReportDevInfo(host, A.reportId, appId)).data;
  const afterFields = after.fields || [];
  const F2 = afterFields.filter((f) => f.cellType === 'Field');
  const dd = diffSnap(snap(before), snap(afterFields));
  const unexpected = dd.filter((x) => !['tableName', '(新增)'].includes(x.key));
  log(`\n保存后: fields=${afterFields.length}  Field=${F2.length}  tableName 缺失=${F2.filter((f) => !f.tableName).length}`);
  log(`tableName 取值集合 = ${JSON.stringify([...new Set(F2.map((f) => f.tableName))])}`);
  log(`快照 diff = ${dd.length} 处（tableName ${dd.filter((x) => x.key === 'tableName').length} / 新增 ${dd.filter((x) => x.key === '(新增)').length} / 其他 ${unexpected.length}）`);
  unexpected.slice(0, 10).forEach((x) => log(`   ⚠ ${coord(x.cell)}.${x.key}: ${x.a} -> ${x.b}`));
  const ok = unexpected.length === 0 && F2.every((f) => f.tableName);
  log(ok ? '✅ 完成：全部 Field 已带 tableName，其余零差异' : '⚠ 请核对上方差异');
  if (A.json) console.log(JSON.stringify({ ok, reportId: A.reportId, tableName: TABLE_NAME, fields: afterFields.length, fieldCells: F2.length, missing: F2.filter((f) => !f.tableName).length, unexpected }));
  if (!ok) process.exitCode = 2;
}

/**
 * 复用的公共件 —— 让其它「定向改 workbook」脚本（如 set_freeze_cells.js）
 * 能直接调用本文件已验证过的重建逻辑，避免各写一份。
 */
module.exports = {
  buildWorkbook,
  assemble,
  coord,
  snap,
  diffSnap,
  CMP_KEYS,
  NON_CELL_KEYS,
  FIELD_ORDER,
  CONST_ORDER,
};

if (require.main === module) {
  main().catch((e) => { console.error('✗ ' + e.message); process.exitCode = 1; });
}
