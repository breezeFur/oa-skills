#!/usr/bin/env node
/**
 * 单元格配置回显校验 / 规范化 — references/cell-config-echo-guide.md
 *
 * Usage:
 *   node validate_cell_config_echo.js --map "货币"
 *   node validate_cell_config_echo.js --map "年份"
 *   node validate_cell_config_echo.js --file cell.json
 *   node validate_cell_config_echo.js --inline '{"formatter":"¥#,##0.00"}'
 *   node validate_cell_config_echo.js --report-id <id> [appId]
 *   node validate_cell_config_echo.js --list
 *
 * Exit 0 = PASS（可有 warnings）；errors → exit 1
 */
'use strict';

const fs = require('fs');

const https = require('https');
const { resolveE10Host } = require('./resolve_e10_host');

/** 设计器数字格式目录（main.js g()） */
const FORMAT_CATALOG = [
  { label: '常规', formatter: 'General', key1: 'common' },
  { label: '数值', formatter: '0.00_);[Red](0.00)', key1: 'value' },
  {
    label: '货币',
    formatter: '"\uFFE5"#,##0.00_);[Red]("\uFFE5"#,##0.00)',
    key1: 'huobi',
  },
  {
    label: '会计专用',
    formatter: '_ "\uFFE5"* #,##0.00_ ;_ "\uFFE5"* -#,##0.00_ ;_ "\uFFE5"* "-"??_ ;_ @_ ',
    key1: 'kuaiji',
  },
  { label: '短日期', formatter: 'yyyy/m/d;@__@', key1: 'shortdate' },
  { label: '长日期', formatter: 'yyyy"年"m"月"d"日";@', key1: 'longdate' },
  { label: '时间', formatter: 'h:mm:ss;@', key1: 'time' },
  { label: '百分比', formatter: '0.00%', key1: 'percent' },
  { label: '分数', formatter: '# ?/?', key1: 'fenshu' },
  { label: '科学计数法', formatter: '0.00E+00', key1: 'kexuejishu' },
  { label: '文本', formatter: '@', key1: 'text' },
];

const GROUP_TYPES = {
  不设置: 'none',
  无: 'none',
  none: 'none',
  年份: 'year',
  年: 'year',
  year: 'year',
  年月: 'yearmonth',
  yearmonth: 'yearmonth',
  yearAndMonth: 'yearmonth', // UI 别名 → 落库
  月份: 'month',
  month: 'month',
  年月日: 'yearmonthday',
  yearmonthday: 'yearmonthday',
  年周: 'yearweekday',
  yearweekday: 'yearweekday',
  月周: 'monthweekday',
  monthweekday: 'monthweekday',
};

