'use strict';
/**
 * 单元格「转换」面板校验 — references/cell-transform-guide.md
 *
 *   node validate_cell_transform.js --map "人员"
 *   node validate_cell_transform.js --map "部门全路径"
 *   node validate_cell_transform.js --map "二维码"
 *   node validate_cell_transform.js --file cell.json
 *   node validate_cell_transform.js --list
 */
const fs = require('fs');

const BROWSER_PRESETS = {
  人员: 'HrmEmployeeComInfo',
  部门: 'HrmDepartmentComInfo',
  部门全路径: 'HrmDepartmentAllPathComInfo',
  '部门（全路径）': 'HrmDepartmentAllPathComInfo',
  HrmEmployeeComInfo: 'HrmEmployeeComInfo',
  HrmDepartmentComInfo: 'HrmDepartmentComInfo',
  HrmDepartmentAllPathComInfo: 'HrmDepartmentAllPathComInfo',
};

const TRANS_MAP = {
  无: { transType: 'default' },
  不转换: { transType: 'default' },
  default: { transType: 'default' },
  none: { transType: 'default', warn: 'none→default（禁止用 none 落库）' },
  人员: { transType: 'browser', browserType: [{ id: 'HrmEmployeeComInfo' }] },
  person: { error: '禁止 transType=person；人员=browser+HrmEmployeeComInfo' },
  hrm: { error: '遗留 hrm 禁止新写；人员=browser+HrmEmployeeComInfo' },
  部门: { transType: 'browser', browserType: [{ id: 'HrmDepartmentComInfo' }] },
  department: { error: '禁止 transType=department；部门=browser+HrmDepartmentComInfo' },
  dept: { error: '遗留 dept 禁止新写；部门=browser+HrmDepartmentComInfo' },
  部门全路径: { transType: 'browser', browserType: [{ id: 'HrmDepartmentAllPathComInfo' }] },
  '部门（全路径）': { transType: 'browser', browserType: [{ id: 'HrmDepartmentAllPathComInfo' }] },
  checkbox: { transType: 'checkbox' },
  Checkbox: { transType: 'checkbox' },
  选择框: { transType: 'select' },
  select: { transType: 'select' },
  颜色选择框: { transType: 'colorSelect' },
  colorSelect: { transType: 'colorSelect' },
  分值图标: { transType: 'scoreIcon' },
  scoreIcon: { transType: 'scoreIcon' },
  斜线文字: { transType: 'slashWord' },
  slashWord: { transType: 'slashWord' },
  关联类型: { transType: 'browser', note: '须另填 browserType（抓包/弹窗）' },
  browser: { transType: 'browser' },
  图片: { transType: 'picture' },
  picture: { transType: 'picture' },
  image: { error: '禁止 image；图片=picture' },
};

const HTML_MAP = { 否: '0', 是: '1', '0': '0', '1': '1', false: '0', true: '1' };
const QR_MAP = {
  无: 'no',
  no: 'no',
  条码: 'barcode',
  barcode: 'barcode',
  二维码: 'qrcode',
  qrcode: 'qrcode',
};
const HIDDEN_MAP = HTML_MAP;
const DIR_MAP = {
  从左向右: 'FromLeftToRight',
  FromLeftToRight: 'FromLeftToRight',
  从右向左: 'FromRightToLeft',
  FromRightToLeft: 'FromRightToLeft',
  竖排: 'VerticalArrangement',
  VerticalArrangement: 'VerticalArrangement',
  顺时针旋转90: 'CW',
  '顺时针旋转90°': 'CW',
  CW: 'CW',
  逆时针旋转90: 'CCW',
  '逆时针旋转90°': 'CCW',
  CCW: 'CCW',
};

function parseArgs(argv) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) out[a.slice(2)] = argv[++i];
    else out._.push(a);
  }
  return out;
}

