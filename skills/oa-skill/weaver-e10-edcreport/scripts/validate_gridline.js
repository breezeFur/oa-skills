#!/usr/bin/env node
/**
 * 网格线门禁 — 默认关闭；workbook 禁止出现 gridline 键（存在即 saveReportDevInfo 500）
 *
 * 实测（固化）：saveReportDevInfo 曾 500「报表内部错误」，二分定位为 workbook sheet
 * 多写了 `gridline` 字段（**存在即 500**），去掉后恢复。新建/改表禁止再写入。
 *
 * 合法开关仅在 sheetProps / pageSetting：
 *   gridLine: int 0|1（默认 0 = 关闭）
 *
 * Usage:
 *   node validate_gridline.js --inline '{"sheetProps":[{"gridLine":0}]}'
 *   node validate_gridline.js --file patch.json [--strict] [--fix]
 *   node validate_gridline.js --report-id <id> [appId]
 *
 * Exit 0 = PASS（可有 warnings）；errors → exit 1
 */
'use strict';

const fs = require('fs');

const https = require('https');
const { resolveE10Host } = require('./resolve_e10_host');

/** workbook sheet 上这些键一旦出现 → saveReportDevInfo 500 风险 */
const FORBIDDEN_WORKBOOK_KEYS = ['gridline', 'gridLine', '__gridline'];

function parseArgs(argv) {
  const o = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const key = a.slice(2);
      const next = argv[i + 1];
      if (!next || next.startsWith('--')) o[key] = true;
      else {
        o[key] = next;
        i++;
      }
    } else o._.push(a);
  }
  return o;
}

function isPlainObject(v) {
  return v != null && typeof v === 'object' && !Array.isArray(v);
}

/** 从 workbook / sheets 树删除禁止键；返回删除计数 */
function stripForbiddenWorkbookKeys(root) {
  let removed = 0;
  const sheets = root?.sheets || root?.workbookProps?.sheets;
  if (!sheets || !isPlainObject(sheets)) return { removed, sheets: sheets || null };
  const out = {};
  for (const [name, sheet] of Object.entries(sheets)) {
    if (!isPlainObject(sheet)) {
      out[name] = sheet;
      continue;
    }
    const next = { ...sheet };
    for (const k of FORBIDDEN_WORKBOOK_KEYS) {
      if (Object.prototype.hasOwnProperty.call(next, k)) {
        delete next[k];
        removed++;
      }
    }
    out[name] = next;
  }
  return { removed, sheets: out };
}

/** sheetProps / pageSetting：gridLine 必须是 0|1 int */
function validateSheetPropGridLine(value, path, { strictDefaultOff } = {}) {
  const errors = [];
  const warnings = [];
  let normalized = 0;

  if (value == null || value === '') {
    return { ok: true, errors, warnings, normalized: 0 };
  }
  if (isPlainObject(value) || Array.isArray(value)) {
    errors.push(
      `${path}=${JSON.stringify(value)}：禁止对象/数组。仅允许 int 0|1（默认 0）`
    );
    return { ok: false, errors, warnings, normalized: 0 };
  }
  if (typeof value === 'boolean') {
    normalized = value ? 1 : 0;
    warnings.push(`${path} 为 boolean，已规范为 ${normalized}；请写 int 0|1`);
  } else if (typeof value === 'string' && /^(0|1)$/.test(value.trim())) {
    normalized = Number(value.trim());
    warnings.push(`${path} 为字符串 "${value}"，已规范为 ${normalized}`);
  } else if (typeof value === 'number' && (value === 0 || value === 1)) {
    normalized = value;
  } else {
    errors.push(`${path}=${JSON.stringify(value)} 非法：仅允许 0 或 1`);
    return { ok: false, errors, warnings, normalized: 0 };
  }

  if (normalized === 1) {
    const msg = `${path}=1：网格线默认关闭；未点名开启时请写 0（feature-map §4.6.1）`;
    if (strictDefaultOff) errors.push(msg);
    else warnings.push(msg);
  }
  return { ok: errors.length === 0, errors, warnings, normalized };
}

function validateWorkbookSheetRoot(sheet, sheetKey) {
  const errors = [];
  const warnings = [];
  const path = `sheets.${sheetKey}`;

  for (const k of FORBIDDEN_WORKBOOK_KEYS) {
    if (Object.prototype.hasOwnProperty.call(sheet, k)) {
      errors.push(
        `${path}.${k} 禁止出现在 workbook 中：saveReportDevInfo 曾因此 500「报表内部错误」` +
          `（二分：存在即 500，去掉即恢复）。网格线只写 sheetProps/pageSetting.gridLine=0|1`
      );
    }
  }
  return { ok: errors.length === 0, errors, warnings };
}

function walkPageSetting(pageSetting, opts) {
  const errors = [];
  const warnings = [];
  const normalized = Array.isArray(pageSetting)
    ? []
    : isPlainObject(pageSetting)
      ? {}
      : pageSetting;

  if (pageSetting == null) return { ok: true, errors, warnings, normalized: null };

  const items = Array.isArray(pageSetting)
    ? pageSetting.map((x, i) => [String(i), x])
    : isPlainObject(pageSetting)
      ? Object.entries(pageSetting)
      : [];

  for (const [k, item] of items) {
    if (!isPlainObject(item)) continue;
    if (item.gridLine != null) {
      const r = validateSheetPropGridLine(item.gridLine, `pageSetting[${k}].gridLine`, opts);
      errors.push(...r.errors);
      warnings.push(...r.warnings);
      if (Array.isArray(normalized)) {
        normalized[Number(k)] = { ...item, gridLine: r.normalized };
      } else {
        normalized[k] = { ...item, gridLine: r.normalized };
      }
    }
  }
  return { ok: errors.length === 0, errors, warnings, normalized };
}

