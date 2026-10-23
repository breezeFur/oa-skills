/**
 * Safe partial-save helpers for saveReportDevInfo.
 * Prevents wiping designer fields/cells when patching snapshot or other workbook metadata.
 *
 * See references/safe-partial-save-guide.md
 */
const zlib = require('zlib');

const https = require('https');

const DEFAULT_HOST = process.env.EB_HOST || process.env.E10_BASE_URL || process.env.E10_HOST || '';

function parseJsonMaybe(v, fallback) {
  if (v == null || v === '') return fallback;
  if (Array.isArray(v) || typeof v === 'object') return v;
  try {
    return JSON.parse(v);
  } catch {
    return fallback;
  }
}

function countWorkbookCells(wb) {
  const sheets = wb?.sheets || {};
  let cells = 0;
  for (const sheet of Object.values(sheets)) {
    const dt = sheet?.data?.dataTable || {};
    for (const x of Object.keys(dt)) cells += Object.keys(dt[x]).length;
  }
  return cells;
}

function normalizeStyleForWorkbook(style) {
  const ct = style.analysisFieldCellType || style.cellType;
  if (ct && typeof ct === 'object') {
    style.cellType = ct;
    delete style.analysisFieldCellType;
  }
  return style;
}

function fieldToCell(f) {
  const style = normalizeStyleForWorkbook(parseJsonMaybe(f.style, {}));
  const ct = style.cellType || {};
  const formatterType = parseJsonMaybe(f.formatterType, ct.formatterType || ['common']);
  if (!ct.typeName && f.cellType === 'Field') {
    style.cellType = {
      ...ct,
      typeName: 'FieldCellType',
      cellType: 'Field',
      name: f.name,
      nameIndex: f.nameIndex,
      text: f.text,
      dataSetId: f.dataSetId,
      fieldKey: f.fieldKey,
      leftX: f.leftX,
      leftY: f.leftY,
      topX: f.topX,
      topY: f.topY,
      expandType: f.expandType,
      displayType: f.displayType,
      countType: f.countType || 'count',
      // 日期分组 / 排序 / 数字格式 key — 设计器回显依赖；禁止重建时丢掉
      groupType: f.groupType !== undefined ? f.groupType : ct.groupType,
      orderType: f.orderType != null ? f.orderType : ct.orderType || 'no',
      formatterType,
      subordination: parseJsonMaybe(f.subordination, ['', '']),
      leftFilterField: parseJsonMaybe(f.leftFilterField, []),
      topFilterField: parseJsonMaybe(f.topFilterField, []),
      // 「转换」面板 — cell-transform-guide.md；重建禁止丢掉
      transType: f.transType != null ? f.transType : ct.transType || 'default',
      browserType: parseJsonMaybe(f.browserType, ct.browserType || []),
      transSelectOptions: parseJsonMaybe(f.transSelectOptions, ct.transSelectOptions || []),
      isHtml: f.isHtml != null ? String(f.isHtml) : ct.isHtml != null ? String(ct.isHtml) : '0',
      qrcodeType: f.qrcodeType || ct.qrcodeType || 'no',
      qrcodelink: f.qrcodelink != null ? String(f.qrcodelink) : ct.qrcodelink != null ? String(ct.qrcodelink) : '0',
      prefixAndSuffix: parseJsonMaybe(f.prefixAndSuffix, ct.prefixAndSuffix || ['', '']),
      hiddenContext:
        f.hiddenContext != null
          ? String(f.hiddenContext)
          : ct.hiddenContext != null
            ? String(ct.hiddenContext)
            : '0',
      textDirection: f.textDirection || ct.textDirection || 'FromLeftToRight',
      // 事件超链接 — Field 与 Const 一样必须写入 cellType，否则预览/点击不生效
      pcHreflink: f.pcHreflink != null ? f.pcHreflink : ct.pcHreflink || '',
      h5Hreflink: f.h5Hreflink != null ? f.h5Hreflink : ct.h5Hreflink || '',
      openType: f.openType || ct.openType || 'blank',
    };
  } else if (f.cellType === 'Field' && style.cellType && typeof style.cellType === 'object') {
    // style 已有 cellType 时仍透传 groupType / formatterType / 转换面板键
    if (f.groupType !== undefined) style.cellType.groupType = f.groupType;
    if (f.orderType != null) style.cellType.orderType = f.orderType;
    style.cellType.formatterType = formatterType;
    if (f.transType != null) style.cellType.transType = f.transType;
    if (f.browserType != null) style.cellType.browserType = parseJsonMaybe(f.browserType, []);
    if (f.transSelectOptions != null)
      style.cellType.transSelectOptions = parseJsonMaybe(f.transSelectOptions, []);
    if (f.isHtml != null) style.cellType.isHtml = String(f.isHtml);
    if (f.qrcodeType != null) style.cellType.qrcodeType = f.qrcodeType;
    if (f.qrcodelink != null) style.cellType.qrcodelink = String(f.qrcodelink);
    if (f.prefixAndSuffix != null)
      style.cellType.prefixAndSuffix = parseJsonMaybe(f.prefixAndSuffix, ['', '']);
    if (f.hiddenContext != null) style.cellType.hiddenContext = String(f.hiddenContext);
    if (f.textDirection != null) style.cellType.textDirection = f.textDirection;
    if (f.pcHreflink != null) style.cellType.pcHreflink = f.pcHreflink;
    if (f.h5Hreflink != null) style.cellType.h5Hreflink = f.h5Hreflink;
    if (f.openType != null) style.cellType.openType = f.openType;
  }
  if (f.cellType === 'Formula' && !ct.typeName) {
    style.cellType = {
      ...ct,
      typeName: 'FormulaCellType',
      cellType: 'Formula',
      cellText: f.cellText,
      leftX: f.leftX,
      leftY: f.leftY,
      topX: f.topX,
      topY: f.topY,
      expandType: f.expandType,
      displayType: f.displayType,
      countType: f.countType || 'count',
      groupType: f.groupType !== undefined ? f.groupType : null,
      formatterType,
    };
  }
  if (f.cellType === 'Const') {
    // 服务端从 workbook.cellType 回写父格/超链接；缺 leftX 时 Java int 默认为 0 → 伪自定义 A1
    const prev = style.cellType && typeof style.cellType === 'object' ? style.cellType : {};
    style.cellType = {
      ...prev,
      typeName: 'ConstCellType',
      cellType: 'Const',
      cellText: f.cellText || f.text || prev.cellText || '',
      leftX: f.leftX != null ? f.leftX : prev.leftX != null ? prev.leftX : -1,
      leftY: f.leftY != null ? f.leftY : prev.leftY != null ? prev.leftY : -1,
      topX: f.topX != null ? f.topX : prev.topX != null ? prev.topX : -1,
      topY: f.topY != null ? f.topY : prev.topY != null ? prev.topY : -1,
      refX: f.refX != null ? f.refX : prev.refX != null ? prev.refX : -1,
      refY: f.refY != null ? f.refY : prev.refY != null ? prev.refY : -1,
      expandType: f.expandType || prev.expandType || 'NoExpand',
      displayType: f.displayType || prev.displayType || 'Group',
      pcHreflink: f.pcHreflink != null ? f.pcHreflink : prev.pcHreflink || '',
      h5Hreflink: f.h5Hreflink != null ? f.h5Hreflink : prev.h5Hreflink || '',
      openType: f.openType || prev.openType || 'blank',
      inheritParent:
        f.inheritParent != null
          ? String(f.inheritParent)
          : prev.inheritParent != null
            ? String(prev.inheritParent)
            : '0',
    };
  }
  // tag.formatterType 与 fields.formatterType 必须一致，否则工具栏数字格式回显错误（见 cell-config-echo-guide.md）
  const tag = { formatterType };
  // 冻结锚点：服务端从 cell.tag.fixed 回写 field.fixed；预览靠 fixed==1 算冻结坐标
  if (f.fixed == 1 || f.fixed === true || (f.tag && (f.tag.fixed === true || f.tag.fixed === 1))) {
    tag.fixed = true;
  }
  const cell = { style, tag };
  if (f.cellType === 'Formula' && f.cellText) cell.formula = f.cellText;
  // 列/行显隐与宽高：隐藏列依赖 cell.colVisible=0（见 WorkSheet columns）
  if (f.width != null && f.width !== '') cell.width = Number(f.width);
  if (f.height != null && f.height !== '') cell.height = Number(f.height);
  if (f.colVisible != null && f.colVisible !== '') cell.colVisible = Number(f.colVisible);
  if (f.rowVisible != null && f.rowVisible !== '') cell.rowVisible = Number(f.rowVisible);
  // 合并单元格：fields.xCount/yCount → cell.rowCount/colCount；缺则合并会在重建 workbook 时被拆掉
  const rc = Math.max(1, Number(f.xCount) || 1);
  const cc = Math.max(1, Number(f.yCount) || 1);
  if (rc > 1 || cc > 1) {
    cell.rowCount = rc;
    cell.colCount = cc;
  }
  return cell;
}

