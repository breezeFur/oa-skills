#!/usr/bin/env node
/**
 * build_from_spec.js —— 声明式一次跑完搭表（禁止空壳 / 禁改名残留）
 *
 *   edc-report build spec --spec <spec.json> [--dry-run] [--form-confirmed] [--source-id <id>]
 *                        [--field-confirmed "标题1,标题2" | --field-confirmed]
 *
 * 流程：应用内定源（exact 直建 / fuzzy 须确认）
 *      → **建表前字段预检**（fieldsBySource；未精确命中 → exit 4，**不建表**）
 *      → 目标名 baseInfo → 本表 addDataset（同源只挂一次）→ fieldsKey（再校验一次）
 *      → saveReportDevInfo（同 reportId）→ 回读（tableName / 显示名一致性 / 重复数据集）
 * 禁止：__build_* / __probe_* 探测壳、跨报表复用 datasetId、落库后再 rename、
 *      字段精确匹配失败时静默兜底到系统字段（如「姓名」→ `name`「标题」）
 *
 * spec.json 结构见 references/spec-build-schema.md
 */
'use strict';

const fs = require('fs');
const path = require('path');
const zlib = require('zlib');
const {
  host,
  get,
  post,
  resolveFormWithPrompt,
  resolveDataset,
  fieldsKeyOf,
  matchField,
  resolveFieldBindings,
  fieldsBySource,
  normText,
  isSystemField,
  deleteReport,
} = require('./spec_lib');
const { resolveLayerStyles } = require('./default_header_style.js');

/** fieldsKey 中某技术名的真实显示名（校验单元格文案用） */
function textByFieldName(fieldsKey, name) {
  const hit = (fieldsKey || []).find((f) => String(f.name) === String(name));
  return hit ? String(hit.text || hit.showName || '') : '';
}

// 数字格式目录（工具栏回显金标准 · cell-config-echo-guide.md §二）
const FORMATS = {
  common: { formatter: 'General', key: 'common' },
  value: { formatter: '0.00_);[Red](0.00)', key: 'value' },
  huobi: { formatter: '"\uFFE5"#,##0.00_);[Red]("\uFFE5"#,##0.00)', key: 'huobi' },
  kuaiji: { formatter: '_ "\uFFE5"* #,##0.00_ ;_ "\uFFE5"* -#,##0.00_ ;_ "\uFFE5"* "-"??_ ;_ @_ ', key: 'kuaiji' },
  shortdate: { formatter: 'yyyy/m/d;@__@', key: 'shortdate' },
  longdate: { formatter: 'yyyy"年"m"月"d"日";@', key: 'longdate' },
  time: { formatter: 'h:mm:ss;@', key: 'time' },
  percent: { formatter: '0.00%', key: 'percent' },
  fenshu: { formatter: '# ?/?', key: 'fenshu' },
  kexuejishu: { formatter: '0.00E+00', key: 'kexuejishu' },
  text: { formatter: '@', key: 'text' },
};
const ALIAS = { 货币: 'huobi', 数值: 'value', 常规: 'common', 会计专用: 'kuaiji', 百分比: 'percent' };

// 设计器字号目录（validate format --list）：pt → px
const FONT_SIZES = [8, 9, 11, 12, 14, 16, 18, 20, 22, 24, 26, 28, 36, 48, 72];
function ptToPx(pt) {
  // 2026-09-09 实测：平台字号 ≈1:1 映射（12号≈12px），不再按 CSS pt×96/72 换算。
  return Number(pt);
}
function normalizeFontPt(pt) {
  const n = Number(pt) || 12;
  if (FONT_SIZES.includes(n)) return n;
  return 12; // 不支持则回退默认 12 号（cell-config-echo-guide.md §五）
}

const DEFAULTS = {
  font: '微软雅黑',
  fontSize: 12,
  bold: false,
  italic: false,
  underline: false,
  foreColor: '#333',
  backColor: '#fff',
  hAlign: 'left', // left|center|right
  vAlign: 'center',
  borderColor: '#999',
};
const HALIGN = { left: 0, center: 1, right: 2 };
const VALIGN = { top: 0, center: 1, bottom: 2 };