/**
 * @param {object} obj
 * @param {{ strictDefaultOff?: boolean }} opts
 */
function validateGridlinePayload(obj, opts = {}) {
  const errors = [];
  const warnings = [];
  const normalized = {};
  if (!obj || typeof obj !== 'object') {
    return { ok: true, errors, warnings, normalized: null };
  }

  const props = obj.sheetProps;
  if (Array.isArray(props)) {
    normalized.sheetProps = props.map((p, i) => {
      if (!isPlainObject(p)) return p;
      const next = { ...p };
      if (p.gridLine != null) {
        const r = validateSheetPropGridLine(p.gridLine, `sheetProps[${i}].gridLine`, opts);
        errors.push(...r.errors);
        warnings.push(...r.warnings);
        next.gridLine = r.normalized;
      }
      return next;
    });
  } else if (isPlainObject(props) && props.gridLine != null) {
    const r = validateSheetPropGridLine(props.gridLine, 'sheetProps.gridLine', opts);
    errors.push(...r.errors);
    warnings.push(...r.warnings);
    normalized.sheetProps = { ...props, gridLine: r.normalized };
  }

  if (obj.gridLine != null && !obj.sheetProps && !obj.sheets) {
    const r = validateSheetPropGridLine(obj.gridLine, 'gridLine', opts);
    errors.push(...r.errors);
    warnings.push(...r.warnings);
    normalized.gridLine = r.normalized;
  }

  if (obj.pageSetting != null) {
    const r = walkPageSetting(obj.pageSetting, opts);
    errors.push(...r.errors);
    warnings.push(...r.warnings);
    if (r.normalized) normalized.pageSetting = r.normalized;
  }

  const sheets = obj.sheets || obj.workbookProps?.sheets;
  if (sheets && isPlainObject(sheets)) {
    const stripped = stripForbiddenWorkbookKeys({ sheets });
    normalized.sheets = stripped.sheets;
    for (const [name, sheet] of Object.entries(sheets)) {
      if (!isPlainObject(sheet)) continue;
      const r = validateWorkbookSheetRoot(sheet, name);
      errors.push(...r.errors);
      warnings.push(...r.warnings);
    }
    if (stripped.removed > 0) {
      warnings.push(
        `--fix 将删除 workbook 内 ${stripped.removed} 个禁止键（gridline/gridLine/__gridline）`
      );
    }
  }

  return { ok: errors.length === 0, errors, warnings, normalized };
}

function eteamsId() {
  return require('./eb_auth.js').eteamsId();
}

function request(host, method, urlPath, headers) {
  return new Promise((resolve, reject) => {
    const u = new URL(host + urlPath);
    const r = https.request(
      {
        method,
        hostname: u.hostname, port: u.port || 443, path: u.pathname + u.search,
        headers,
        rejectUnauthorized: false,
      },
      (res) => {
        let d = '';
        res.on('data', (c) => (d += c));
        res.on('end', () => {
          try {
            resolve(JSON.parse(d));
          } catch {
            resolve({ raw: d.slice(0, 300) });
          }
        });
      }
    );
    r.on('error', reject);
    r.end();
  });
}

async function verifyReport(reportId, appId, opts) {
  const host = resolveE10Host();
  const et = eteamsId();
  const headers = {
    eteamsid: et,
    ebBusinessId: appId || '',
    Cookie: `langType=zh_CN; LOGIN_TYPE=pc_account; ETEAMSID=${et}`,
    Accept: 'application/json',
    Referer: `${host}/sp/edc/report/designer/${reportId}`,
    'User-Agent': 'Mozilla/5.0 AgentType=WorkBuddy,IsAgent=true',
  };
  const base = await request(
    host,
    'GET',
    `/api/bs/edc/report/baseInfo?id=${reportId}&useTag=backend`,
    headers
  );
  appId = String(base.data?.appId || appId || '');
  headers.ebBusinessId = appId;
  const info = await request(
    host,
    'GET',
    `/api/bs/edc/report/getReportDevInfo?reportId=${reportId}`,
    headers
  );
  const page = await request(
    host,
    'GET',
    `/api/bs/edc/report/allPageSetting?sheetId=${reportId}`,
    headers
  );

  const data = info.data || {};
  return validateGridlinePayload(
    {
      sheetProps: data.sheetProps || [],
      pageSetting: page.data || [],
      sheets: data.workbookProps?.sheets,
    },
    opts
  );
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const opts = { strictDefaultOff: Boolean(args.strict) };

  if (args.inline || args.file) {
    let raw = args.file ? fs.readFileSync(args.file, 'utf8') : String(args.inline);
    if (raw.charCodeAt(0) === 0xfeff) raw = raw.slice(1);
    const obj = JSON.parse(raw);
    const result = validateGridlinePayload(obj, opts);
    const out = args.fix
      ? { ...result, fixed: result.normalized }
      : result;
    console.log(JSON.stringify(out, null, 2));
    process.exit(result.ok ? 0 : 1);
  }

  const reportId = args['report-id'] || args._[0];
  const appId = args['app-id'] || args._[1];
  if (!reportId) {
    console.error(
      'Usage: validate_gridline.js --inline "{...}" | --file patch.json | --report-id <id> [appId] [--strict] [--fix]'
    );
    process.exit(2);
  }

  verifyReport(reportId, appId, opts).then((r) => {
    console.log(JSON.stringify(r, null, 2));
    process.exit(r.ok ? 0 : 1);
  });
}

module.exports = {
  FORBIDDEN_WORKBOOK_KEYS,
  stripForbiddenWorkbookKeys,
  validateSheetPropGridLine,
  validateGridlinePayload,
};

if (require.main === module) main();