function buildSpansFromFields(fields) {
  const spans = [];
  for (const f of fields || []) {
    const rc = Math.max(1, Number(f.xCount) || 1);
    const cc = Math.max(1, Number(f.yCount) || 1);
    if (rc > 1 || cc > 1) {
      spans.push({ row: Number(f.x), col: Number(f.y), rowCount: rc, colCount: cc });
    }
  }
  return spans;
}

function buildWorkbookFromFields(fields, sheetProps, patchFn) {
  const sp = (sheetProps && sheetProps[0]) || {};
  const dataTable = {};
  for (const f of fields) {
    const x = String(f.x);
    const y = String(f.y);
    if (!dataTable[x]) dataTable[x] = {};
    dataTable[x][y] = fieldToCell(f);
  }
  const wb = {
    version: '11.1.0',
    sheetCount: 1,
    newTabVisible: false,
    tabEditable: false,
    sheets: {
      Sheet1: {
        name: sp.name || 'Sheet1',
        rowCount: 200,
        columnCount: 30,
        activeRow: 1,
        activeCol: 5,
        // 禁止写 gridline/__gridline：workbook 存在 gridline 键 → saveReportDevInfo 500
        spans: buildSpansFromFields(fields),
        data: { dataTable },
      },
    },
  };
  if (typeof patchFn === 'function') patchFn(wb);
  return wb;
}