function makeStyle(styleSpec) {
  const s = Object.assign({}, DEFAULTS, styleSpec || {});
  const pt = normalizeFontPt(s.fontSize);
  const weight = s.bold ? '700' : '400';
  const style = s.italic ? 'italic' : 'normal';
  const font = `${style} ${weight} ${ptToPx(pt)}px ${s.font}`;
  const border = { color: s.borderColor, style: 1 };
  return {
    backColor: s.backColor,
    backgroundImageLayout: 0,
    borderBottom: border,
    borderLeft: border,
    borderRight: border,
    borderTop: border,
    font,
    foreColor: s.foreColor,
    hAlign: HALIGN[s.hAlign] != null ? HALIGN[s.hAlign] : 0,
    vAlign: VALIGN[s.vAlign] != null ? VALIGN[s.vAlign] : 1,
    textDecoration: s.underline ? 1 : 0,
    textIndent: 0,
    wordWrap: true,
  };
}

function normFormat(fmt) {
  const k = ALIAS[fmt] || fmt || 'common';
  return FORMATS[k] || FORMATS.common;
}

// 数据集后缀：设计器按注册契约在数据源名后追加
//   LOGIC（weaver-ebuilder-form-service，普通应用表单）→ (业务模块)
//   FORM （共享表契约）                              → (表单)
// 服务端不回传时由此兜底，保证 tableName 恒非空。
const DATASET_SUFFIX = { logic: '(业务模块)', form: '(表单)' };
function datasetSuffix(sourceType) {
  return DATASET_SUFFIX[String(sourceType || 'logic').toLowerCase()] || '(业务模块)';
}
function resolveTableName(f) {
  // 1) 已带后缀的完整值 → 直接用
  const full = f.tableName || '';
  if (full && /[（(].+[)）]\s*$/.test(full)) return full;
  if (full) return /[（(].+[)）]\s*$/.test(full) ? full : full + datasetSuffix(f.sourceType);
  // 2) 数据集裸名 + 后缀（datasetName 来自 fieldsKey，可能已是 displayName）
  const base = f.datasetName || f.datasetLabel || f.sourceName || '';
  if (!base) return '';
  // 已含括号则由 datasetSuffix 之外的后缀保留
  if (/[（(].+[)）]\s*$/.test(base)) return base;
  return base + datasetSuffix(f.sourceType);
}

function constCell(text, style, { left, rowCount, colCount, fixed }) {
  const st = makeStyle(style);
  st.cellType = {
    typeName: 'ConstCellType',
    cellType: 'Const',
    cellText: text,
    leftX: left[0],
    leftY: left[1],
    topX: -1,
    topY: -1,
    refX: -1,
    refY: -1,
    expandType: 'NoExpand',
    displayType: 'Group',
    countType: 'count',
    groupType: null,
    orderType: 'no',
    formatterType: ['common'],
    subordination: ['', ''],
    pcHreflink: '',
    h5Hreflink: '',
    openType: 'blank',
    inheritParent: '0',
    isActiveParent: false,
    arrowType: 'None',
    textDirection: 'FromLeftToRight',
    allowOverflow: true,
    hiddenContext: '0',
    transSelectOptions: [],
    browserType: [],
    thumbnail: 'NoDisplay',
    conditionRule: {},
  };
  const cell = { style: st, tag: { formatterType: ['common'] } };
  if (fixed) cell.tag.fixed = true; // 冻结锚点 → 服务端回写 field.fixed=1
  if (rowCount > 1 || colCount > 1) {
    cell.rowCount = rowCount;
    cell.colCount = colCount;
  }
  return cell;
}

