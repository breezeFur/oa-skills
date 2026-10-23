'use strict';
/**
 * 事件超链接 / 打开方式 / 传参校验 — references/event-hreflink-guide.md
 *
 *   node validate_event_href.js --map "弹出页"
 *   node validate_event_href.js --file cell.json
 *   node validate_event_href.js --inline '{"pcHreflink":"...","openType":"blank"}'
 *   node validate_event_href.js --list
 *
 * 强制：ASCII ?/&；查询串单元格用 参数名=坐标（无花括号）；路径用 {坐标}；禁全角 ？
 */
const fs = require('fs');

const OPEN_TYPE_MAP = {
  弹出页: 'blank',
  弹窗: 'blank',
  弹层: 'blank',
  新页签: 'blank',
  blank: 'blank',
  当前页: 'self',
  self: 'self',
  执行js代码: 'jsscript',
  执行JS代码: 'jsscript',
  jsscript: 'jsscript',
  js: 'jsscript',
};

const FORBIDDEN_OPEN = new Set(['popup', 'window', 'new', 'modal', 'redirect']);
const FORBIDDEN_PARAM_NAMES = new Set(['id', 'name']);

function parseArgs(argv) {
  const out = { _: [] };
  const flags = new Set(['list', 'fix']);
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const key = a.slice(2);
      if (flags.has(key) || i + 1 >= argv.length || String(argv[i + 1]).startsWith('--')) {
        out[key] = true;
      } else {
        out[key] = argv[++i];
      }
    } else out._.push(a);
  }
  return out;
}

/** 全角标点 → ASCII；去掉异常空白 */
function sanitizeHrefString(s) {
  return String(s || '')
    .replace(/\uFF1F/g, '?') // ？
    .replace(/\uFF06/g, '&') // ＆
    .replace(/\u3000/g, ' ')
    .trim();
}

function normalizeHref(input, { fix = false } = {}) {
  const errors = [];
  const warnings = [];
  const normalized = {};

  const map = input.map != null ? String(input.map).trim() : '';
  let openType = input.openType;

  if (map && OPEN_TYPE_MAP[map]) {
    openType = OPEN_TYPE_MAP[map];
  } else if (map && !input.pcHreflink && !input.openType) {
    errors.push(`无法映射打开方式「${map}」。支持：弹出页/当前页/执行js代码（blank/self/jsscript）`);
  }

  if (openType != null && openType !== '') {
    const raw = String(openType);
    if (FORBIDDEN_OPEN.has(raw)) {
      errors.push(`禁止 openType=${raw}；请用 blank|self|jsscript`);
    } else if (OPEN_TYPE_MAP[raw]) {
      normalized.openType = OPEN_TYPE_MAP[raw];
    } else if (['blank', 'self', 'jsscript'].includes(raw)) {
      normalized.openType = raw;
    } else {
      errors.push(`非法 openType=${raw}`);
    }
  } else if (input.pcHreflink || input.h5Hreflink) {
    normalized.openType = 'blank';
    warnings.push('未指定 openType，默认 blank（弹出页）');
  }

  function checkLink(raw, key) {
    if (raw == null) return;
    let s = String(raw);
    if (/[？\uFF1F\uFF06]/.test(s)) {
      const msg =
        '链接含全角？/＆（事故：点击无反应）。必须用 ASCII ? 与 &。见 event-hreflink-guide.md';
      if (fix) {
        s = sanitizeHrefString(s);
        warnings.push(msg + '（已自动替换为 ASCII）');
      } else {
        errors.push(msg);
      }
    }
    if (fix) s = sanitizeHrefString(s);
    normalized[key] = s;

    // 查询串：参数名=坐标（无花括号），如 zclb=D7
    const queryCellParams = [...s.matchAll(/[?&]([^=&]+)=([A-Za-z]+\d+)\b/g)];
    for (const m of queryCellParams) {
      const pname = m[1];
      if (FORBIDDEN_PARAM_NAMES.has(pname.toLowerCase())) {
        warnings.push(
          `参数名「${pname}」易与系统关键字冲突，建议改用 zclb/zcmc 等非 id/name 名`
        );
      }
    }

    // 路径花括号 {C4}
    if (/\/\{[A-Za-z]+\d+\}/.test(s) || /\{[A-Za-z]+\d+\}/.test(s)) {
      const lx = input.leftX;
      const ly = input.leftY;
      if (input.cellType === 'Const' || input.typeName === 'ConstCellType') {
        if (lx == null || ly == null || (Number(lx) === -1 && Number(ly) === -1)) {
          errors.push(
            '路径含 {坐标} 时，Const 左父格须指向数据格（禁止默认 -1,-1）；见 event-hreflink-guide.md §三'
          );
        }
        if (Number(lx) === 0 && Number(ly) === 0) {
          errors.push('禁止伪自定义父格 (0,0)');
        }
      }
    }

    // 旧式 $ds.field$：允许但提示手册主推坐标
    if (/\$[^$]+\.[^$]+\$/.test(s)) {
      warnings.push(
        '含 $datasetId.field$：引擎可用，但帮助手册主推查询串「参数名=坐标」或路径「/{坐标}」'
      );
    }

    if (/\{searchfield\d+/i.test(s)) {
      warnings.push('含查询条件占位 {searchfield00x}：确认 asNameIndex 与条件配置一致');
    }

    // 花括号包着坐标出现在查询串值位置（错误用法）
    if (/[?&][^=]+=\{[A-Za-z]+\d+\}/.test(s)) {
      errors.push(
        '查询串单元格传参勿写 param={D7}；手册要求 param=D7（无花括号）。路径占位才用 {D7}'
      );
    }
  }

  const pc = input.pcHreflink != null ? input.pcHreflink : input.hreflink;
  const h5 = input.h5Hreflink != null ? input.h5Hreflink : input.mbhreflink;
  checkLink(pc, 'pcHreflink');
  if (h5 != null) checkLink(h5, 'h5Hreflink');

  if (input.cellText != null) normalized.cellText = String(input.cellText);
  if (input.cellType != null) normalized.cellType = input.cellType;

  return { ok: errors.length === 0, errors, warnings, normalized };
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.list || args._[0] === 'list') {
    console.log(
      JSON.stringify(
        {
          openType: OPEN_TYPE_MAP,
          rules: {
            queryCell: '参数名=坐标（无花括号），如 zclb=D7&zcmc=E7',
            pathCell: '/sp/.../card/0/{id}/{C4}',
            queryCondition: '{searchfield001}',
            asciiOnly: '禁止全角？＆；必须 ASCII ? &',
            avoidParamNames: ['id', 'name'],
            parentChain: '仅当前格+左/上父格（父格的父格也可）',
          },
          guide: 'references/event-hreflink-guide.md',
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
    console.error(
      'Usage: validate_event_href.js --map "弹出页"|--file cell.json|--inline "{...}"|--list [--fix]'
    );
    process.exit(2);
  }

  const result = normalizeHref(input, { fix: !!args.fix });
  console.log(JSON.stringify(result, null, 2));
  process.exit(result.ok ? 0 : 1);
}

module.exports = {
  normalizeHref,
  sanitizeHrefString,
  OPEN_TYPE_MAP,
};

if (require.main === module) main();