/** 保存前剔除 workbook sheet 上的 gridline 族键（存在即 500） */
function stripWorkbookGridlineKeys(wb) {
  if (!wb || !wb.sheets) return wb;
  for (const sh of Object.values(wb.sheets)) {
    if (!sh || typeof sh !== 'object') continue;
    delete sh.gridline;
    delete sh.gridLine;
    delete sh.__gridline;
  }
  return wb;
}

/**
 * Build workbook for saveReportDevInfo without wiping layout.
 * @param {object} devData - getReportDevInfo.data
 * @param {function} [patchFn] - optional (wb) => void
 */
function mergeWorkbookSafe(devData, patchFn) {
  const fields = devData?.fields || [];
  const props = devData?.workbookProps;
  const propCells = props ? countWorkbookCells(props) : 0;

  let wb;
  if (props && props.sheets && propCells > 0) {
    wb = JSON.parse(JSON.stringify(props));
  } else {
    if (!fields.length) {
      throw new Error(
        'Layout guard: report has no fields and workbook is empty — refusing saveReportDevInfo. ' +
          'Use rollbackReport or restore_report_from_version.js first.'
      );
    }
    wb = buildWorkbookFromFields(fields, devData?.sheetProps, null);
  }
  if (typeof patchFn === 'function') patchFn(wb);

  stripWorkbookGridlineKeys(wb);

  // 防设计区空白：showLocation 禁止 0；残缺滑动分页强制关闭；snapshot 雪花 ID 禁止 number
  for (const sh of Object.values(wb.sheets || {})) {
    if (!sh.tag) sh.tag = {};
    const loc = sh.tag.showLocation;
    if (loc == null || loc === 0 || loc === '0') {
      sh.tag.showLocation = 2;
    }
    const split = sh.tag.allPageSetting || sh.tag.pageSetting;
    if (split && typeof split === 'object') {
      const scroll = String(split.scrollPage == null ? '0' : split.scrollPage);
      const content = split.scrollContentField;
      const emptyContent =
        content == null ||
        content === '' ||
        (Array.isArray(content) && content.length === 0);
      if (scroll === '1' && emptyContent) {
        split.scrollPage = '0';
      }
    }
  }
  if (wb.snapshot && typeof wb.snapshot === 'object') {
    for (const k of ['sheetId', 'id', 'jobId']) {
      if (wb.snapshot[k] != null && typeof wb.snapshot[k] === 'number') {
        throw new Error(
          `Blank guard: snapshot.${k} is number (${wb.snapshot[k]}) — refuse save. Use String(snowflakeId); Number() truncates and blanks the designer.`
        );
      }
    }
  }

  return wb;
}

function encodeWorkbook(obj) {
  return zlib.gzipSync(Buffer.from(JSON.stringify(obj), 'utf8'), { level: 9, memLevel: 8 }).toString('base64');
}

function assertLayoutNotEmptyBeforeSave(devData, { allowEmpty = false } = {}) {
  const fields = devData?.fields || [];
  const cells = countWorkbookCells(devData?.workbookProps);
  if (allowEmpty) return { fields: fields.length, cells };
  if (fields.length === 0 && cells === 0) {
    throw new Error('Layout guard: fields and workbook cells are both empty — aborting save');
  }
  return { fields: fields.length, cells };
}

function verifyLayoutPreserved(before, after, { minFields } = {}) {
  const afterFields = (after?.fields || []).length;
  const floor = minFields != null ? minFields : before.fields;
  if (afterFields < floor) {
    throw new Error(
      `Layout guard: fields dropped from ${before.fields} to ${afterFields}. ` +
        'Run rollbackReport immediately.'
    );
  }
  return { fields: afterFields, ok: true };
}

function eteamsId() {
  return require('./eb_auth.js').eteamsId();
}