function fieldCell(f, style, { text, left, isRoot, fmtKey, groupType, conditionRule }) {
  const st = makeStyle(style);
  const fmt = FORMATS[fmtKey] || FORMATS.common;
  st.formatter = fmt.formatter;
  // 【绑定契约 · 勿删】属性面板回显必需：
  //   tableName = 数据集显示名（含括号后缀，如「党员发展(业务模块)」）
  //   fieldId/fieldName/fieldText = 字段标识三件套
  // 缺失会导致左侧数据源不显示模块类型、字段属性面板回显不全（历史回归事故）。
  const tableName = resolveTableName(f);
  const cfg = f.config || {};
  const fieldId = String(f.fieldId || cfg.fieldId || '');
  const fieldName = String(f.name || '');
  const fieldText = String(text || f.text || '');
  st.cellType = {
    typeName: 'FieldCellType',
    cellType: 'Field',
    name: f.name,
    nameIndex: f.nameIndex || '',
    text: text,
    dataSetId: f.dataSetId,
    tableName,
    fieldId,
    fieldName,
    fieldText,
    fieldKey: `${f.dataSetId}.${f.nameIndex}.${f.name}`,
    leftX: left[0],
    leftY: left[1],
    topX: -1,
    topY: -1,
    refX: -1,
    refY: -1,
    expandType: 'Vertical',
    displayType: 'Group',
    countType: 'count',
    groupType: groupType || null,
    orderType: 'no',
    formatterType: [fmt.key],
    subordination: ['', ''],
    leftFilterField: [],
    topFilterField: [],
    customFilterField: [],
    dataFilterField: [],
    transType: 'default',
    browserType: [],
    transSelectOptions: [],
    // 日期字段属性面板回显（旧包 field_bind 契约，勿删）
    dateTimeProp: {
      dateTimeFormart: '',
      dateTimeRangeType: '0',
      dateTimeRange0: [],
      dateTimeRange1: ['{startTime}', '{endTime}'],
      dateTimeRange2: ['', ''],
      dateTimeView: 'Day',
    },
    isHtml: '0',
    qrcodeType: 'no',
    qrcodelink: '0',
    prefixAndSuffix: ['', ''],
    hiddenContext: '0',
    textDirection: 'FromLeftToRight',
    pcHreflink: '',
    h5Hreflink: '',
    openType: 'blank',
    isActiveParent: !!isRoot,
    arrowType: 'None',
    allowOverflow: true,
    thumbnail: 'NoDisplay',
    editorType: 1,
    conditionRule: conditionRule || {},
  };
  return { style: st, tag: { formatterType: [fmt.key] } };
}

function formulaCell(expr, style, left) {
  const bare = String(expr).replace(/^=+/, ''); // 禁止前导 =
  const st = makeStyle(style);
  st.formatter = ''; // 与手动保存对齐
  st.cellType = {
    typeName: 'FormulaCellType',
    cellType: 'Formula',
    cellText: bare,
    editorType: 1,
    leftX: left[0],
    leftY: left[1],
    topX: -1,
    topY: -1,
    refX: -1,
    refY: -1,
    expandType: 'NoExpand',
    displayType: 'Group',
    countType: 'count',
    groupType: null,
    orderType: 'no',
    formatterType: [],
    subordination: ['', ''],
    isActiveParent: false,
    arrowType: 'None',
    textDirection: 'FromLeftToRight',
    allowOverflow: true,
    hiddenContext: '0',
    transSelectOptions: [],
    browserType: [],
    thumbnail: 'NoDisplay',
    conditionRule: {},
  };
  return { style: st, formula: bare, tag: { formatterType: ['common'] } };
}

const RELATION = {
  '>': 'highlight:greater',
  '>=': 'highlight:greaterAndEquals',
  '<': 'highlight:less',
  '<=': 'highlight:lessAndEquals',
  '=': 'highlight:equals',
  '!=': 'highlight:noEquals',
  between: 'highlight:interval',
  包含: 'highlight:include',
};

function buildConditionRule(rule) {
  if (!rule) return {};
  const out = {};
  if (rule.highlight) {
    const h = rule.highlight;
    const rel = RELATION[h.op] || h.op;
    out.highlightDatas = [
      {
        index: 0,
        conditionType: 'currCell',
        relation: rel,
        value1: String(h.value1 != null ? h.value1 : ''),
        value2: String(h.value2 != null ? h.value2 : ''),
        foreColor: h.foreColor || '#FF0000',
        fontSize: String(normalizeFontPt(h.fontSize || 12)),
        fontFamily: h.fontFamily || '微软雅黑',
        bold: !!h.bold,
        italic: !!h.italic,
        underline: !!h.underline,
      },
    ];
  }
  if (rule.databar) {
    const d = rule.databar;
    out.lineDatas = [
      {
        index: 0,
        leftType: d.leftType || 'min',
        leftValue: String(d.leftValue || ''),
        rightType: d.rightType || 'max',
        rightValue: String(d.rightValue || ''),
        gradient: d.solid ? 'solid' : 'gradient',
        color: d.color || '#6495ED',
        negativeFillColor: d.negativeFillColor || '#FF0000',
      },
    ];
  }
  if (rule.iconset) {
    const i = rule.iconset;
    const t = i.thresholds || [67, 33];
    out.iconDatas = [
      {
        index: 0,
        iconSetType: String(i.type != null ? i.type : 0),
        iconCriteria: t.map((v) => ({
          iconValue: String(v),
          isGreaterThanOrEqualTo: true,
          iconValueType: 1,
        })),
      },
    ];
  }
  return out;
}