/** 常见错误货币串 → 规范化 */
const FORMAT_ALIASES = [
  { test: /^(¥|￥|\$)?#,##0(\.00)?$/, key1: 'huobi' },
  { test: /^¥#,##0\.00$/, key1: 'huobi' },
  { test: /huobi/i, key1: 'huobi' },
  { test: /^货币$/, key1: 'huobi' },
  { test: /^百分比|percent$/i, key1: 'percent' },
  { test: /^数值|number$/i, key1: 'value' },
  { test: /^常规|general$/i, key1: 'common' },
  { test: /^文本|text$/i, key1: 'text' },
];

/** 设计器常见字号（Spread 下拉）；不在列表则 warning + 默认 12 */
const SUPPORTED_FONT_SIZES = new Set([8, 9, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 36, 48, 72]);
const DEFAULT_FONT_SIZE = 12;
const SUPPORTED_FONTS = new Set([
  '微软雅黑',
  '宋体',
  '黑体',
  '楷体',
  '仿宋',
  'Arial',
  'Calibri',
  'Times New Roman',
  'Tahoma',
  'Verdana',
  'sans-serif',
]);
const DEFAULT_FONT = '微软雅黑';

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

function parseMaybe(v, fb) {
  if (v == null || v === '') return fb;
  if (typeof v === 'object') return v;
  try {
    return JSON.parse(v);
  } catch {
    return fb;
  }
}

function findFormatByKey1(key1) {
  return FORMAT_CATALOG.find((x) => x.key1 === key1);
}

function findFormatByFormatter(fmt) {
  return FORMAT_CATALOG.find((x) => x.formatter === fmt);
}

/**
 * 规范化数字格式；返回 { ok, errors, warnings, normalized }
 */
function normalizeNumberFormat(input) {
  const errors = [];
  const warnings = [];
  let formatter = input.formatter != null ? String(input.formatter) : '';
  let formatterType = parseMaybe(input.formatterType, null);
  if (typeof formatterType === 'string') formatterType = [formatterType];

  const mapLabel = input.map || input.label || '';
  if (mapLabel) {
    const hit =
      FORMAT_CATALOG.find((x) => x.label === mapLabel) ||
      FORMAT_CATALOG.find((x) => x.key1 === mapLabel) ||
      findFormatByKey1(
        (FORMAT_ALIASES.find((a) => a.test.test(String(mapLabel))) || {}).key1
      );
    if (!hit) {
      errors.push(`无法映射数字格式「${mapLabel}」到设计器目录`);
      return { ok: false, errors, warnings, normalized: null };
    }
    return {
      ok: true,
      errors,
      warnings,
      normalized: { formatter: hit.formatter, formatterType: [hit.key1], label: hit.label },
    };
  }

  // 已是目录全等
  const byId = findFormatByFormatter(formatter);
  if (byId) {
    const ft0 = Array.isArray(formatterType) && formatterType[0] ? formatterType[0] : byId.key1;
    if (ft0 !== byId.key1) {
      warnings.push(
        `formatter 已是「${byId.label}」目录值，但 formatterType[0]=${ft0}，已规范为 ${byId.key1}（否则工具栏可能回显错误）`
      );
    }
    return {
      ok: true,
      errors,
      warnings,
      normalized: { formatter: byId.formatter, formatterType: [byId.key1], label: byId.label },
    };
  }

  // 别名纠正
  for (const a of FORMAT_ALIASES) {
    if (a.test.test(formatter) || a.test.test(String(mapLabel))) {
      const hit = findFormatByKey1(a.key1);
      warnings.push(
        `formatter「${formatter}」不是设计器目录全等值，已规范为「${hit.label}」（否则工具栏回显为常规）`
      );
      return {
        ok: true,
        errors,
        warnings,
        normalized: { formatter: hit.formatter, formatterType: [hit.key1], label: hit.label },
      };
    }
  }

  if (formatter && formatter !== 'General' && formatter !== '') {
    warnings.push(
      `formatter「${formatter}」未在标准目录中，将按「其他数字格式」(custom) 回显；若要工具栏显示「货币」等，请改用目录全等值`
    );
    return {
      ok: true,
      errors,
      warnings,
      normalized: {
        formatter,
        formatterType: Array.isArray(formatterType) && formatterType[0] ? formatterType : ['custom'],
        label: '其他数字格式',
      },
    };
  }

  return {
    ok: true,
    errors,
    warnings,
    normalized: { formatter: 'General', formatterType: ['common'], label: '常规' },
  };
}

function normalizeGroupType(input) {
  const errors = [];
  const warnings = [];
  const raw = input.groupType != null ? String(input.groupType) : input.map || input.label || '';
  if (!raw) {
    return { ok: true, errors, warnings, normalized: { groupType: 'none', label: '不设置' } };
  }
  const mapped = GROUP_TYPES[raw] || GROUP_TYPES[raw.trim()];
  if (!mapped) {
    errors.push(
      `无法映射日期分组「${raw}」。支持：不设置/年份/年月/月份/年月日/年周/月周（或 year/yearmonth/...）`
    );
    return { ok: false, errors, warnings, normalized: null };
  }
  if (raw === 'yearAndMonth') {
    warnings.push('UI 别名 yearAndMonth 已规范为落库值 yearmonth');
  }
  const label =
    Object.keys(GROUP_TYPES).find((k) => GROUP_TYPES[k] === mapped && /[\u4e00-\u9fff]/.test(k)) ||
    mapped;
  return { ok: true, errors, warnings, normalized: { groupType: mapped, label } };
}

function normalizeFont(input) {
  const warnings = [];
  const errors = [];
  let fontFamily = input.fontFamily || input.font || '';
  let fontSize = input.fontSize != null ? Number(input.fontSize) : null;
  // parse from CSS font string "italic bold 10px 微软雅黑"
  if (typeof input.font === 'string' && /\d+px/.test(input.font)) {
    const m = input.font.match(/(\d+(?:\.\d+)?)px\s+(.+)$/);
    if (m) {
      fontSize = Number(m[1]);
      fontFamily = m[2].trim();
    }
  }
  if (fontSize != null && !SUPPORTED_FONT_SIZES.has(fontSize)) {
    warnings.push(
      `报表不支持 ${fontSize} 号字体，已按默认字号 ${DEFAULT_FONT_SIZE} 展示（不中断）`
    );
    fontSize = DEFAULT_FONT_SIZE;
  }
  if (fontFamily && !SUPPORTED_FONTS.has(fontFamily)) {
    warnings.push(`字体「${fontFamily}」不在常用支持列表，已回退为 ${DEFAULT_FONT}（不中断）`);
    fontFamily = DEFAULT_FONT;
  }
  return {
    ok: true,
    errors,
    warnings,
    normalized: {
      fontFamily: fontFamily || DEFAULT_FONT,
      fontSize: fontSize != null ? fontSize : DEFAULT_FONT_SIZE,
    },
  };
}

function validateCellPatch(obj) {
  const errors = [];
  const warnings = [];
  const normalized = {};

  if (obj.wholeSheetStyle || obj.wholeSheetBorder || obj.applyToEntireReport) {
    errors.push(
      '不支持对整个报表全量设置单元格样式或边框样式。请指定区域（如 B3:H5），并提示用户确认范围。'
    );
  }

  if (
    obj.formatter != null ||
    obj.formatterType != null ||
    (obj.map && /货币|数值|常规|百分比|会计|日期|时间|文本|科学|分数/.test(obj.map))
  ) {
    const r = normalizeNumberFormat(obj);
    errors.push(...r.errors);
    warnings.push(...r.warnings);
    if (r.normalized) normalized.numberFormat = r.normalized;
  }

  if (
    obj.groupType != null ||
    (obj.map && /年份|年月|月份|年月日|年周|月周|不设置|year/.test(obj.map))
  ) {
    const r = normalizeGroupType(obj);
    errors.push(...r.errors);
    warnings.push(...r.warnings);
    if (r.normalized) normalized.groupType = r.normalized;
  }

  if (obj.font != null || obj.fontSize != null || obj.fontFamily != null) {
    const r = normalizeFont(obj);
    warnings.push(...r.warnings);
    if (r.normalized) normalized.font = r.normalized;
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

async function verifyReport(reportId, appId) {
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
  if (!appId) {
    const base = await request(host, 'GET', `/api/bs/edc/report/baseInfo?id=${reportId}&useTag=backend`, headers);
    appId = String(base.data?.appId || '');
    headers.ebBusinessId = appId;
  }
  const info = await request(
    host,
    'GET',
    `/api/bs/edc/report/getReportDevInfo?reportId=${reportId}`,
    headers
  );
  const fields = info.data?.fields || [];
  const errors = [];
  const warnings = [];
  const rows = [];

  for (const f of fields) {
    const style = parseMaybe(f.style, {});
    const fmt = style.formatter || '';
    const ft = parseMaybe(f.formatterType, ['common']);
    const ft0 = Array.isArray(ft) ? ft[0] : 'common';
    const issues = [];

    if (fmt && fmt !== 'General' && fmt !== '') {
      const byId = findFormatByFormatter(fmt);
      if (!byId) {
        issues.push(`formatter 非目录全等「${fmt}」→ 工具栏可能显示「其他/常规」`);
      } else if (ft0 !== byId.key1) {
        issues.push(
          `货币等回显断裂：formatter 是「${byId.label}」但 formatterType[0]=${ft0}（应为 ${byId.key1}）`
        );
      }
      // alias trap
      if (/^[¥￥]#,##0/.test(fmt) || fmt === '¥#,##0.00') {
        issues.push('疑似错误货币串 ¥#,##0.00，应使用目录货币 formatter + huobi');
      }
    }

    if (f.groupType && f.groupType !== 'none') {
      if (!Object.values(GROUP_TYPES).includes(f.groupType)) {
        issues.push(`未知 groupType=${f.groupType}`);
      }
      if (f.groupType === 'yearAndMonth') {
        issues.push('groupType=yearAndMonth 应为 yearmonth（落库）');
      }
    }

    if (issues.length) {
      rows.push({
        excel: `${String.fromCharCode(65 + Number(f.y))}${Number(f.x) + 1}`,
        text: f.text || f.cellText,
        formatter: fmt,
        formatterType: ft,
        groupType: f.groupType,
        issues,
      });
      for (const iss of issues) {
        if (/回显断裂|错误货币|yearAndMonth|未知 groupType/.test(iss)) errors.push(`${f.text}: ${iss}`);
        else warnings.push(`${f.text}: ${iss}`);
      }
    }
  }

  return { ok: errors.length === 0, errors, warnings, rows, fieldCount: fields.length };
}

function main() {
  const args = parseArgs(process.argv.slice(2));

  if (args.list) {
    console.log(JSON.stringify({ formats: FORMAT_CATALOG, groupTypes: GROUP_TYPES, fontSizes: [...SUPPORTED_FONT_SIZES] }, null, 2));
    process.exit(0);
  }

  if (args['report-id'] || args._[0]) {
    const reportId = args['report-id'] || args._[0];
    const appId = args['app-id'] || args._[1];
    verifyReport(reportId, appId).then((r) => {
      console.log(JSON.stringify(r, null, 2));
      process.exit(r.ok ? 0 : 1);
    });
    return;
  }

  let input = {};
  if (args.file) input = JSON.parse(fs.readFileSync(args.file, 'utf8'));
  else if (args.inline) input = JSON.parse(args.inline);
  else if (args.map) input = { map: String(args.map) };
  else {
    console.error(
      'Usage: validate_cell_config_echo.js --map "货币"|"年份" | --file cell.json | --report-id <id> | --list'
    );
    process.exit(2);
  }

  const result = validateCellPatch(input);
  console.log(JSON.stringify(result, null, 2));
  process.exit(result.ok ? 0 : 1);
}

module.exports = {
  FORMAT_CATALOG,
  GROUP_TYPES,
  normalizeNumberFormat,
  normalizeGroupType,
  normalizeFont,
  validateCellPatch,
  SUPPORTED_FONT_SIZES,
  DEFAULT_FONT_SIZE,
};

if (require.main === module) main();