function apiHeaders(host, et, reportId, appId) {
  return {
    eteamsid: et,
    ebBusinessId: appId || '',
    Cookie: `langType=zh_CN; LOGIN_TYPE=pc_account; ETEAMSID=${et}`,
    Accept: 'application/json',
    Referer: `${host}/sp/edc/report/designer/${reportId}`,
    'User-Agent': 'Mozilla/5.0 AgentType=WorkBuddy,IsAgent=true',
  };
}

function buildMultipart(fieldsObj) {
  const boundary = `----SafeReportSave${Date.now()}`;
  const parts = [];
  for (const [k, v] of Object.entries(fieldsObj)) {
    parts.push(`--${boundary}\r\nContent-Disposition: form-data; name="${k}"\r\n\r\n${v}\r\n`);
  }
  parts.push(`--${boundary}--\r\n`);
  return {
    body: Buffer.from(parts.join(''), 'utf8'),
    contentType: `multipart/form-data; boundary=${boundary}`,
  };
}

function request(method, url, body, headers) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const r = https.request(
      { method, hostname: u.hostname, port: u.port || 443, path: u.pathname + u.search, headers, rejectUnauthorized: false },
      (res) => {
        let b = '';
        res.on('data', (c) => (b += c));
        res.on('end', () => {
          try {
            resolve({ status: res.statusCode, json: JSON.parse(b), raw: b });
          } catch {
            resolve({ status: res.statusCode, raw: b });
          }
        });
      }
    );
    r.on('error', reject);
    if (body) r.write(body);
    r.end();
  });
}

async function getReportDevInfo(host, reportId, appId) {
  const et = eteamsId();
  const url = `${host}/api/bs/edc/report/getReportDevInfo?reportId=${reportId}`;
  const { json } = await request('GET', url, null, apiHeaders(host, et, reportId, appId));
  if (json.code !== 200) throw new Error(`getReportDevInfo failed: ${json.msg}`);
  return { et, data: json.data || {}, raw: json };
}

async function saveReportDevInfo(host, { reportId, appId, name, designKey, workbookB64, et, groupId, nameLabelId }) {
  // groupId / nameLabelId：优先用调用方传入（通常来自 baseInfo 原值），禁止脚本擅自硬编码改分组
  const { body, contentType } = buildMultipart({
    groupId: groupId != null && groupId !== '' ? String(groupId) : '0',
    appId,
    reportId,
    name,
    nameLabelId: nameLabelId != null && nameLabelId !== '' ? String(nameLabelId) : '-1',
    designKey,
    workbook: workbookB64,
  });
  const url = `${host}/api/bs/edc/report/saveReportDevInfo`;
  return request('POST', url, body, {
    ...apiHeaders(host, et, reportId, appId),
    'Content-Type': contentType,
    'Content-Length': body.length,
  });
}

/**
 * Safe saveReportDevInfo: merge workbook, save, verify fields not dropped.
 */
async function safeSaveReportDevInfo(host, { reportId, appId, name, designKey, devData, patchFn, et, groupId, nameLabelId }) {
  const before = assertLayoutNotEmptyBeforeSave(devData);
  const wb = mergeWorkbookSafe(devData, patchFn);
  // 空 workbook 门禁：重建后仍无 cell 则拒绝保存
  if (countWorkbookCells(wb) < 1 && (devData?.fields || []).length > 0) {
    throw new Error(
      'Layout guard: rebuilt workbook has 0 cells while fields exist — refuse save. Rebuild from fields with spans.'
    );
  }
  const wb64 = encodeWorkbook(wb);
  const sessionEt = et || eteamsId();
  // 未显式传入时，尝试从 sheet/base 上下文外的调用方负责；此处默认 0/-1 仅作兜底
  const res = await saveReportDevInfo(host, {
    reportId,
    appId,
    name,
    designKey,
    workbookB64: wb64,
    et: sessionEt,
    groupId,
    nameLabelId,
  });
  if (res.json?.code !== 200) {
    throw new Error(`saveReportDevInfo failed: ${res.json?.msg || res.raw}`);
  }
  const afterFetch = await getReportDevInfo(host, reportId, appId);
  verifyLayoutPreserved(before, afterFetch.data, { minFields: before.fields });
  return { before, after: afterFetch.data, saveResponse: res.json };
}

module.exports = {
  parseJsonMaybe,
  countWorkbookCells,
  fieldToCell,
  buildSpansFromFields,
  buildWorkbookFromFields,
  stripWorkbookGridlineKeys,
  mergeWorkbookSafe,
  encodeWorkbook,
  assertLayoutNotEmptyBeforeSave,
  verifyLayoutPreserved,
  getReportDevInfo,
  saveReportDevInfo,
  safeSaveReportDevInfo,
  buildMultipart,
  apiHeaders,
  request,
  DEFAULT_HOST,
};