function colLetter(i) {
  let s = '';
  let n = i;
  do {
    s = String.fromCharCode(65 + (n % 26)) + s;
    n = Math.floor(n / 26) - 1;
  } while (n >= 0);
  return s;
}

function buildWorkbook(spec, datasetId, sourceId, fieldsKey, dsMeta, plan) {
  const cols = spec.columns;
  const meta = dsMeta || {};
  const datasetLabel = meta.label || spec.sourceName || '';
  const sourceType = meta.sourceType || spec.sourceType || 'logic';
  const layers = resolveLayerStyles(spec);
  const titleStyle = layers.title;
  const headerStyle = layers.header;
  const bodyStyle = layers.body;
  const layout = spec.layout || {};
  const withTitle = !!layout.title;
  const titleX = 0;
  const headX = withTitle ? 1 : 0;
  const dataX = headX + 1;
  const nCol = cols.length;
  const widths = cols.map((c) => c.width || 120);
  // 严格绑定结果（index → fieldsKey 字段）；无 plan 时单列兜底解析
  const bindingAt = (i) => {
    if (plan && plan.bindings) {
      const b = plan.bindings.find((x) => x.index === i);
      if (b) return b.field;
    }
    return matchField(fieldsKey, cols[i].field);
  };

  const dt = {};
  const spans = [];

  if (withTitle) {
    dt[String(titleX)] = {
      '0': constCell(layout.title, titleStyle, {
        left: [-1, -1],
        rowCount: 1,
        colCount: nCol,
      }),
    };
    spans.push({ row: titleX, col: 0, rowCount: 1, colCount: nCol });
  }

  // 表头行：首格 -1,-1，其余链式跟随左邻；冻结时首格打 fixed 锚点
  const head = {};
  const freezeRows = Number(layout.freezeRows || 0);
  cols.forEach((c, i) => {
    const left = i === 0 ? [-1, -1] : [headX, i - 1];
    head[String(i)] = constCell(c.title, headerStyle, {
      left,
      fixed: freezeRows > 0 && i === 0,
    });
  });
  dt[String(headX)] = head;

  // 数据行
  const data = {};
  cols.forEach((c, i) => {
    const left = i === 0 ? [-1, -1] : [dataX, i - 1];
    if (c.formula) {
      data[String(i)] = formulaCell(c.formula, bodyStyle, [dataX, 0]);
    } else {
      const fk = bindingAt(i);
      data[String(i)] = fieldCell(
        {
          name: fk.name,
          nameIndex: sourceId,
          dataSetId: datasetId,
          // 数据集显示名 + 字段三件套来源（缺失即历史回归事故）
          tableName: fk.tableName || fk.datasetName || datasetLabel,
          datasetLabel,
          sourceType,
          fieldId: (fk.config && fk.config.fieldId) || fk.fieldId || '',
          fieldText: fk.text || fk.showName || c.field,
        },
        bodyStyle,
        {
          text: c.title,
          left,
          isRoot: i === 0,
          fmtKey: ALIAS[c.format] || c.format || 'common',
          groupType: c.groupType || null,
          conditionRule: buildConditionRule(c.rule),
        }
      );
    }
  });
  dt[String(dataX)] = data;

  const sheet = {
    name: 'Sheet1',
    rowCount: 200,
    columnCount: 30,
    activeRow: dataX,
    activeCol: 0,
    frozenRowCount: freezeRows,
    frozenColCount: 0,
    rows: (withTitle ? [{ size: 34 }, { size: 26 }, { size: 24 }] : [{ size: 26 }, { size: 24 }]).slice(
      0,
      dataX + 1
    ),
    columns: widths.map((w) => ({ size: w })),
    spans,
    tag: {
      showLocation: layout.showLocation === 'left' ? 1 : 2,
      fixedCell: freezeRows > 0 ? { x: headX, y: 0 } : undefined,
    },
    data: { dataTable: dt },
  };
  if (!sheet.tag.fixedCell) delete sheet.tag.fixedCell;
  // 硬约束：sheet 禁写 gridline 族键（存在 → saveReportDevInfo 500）
  return {
    version: '11.1.0',
    sheetCount: 1,
    newTabVisible: false,
    tabEditable: false,
    sheets: { Sheet1: sheet },
    __meta: { styleSource: layers.source },
  };
}