function normalizeTransform(input) {
  const errors = [];
  const warnings = [];
  const normalized = {};
  const map = input.map != null ? String(input.map).trim() : '';

  // ---- transType from map or explicit ----
  let transType = input.transType;
  let browserType = input.browserType;
  let transSelectOptions = input.transSelectOptions;

  if (map) {
    if (map === '条码' || map === '二维码' || map === 'barcode' || map === 'qrcode') {
      normalized.qrcodeType = QR_MAP[map];
    } else if (map === 'HTML' || map === 'HTML转换' || map === '开启HTML') {
      normalized.isHtml = '1';
    } else if (map === 'html') {
      errors.push('禁止把 html 当 transType；HTML转换用 isHtml="1"');
    } else if (map === '隐藏内容' || map === '隐藏') {
      normalized.hiddenContext = '1';
    } else if (DIR_MAP[map]) {
      normalized.textDirection = DIR_MAP[map];
    } else if (TRANS_MAP[map]) {
      const t = TRANS_MAP[map];
      if (t.error) errors.push(t.error);
      else {
        transType = t.transType;
        if (t.browserType) browserType = t.browserType;
        if (t.warn) warnings.push(t.warn);
        if (t.note) warnings.push(t.note);
      }
    } else if (BROWSER_PRESETS[map]) {
      transType = 'browser';
      browserType = [{ id: BROWSER_PRESETS[map] }];
    } else {
      errors.push(`无法映射「${map}」。见 --list 或 cell-transform-guide.md`);
    }
  }

  if (transType != null) {
    const bad = ['person', 'department', 'image', 'html', 'barcode', 'qrcode', 'hidden', 'none'];
    if (bad.includes(String(transType))) {
      errors.push(`非法 transType=${transType}；见 cell-transform-guide.md`);
    } else {
      normalized.transType = String(transType);
    }
  }

  if (browserType != null) {
    normalized.browserType = Array.isArray(browserType)
      ? browserType
      : typeof browserType === 'string'
        ? JSON.parse(browserType)
        : browserType;
    if (normalized.transType === 'browser' && (!normalized.browserType || !normalized.browserType.length)) {
      warnings.push('transType=browser 但 browserType 为空（关联类型须弹窗/抓包补全）');
    }
  }

  if (transSelectOptions != null) {
    normalized.transSelectOptions = Array.isArray(transSelectOptions)
      ? transSelectOptions
      : typeof transSelectOptions === 'string'
        ? JSON.parse(transSelectOptions)
        : transSelectOptions;
  }

  if (input.isHtml != null || input.html != null) {
    const raw = input.isHtml != null ? input.isHtml : input.html;
    const v = HTML_MAP[String(raw)];
    if (v == null) errors.push(`isHtml 非法: ${raw}（须 0|1 / 否|是）`);
    else normalized.isHtml = v;
  }

  if (input.qrcodeType != null || input.barcode != null) {
    const raw = input.qrcodeType != null ? input.qrcodeType : input.barcode;
    const v = QR_MAP[String(raw)];
    if (v == null) errors.push(`qrcodeType 非法: ${raw}（须 no|barcode|qrcode）`);
    else normalized.qrcodeType = v;
  }

  if (input.qrcodelink != null) {
    const v = HTML_MAP[String(input.qrcodelink)];
    if (v == null) errors.push(`qrcodelink 非法: ${input.qrcodelink}`);
    else normalized.qrcodelink = v;
  }

  if (input.prefixAndSuffix != null) {
    let arr = input.prefixAndSuffix;
    if (typeof arr === 'string') {
      try {
        arr = JSON.parse(arr);
      } catch {
        arr = [arr, ''];
      }
    }
    if (!Array.isArray(arr) || arr.length < 2) {
      errors.push('prefixAndSuffix 须为长度≥2 的数组 ["前缀","后缀"]');
    } else normalized.prefixAndSuffix = [String(arr[0] ?? ''), String(arr[1] ?? '')];
  } else if (input.prefix != null || input.suffix != null) {
    normalized.prefixAndSuffix = [String(input.prefix ?? ''), String(input.suffix ?? '')];
  }

  if (input.hiddenContext != null || input.hideContent != null) {
    if (input.hideContent != null) warnings.push('键名应为 hiddenContext（非 hideContent）');
    const raw = input.hiddenContext != null ? input.hiddenContext : input.hideContent;
    const v = HIDDEN_MAP[String(raw)];
    if (v == null) errors.push(`hiddenContext 非法: ${raw}`);
    else normalized.hiddenContext = v;
  }

  if (input.textDirection != null) {
    const v = DIR_MAP[String(input.textDirection)];
    if (v == null) errors.push(`textDirection 非法: ${input.textDirection}`);
    else normalized.textDirection = v;
  }

  // defaults hint when only map set a trans
  if (normalized.transType && normalized.isHtml == null) normalized.isHtml = normalized.isHtml || undefined;

  return { ok: errors.length === 0, errors, warnings, normalized };
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.list != null || args._[0] === 'list') {
    console.log(
      JSON.stringify(
        {
          transType: Object.keys(TRANS_MAP).filter((k) => !TRANS_MAP[k].error),
          browserPresets: BROWSER_PRESETS,
          isHtml: HTML_MAP,
          qrcodeType: QR_MAP,
          textDirection: DIR_MAP,
          guide: 'references/cell-transform-guide.md',
        },
        null,
        2
      )
    );
    process.exit(0);
  }

  let input = {};
  if (args.file) input = JSON.parse(fs.readFileSync(args.file, 'utf8'));
  else if (args.inline) input = JSON.parse(args.inline);
  else if (args.map) input = { map: String(args.map) };
  else {
    console.error('Usage: validate_cell_transform.js --map "人员"|--file cell.json|--list');
    process.exit(2);
  }

  const result = normalizeTransform(input);
  console.log(JSON.stringify(result, null, 2));
  process.exit(result.ok ? 0 : 1);
}

module.exports = { normalizeTransform, TRANS_MAP, QR_MAP, DIR_MAP, BROWSER_PRESETS };

if (require.main === module) main();