function gzipB64(obj) {
  return zlib.gzipSync(Buffer.from(JSON.stringify(obj), 'utf8'), { level: 9 }).toString('base64');
}

function parseArgs(argv) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const k = a.slice(2);
      const v = argv[i + 1] && !argv[i + 1].startsWith('--') ? argv[++i] : true;
      out[k] = v;
    } else out._.push(a);
  }
  return out;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const specPath = args.spec;
  if (!specPath) {
    throw new Error(
      'Usage: edc-report build spec --spec <spec.json> [--dry-run] [--form-confirmed] [--source-id <id>] ' +
        '[--field-confirmed "标题1,标题2" | --field-confirmed]'
    );
  }
  const spec = JSON.parse(fs.readFileSync(path.resolve(specPath), 'utf8'));
  const appId = String(spec.appId || '');
  const finalName = spec.reportName || spec.name;
  // form/sourceId **不作为**前置必填：未指明表时交由「规则 B」出候选让用户指定（禁止按关键词猜表）
  if (!appId || !finalName || !Array.isArray(spec.columns)) {
    throw new Error('spec 需含 appId / name(报表名) / columns[]；form|sourceId 可省（省则走规则 B 让用户选表）');
  }

  const T = Date.now();
  const mark = (n, extra) =>
    console.log(`  ${String(Date.now() - T).padStart(5)}ms  ${n}${extra ? ' — ' + extra : ''}`);

  // 0 定源（仅当前应用；**规则 B**：未指明表 / 非完全精准匹配 → 提示用户指定，不建表）
  const formGate = await resolveFormWithPrompt(appId, String(spec.form || ''), {
    sourceId: args['source-id'] || spec.sourceId,
    confirmedSourceId: args['source-id'] || spec.sourceId,
    formConfirmed: !!(args['form-confirmed'] || spec.formConfirmed),
    keywords: spec.formKeywords || spec.keywords,
    suggestOnly: !spec.form && !spec.sourceId && !args['source-id'],
  });
  mark('resolveForm', `${formGate.reason} needConfirm=${formGate.needConfirm}`);

  if (formGate.needConfirm) {
    const formHit = {
      candidates: formGate.candidates,
      match: formGate.reason,
      message: formGate.message,
    };
    console.log(
      JSON.stringify(
        {
          ok: false,
          action: formGate.candidates.length ? 'confirm_form' : 'need_exact_form_name',
          rule: 'B',
          needConfirm: true,
          autoBind: false,
          appId,
          formQuery: spec.form || null,
          reason: formGate.reason,
          match: formGate.reason,
          message:
            formHit.message ||
            '当前应用内未精准命中表单。请提供准确表名或 sourceId；若下列候选正确，确认后加 --form-confirmed 或 spec.formConfirmed/sourceId 再搭。',
          confirmPrompt: formGate.candidates.length
            ? '请用户从 candidates 中**指定一张表**（填写 form/sourceId）后再搭建。'
            : '请用户提供准确表名或 sourceId（可先 edc-report find form <appId> --list 浏览）。',
          candidates: formGate.candidates || [],
          next: {
            cli: 'edc-report build spec --spec <spec.json> --form-confirmed --source-id <id>',
            specFields: { formConfirmed: true, sourceId: '<id>', form: '<准确表名>' },
          },
          reportCreated: false,
          totalMs: Date.now() - T,
        },
        null,
        2
      )
    );
    process.exit(3);
  }

  const sourceId = String(formGate.form.id);

  const fcArg = args['field-confirmed'];
  const fcList =
    typeof fcArg === 'string' && fcArg !== '*'
      ? fcArg
          .split(/[,，]/)
          .map((s) => s.trim())
          .filter(Boolean)
      : [];
  const fieldOpts = {
    fieldMap: spec.fieldMap || {},
    // --field-confirmed（无值）/ '*': 全部确认；spec.confirmDisplayMismatch 同理
    confirmDisplayMismatch: fcArg === true || fcArg === '*' || !!spec.confirmDisplayMismatch,
    fieldConfirmed: [
      ...(Array.isArray(spec.fieldConfirmed) ? spec.fieldConfirmed : []),
      ...fcList,
    ],
  };

  // 0.5 **建表前字段预检**（fieldsBySource，与 fieldsKey 同形）
  //     未精确命中 → 直接提示用户指定字段，**不建表**（禁止「先建壳再回滚」）
  let prePlan = null;
  try {
    const preFields = await fieldsBySource(sourceId, appId, { sourceType: spec.sourceType });
    if (preFields.length) {
      prePlan = resolveFieldBindings(preFields, spec.columns, fieldOpts);
      mark('preflight fields', `${preFields.length} 字段 · 未命中 ${prePlan.unmatched.length}`);
    }
  } catch (e) {
    console.warn('WARN 预检 fieldsBySource 失败，改由落库前 fieldsKey 门禁兜底：' + e.message);
  }
  if (prePlan && !prePlan.ok) {
    const allFields = prePlan.unmatched[0] && prePlan.unmatched[0].allFields ? prePlan.unmatched[0].allFields : [];
    console.log(
      JSON.stringify(
        {
          ok: false,
          action: 'confirm_field',
          rule: 'A',
          needConfirm: true,
          autoBind: false,
          appId,
          sourceId,
          formName: formGate.form.name,
          reportCreated: false,
          unmatched: prePlan.unmatched.map((u) => ({
            column: u.title,
            reason: u.reason,
            resolved: u.resolvedName ? { name: u.resolvedName, text: u.resolvedText } : undefined,
            message: u.message,
            prompt:
              u.reason === 'display_mismatch'
                ? `列「${u.title}」将绑到「${u.resolvedText}」(${u.resolvedName})，若确认文案有意如此，加 --field-confirmed "${u.title}"。`
                : `需求字段「${u.title}」在**当前数据集表单中不存在**：请用户从 allFields/candidates 中**指定字段**（禁止自动兜底系统字段）。`,
            candidates: u.candidates,
          })),
          // 全量可选字段（供用户挑选；含系统字段，但禁止自动兜底）
          allFields: allFields.map((f) => ({ name: f.name, text: f.text, system: !!f.system })),
          message:
            '列字段未在该数据源精确命中（或与真实显示名不一致）。**未创建任何报表**。' +
            '请用户指定字段后，用 spec.fieldMap（{列标题: 字段显示名或 field_xxx}）或 spec.fieldConfirmed 复跑。',
          next: {
            cli: 'edc-report build spec --spec <spec.json> --field-confirmed "标题1,标题2"',
            specFields: {
              fieldMap: { '<列标题>': '<字段显示名 | field_雪花 | 系统字段名>' },
              fieldConfirmed: ['<与字段真实显示名不同但已确认的列标题>'],
            },
          },
          totalMs: Date.now() - T,
        },
        null,
        2
      )
    );
    process.exit(4);
  }

  if (args['dry-run']) {
    console.log(
      JSON.stringify(
        {
          ok: true,
          dryRun: true,
          sourceId,
          formName: formGate.form.name,
          match: formGate.reason,
          bindings: prePlan
            ? prePlan.bindings.map((b) => ({
                column: b.title,
                field: b.field.name,
                displayText: b.displayText,
                how: b.how,
                mismatchConfirmed: b.mismatchConfirmed,
              }))
            : null,
        },
        null,
        2
      )
    );
    return;
  }

  // 1 直接用目标报表名创建（禁止 __build_* 空壳 / 禁止先建再改名）
  const shell = await post('/api/bs/edc/report/baseInfo', {
    appId,
    form: [
      ['id', '0'],
      ['name', finalName],
      ['nameLabelId', '-1'],
      ['groupId', '0'],
      ['showOrder', '1'],
      ['appId', appId],
    ],
  });
  const reportId = String((shell.json && shell.json.data) || '');
  if (!reportId || reportId === 'undefined') {
    throw new Error('baseInfo 创建失败：' + shell.raw.slice(0, 200));
  }
  mark('baseInfo', `${reportId} name=${finalName}`);

  try {
    // 2 本报表 addDataset（同源只挂一次；禁止重复挂载 / 跨报表复用）
    const ds = await resolveDataset({
      reportId,
      appId,
      sourceId,
      datasetId: spec.datasetId,
      sourceType: spec.sourceType,
      sourceGroup: spec.sourceGroup,
      // 回显名强制 `{表单名}(业务模块)`（裸表单名会导致面板缺后缀）
      sourceName: spec.sourceName || formGate.form.name,
    });
    mark(
      'dataset',
      `${ds.id}${ds.reused ? ' (本表复用)' : ' (本表新建)'} name=${ds.name}${
        ds.duplicates && ds.duplicates.length ? ' DUP=' + ds.duplicates.join(',') : ''
      }`
    );

    // 3 同表取 fieldsKey（传入 dsMeta 使字段自带数据集显示名）
    const dsMeta = {
      label: ds.name || spec.sourceName || formGate.form.name,
      sourceType: ds.sourceType || spec.sourceType || 'logic',
    };
    const fieldsKey = await fieldsKeyOf(ds.id, reportId, appId, dsMeta);
    mark('fieldsKey', `${fieldsKey.length} 字段`);
    const legal = new Set(fieldsKey.map((f) => String(f.name)));

    // 3.5 权威门禁：按**落库 fieldsKey** 再解析一次；不通过 → 删除本表并请用户指定字段
    const plan = resolveFieldBindings(fieldsKey, spec.columns, fieldOpts);
    if (!plan.ok) {
      try {
        await deleteReport(reportId, appId);
        console.error('字段未精确命中，已删除未完成报表 ' + reportId);
      } catch (_) {
        /* ignore */
      }
      console.log(
        JSON.stringify(
          {
            ok: false,
            action: 'confirm_field',
            needConfirm: true,
            reportId,
            reportDeleted: true,
            datasetId: ds.id,
            appId,
            sourceId,
            unmatched: plan.unmatched.map((u) => ({
              column: u.title,
              reason: u.reason,
              resolved: u.resolvedName ? { name: u.resolvedName, text: u.resolvedText } : undefined,
              message: u.message,
              prompt:
                u.reason === 'display_mismatch'
                  ? `列「${u.title}」将绑到「${u.resolvedText}」(${u.resolvedName})，确认文案有意如此则加 --field-confirmed "${u.title}"。`
                  : `需求字段「${u.title}」在当前数据集表单中不存在：请用户从 candidates/allFields 中指定字段。`,
              candidates: u.candidates,
            })),
            allFields: (plan.unmatched[0] && plan.unmatched[0].allFields
              ? plan.unmatched[0].allFields
              : []
            ).map((f) => ({ name: f.name, text: f.text, system: !!f.system })),
            message:
              '列字段未在 fieldsKey 精确命中。已删除本轮未交付报表。请用户指定字段后，' +
              '用 spec.fieldMap（{列标题: 字段显示名或 field_xxx}）或 --field-confirmed 复跑。',
            next: {
              cli: 'edc-report build spec --spec <spec.json> --field-confirmed "标题1"',
              specFields: { fieldMap: { '<列标题>': '<字段显示名>' } },
            },
            totalMs: Date.now() - T,
          },
          null,
          2
        )
      );
      process.exit(4);
    }
    mark('resolveFieldBindings', `${plan.bindings.length}/${spec.columns.length} 列已精确绑定`);

    // 4 组 workbook + 落库（同 reportId 一次完成）
    // tableName 后缀由注册类型决定：(业务模块) / (表单)
    const wb = buildWorkbook(spec, ds.id, sourceId, fieldsKey, dsMeta, plan);
    const styleSource = (wb.__meta && wb.__meta.styleSource) || 'unknown';
    delete wb.__meta;
    const cells = Object.values(wb.sheets.Sheet1.data.dataTable).reduce(
      (n, row) => n + Object.keys(row).length,
      0
    );
    mark('buildWorkbook', `${cells} 单元格 · style=${styleSource}`);

    const b64 = gzipB64(wb);
    const saved = await post('/api/bs/edc/report/saveReportDevInfo', {
      appId,
      referer: reportId,
      form: [
        ['groupId', '0'],
        ['appId', appId],
        ['reportId', reportId],
        ['name', finalName],
        ['nameLabelId', '-1'],
        ['designKey', ''],
        ['workbook', b64],
      ],
    });
    if (!saved.json || saved.json.code !== 200) {
      throw new Error('saveReportDevInfo 失败：' + saved.raw.slice(0, 300));
    }
    mark('saveReportDevInfo', '200');

    // 5 回读（无 rename）
    const dev = await get('/api/bs/edc/report/getReportDevInfo', {
      appId,
      referer: reportId,
      query: { reportId },
    });
    const fields = (dev.json && dev.json.data && dev.json.data.fields) || [];
    const types = fields.reduce((m, f) => ((m[f.cellType] = (m[f.cellType] || 0) + 1), m), {});
    const badBind = fields
      .filter((f) => f.cellType === 'Field')
      .filter((f) => !legal.has(String(f.name)));
    // 【落库门禁 · 历史回归】tableName 缺失 → 数据源不显示模块类型后缀；(业务模块)/(表单)
    const fieldCells = fields.filter((f) => f.cellType === 'Field');
    const missingTableName = fieldCells.filter((f) => !f.tableName);
    // 【显示名一致性门禁 · 2026-09-11】单元格文案 ≠ 绑定字段真实显示名 → 必须提示用户确认
    //   事故：B3 文案「姓名」实绑系统字段 name（真实显示名「标题」），列语义被静默改写
    const displayMismatch = fieldCells
      .filter((f) => {
        const real = textByFieldName(fieldsKey, f.name);
        return real && normText(real) !== normText(f.text);
      })
      .map((f) => ({
        cell: `${colLetter(Number(f.y))}${Number(f.x) + 1}`,
        cellText: f.text,
        field: String(f.name || ''),
        realDisplayName: textByFieldName(fieldsKey, f.name),
        systemField: isSystemField({ name: f.name }),
      }));
    mark('getReportDevInfo', `${fields.length} 字段 ${JSON.stringify(types)}`);
    if (missingTableName.length) {
      console.error(
        `WARN ${missingTableName.length}/${fieldCells.length} 个 Field 单元格缺 tableName` +
          `（数据源将不显示模块类型后缀）。样例：${missingTableName
            .slice(0, 3)
            .map((f) => `(${f.x},${f.y})`)
            .join(' ')}`
      );
      process.exitCode = 2;
    }
    if (displayMismatch.length) {
      console.error(
        'WARN 显示名与绑定字段不一致（需用户确认）：' +
          displayMismatch.map((m) => `${m.cell}「${m.cellText}」→「${m.realDisplayName}」`).join('；')
      );
      process.exitCode = 2;
    }
    const datasetDuplicates = ds.duplicates || [];
    if (datasetDuplicates.length) {
      console.error(
        `WARN 同 sourceId 存在重复数据集挂载：${[ds.id, ...datasetDuplicates].join(',')}` +
          '（会导致左侧出现重复数据源分组；清理见 dataset-sidebar-ops-guide.md §5.3）'
      );
      process.exitCode = 2;
    }

    console.log(
      JSON.stringify(
        {
          ok: true,
          reportId,
          datasetId: ds.id,
          datasetName: ds.name,
          datasetNameExpected: ds.requestedName || null,
          datasetReused: ds.reused,
          datasetScope: ds.scope || 'same-report',
          datasetDuplicates,
          name: finalName,
          formName: formGate.form.name,
          formMatch: formGate.reason,
          sourceId,
          appId,
          fields: fields.length,
          cellTypes: types,
          fieldBindings: plan.bindings.map((b) => ({
            column: b.title,
            field: b.field.name,
            displayText: b.displayText,
            how: b.how,
            mismatchConfirmed: b.mismatchConfirmed,
          })),
          tableName: fieldCells.length ? fieldCells[0].tableName : null,
          tableNameMissing: missingTableName.length,
          bindErrors: badBind.map((f) => f.name),
          displayMismatch,
          noTempShell: true,
          totalMs: Date.now() - T,
          designerUrl: `https://${host()}/sp/edc/report/designer/${reportId}`,
        },
        null,
        2
      )
    );
    if (badBind.length) {
      console.error('WARN 字段绑定不在 fieldsKey：' + badBind.map((f) => f.name).join(','));
      process.exitCode = 2;
    }
  } catch (e) {
    // 仅失败时删除本表未交付成品（非「先建空壳再删」流程）
    try {
      await deleteReport(reportId, appId);
      console.error('搭建失败，已删除未完成报表 ' + reportId);
    } catch (_) {
      /* ignore */
    }
    throw e;
  }
}

main().catch((e) => {
  console.error('FAIL: ' + (e && e.message ? e.message : e));
  process.exit(1);
});
