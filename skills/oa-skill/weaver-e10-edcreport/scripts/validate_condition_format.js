#!/usr/bin/env node
/**
 * 条件格式（突出显示）校验 — 见 references/condition-format-guide.md
 *
 * Usage:
 *   node validate_condition_format.js --file rule.json
 *   node validate_condition_format.js --inline '{"highlightDatas":[...]}'
 *   node validate_condition_format.js --report-id <id> [appId]
 *   node validate_condition_format.js --map "介于 1 5"   # 自然语言试映射（不落库）
 *
 * Exit 0 = PASS（可有 warnings）；有 errors → exit 1
 */
'use strict';

const fs = require('fs');

const https = require('https');
const { resolveE10Host } = require('./resolve_e10_host');

/** 引擎 ReportUtil 识别的 type（strip highlight: 后） */
const ALLOWED = new Set([
  'greater',
  'greaterAndEquals',
  'less',
  'lessAndEquals',
  'equals',
  'noEquals',
  'interval',
  'include',
  'happenDate',
  'sameValue',
]);

/** 常见错误别名 → 建议 */
const ALIAS_FIX = {
  between: 'interval',
  gt: 'greater',
  gte: 'greaterAndEquals',
  lt: 'less',
  lte: 'lessAndEquals',
  eq: 'equals',
  ne: 'noEquals',
  neq: 'noEquals',
};

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

function normalizeRelation(rel) {
  const raw = String(rel || '').trim();
  const stripped = raw.replace(/^highlight:/i, '');
  return { raw, stripped, full: stripped ? `highlight:${stripped}` : '' };
}

/**
 * @param {object} conditionRule - { highlightDatas?, lineDatas?, iconDatas? } 或 highlightDatas 数组
 * @param {{ cellLabel?: string }} opts
 */
function validateConditionRule(conditionRule, opts = {}) {
  const errors = [];
  const warnings = [];
  const suggestions = [];
  const label = opts.cellLabel || 'cell';

  let rule = conditionRule;
  if (Array.isArray(conditionRule)) {
    rule = { highlightDatas: conditionRule };
  }
  rule = parseMaybe(rule, null);
  if (!rule || typeof rule !== 'object') {
    return {
      ok: true,
      errors: [],
      warnings: [`${label}: conditionRule 空/非对象，跳过`],
      suggestions: [],
      normalized: null,
    };
  }

  const highlights = parseMaybe(rule.highlightDatas, []);
  if (!Array.isArray(highlights)) {
    errors.push(`${label}: highlightDatas 必须是数组`);
    return { ok: false, errors, warnings, suggestions, normalized: null };
  }

  const normalizedHighlights = [];
  const numericBands = []; // for conflict: { index, lo, hi, exclusive, styleKey }

  for (let i = 0; i < highlights.length; i++) {
    const h = highlights[i] || {};
    const { raw, stripped, full } = normalizeRelation(h.relation);
    if (!stripped) {
      errors.push(`${label}[#${i}]: 缺 relation`);
      continue;
    }

    if (!ALLOWED.has(stripped)) {
      const fix = ALIAS_FIX[stripped];
      if (fix) {
        errors.push(
          `${label}[#${i}]: relation "${raw}" 引擎不识别（会静默不生成规则）。请改为 highlight:${fix}`
        );
        suggestions.push({
          index: i,
          from: full || raw,
          to: `highlight:${fix}`,
          reason: '别名修正',
        });
      } else {
        errors.push(
          `${label}[#${i}]: relation "${raw}" 不在白名单。支持: ${[...ALLOWED].map((x) => 'highlight:' + x).join(', ')}。若为复合逻辑，请拆成多条互不重叠规则或改用「介于」，并请用户确认。`
        );
        suggestions.push({
          index: i,
          from: raw,
          to: null,
          reason: '不支持 — 需用户确认是否拆规则或放弃',
        });
      }
      continue;
    }

    if (stripped === 'interval') {
      if (h.value1 == null || h.value1 === '' || h.value2 == null || h.value2 === '') {
        errors.push(`${label}[#${i}]: interval（介于）必须同时有 value1（下界）与 value2（上界）`);
      }
      const lo = Number(h.value1);
      const hi = Number(h.value2);
      if (!Number.isNaN(lo) && !Number.isNaN(hi)) {
        if (lo > hi) warnings.push(`${label}[#${i}]: interval 下界 ${lo} > 上界 ${hi}`);
        numericBands.push({
          index: i,
          kind: 'interval',
          lo,
          hi,
          styleKey: `${h.foreColor || ''}|${h.backColor || ''}|${!!h.bold}`,
        });
      }
    } else if (['greater', 'greaterAndEquals', 'less', 'lessAndEquals', 'equals', 'noEquals'].includes(stripped)) {
      if (h.value1 == null || h.value1 === '') {
        errors.push(`${label}[#${i}]: ${stripped} 需要 value1`);
      }
      const v = Number(h.value1);
      if (!Number.isNaN(v)) {
        numericBands.push({
          index: i,
          kind: stripped,
          value: v,
          styleKey: `${h.foreColor || ''}|${h.backColor || ''}|${!!h.bold}`,
        });
      }
    }

    normalizedHighlights.push({
      ...h,
      index: h.index != null ? h.index : i,
      relation: full,
      conditionType: h.conditionType || 'currCell',
    });
  }

  // 冲突：两条 greater 且阈值不同、样式不同 → 高值区间重叠
  const greaters = numericBands.filter((b) => b.kind === 'greater' || b.kind === 'greaterAndEquals');
  if (greaters.length >= 2) {
    const styles = new Set(greaters.map((g) => g.styleKey));
    if (styles.size > 1) {
      warnings.push(
        `${label}: 多条「大于/大于等于」且样式不同，高值区间会重叠命中（冲突）。建议低档改用 interval 与高档错开，并请用户确认边界。示例: interval(1,5)红 + greater(5)蓝`
      );
      suggestions.push({
        reason: '冲突 — 请用户确认是否改为 interval + greater',
        bands: greaters,
      });
    }
  }

  // greater + less 成对但样式相同：可能是用户想 AND 区间
  const lesses = numericBands.filter((b) => b.kind === 'less' || b.kind === 'lessAndEquals');
  if (greaters.length === 1 && lesses.length === 1) {
    const g = greaters[0];
    const l = lesses[0];
    if (g.styleKey === l.styleKey) {
      warnings.push(
        `${label}: 检测到 greater(#${g.index}) + less(#${l.index}) 同样式。多规则是 OR 不是 AND，无法实现「大于且小于」。请改为一条 highlight:interval，并请用户确认。`
      );
      suggestions.push({
        reason: 'OR≠AND — 建议合并为 interval',
        to: {
          relation: 'highlight:interval',
          value1: String(g.value),
          value2: String(l.value),
        },
      });
    }
  }

  // —— 数据条 lineDatas ——
  const lineDatas = parseMaybe(rule.lineDatas, []);
  const normalizedLines = [];
  if (rule.lineDatas != null && !Array.isArray(lineDatas)) {
    errors.push(`${label}: lineDatas 必须是数组`);
  } else if (Array.isArray(lineDatas)) {
    for (let i = 0; i < lineDatas.length; i++) {
      const d = lineDatas[i] || {};
      const leftType = d.leftType || 'min';
      const rightType = d.rightType || 'max';
      const gradient = d.gradient || 'gradient';
      if (!['min', 'max', 'custom'].includes(String(leftType))) {
        errors.push(`${label}.lineDatas[#${i}]: leftType 非法（min|max|custom）`);
      }
      if (!['min', 'max', 'custom'].includes(String(rightType))) {
        errors.push(`${label}.lineDatas[#${i}]: rightType 非法（min|max|custom）`);
      }
      if (!['gradient', 'solid'].includes(String(gradient))) {
        errors.push(`${label}.lineDatas[#${i}]: gradient 须为 gradient|solid`);
      }
      if (leftType === 'custom' && (d.leftValue == null || d.leftValue === '')) {
        errors.push(`${label}.lineDatas[#${i}]: leftType=custom 需要 leftValue`);
      }
      if (rightType === 'custom' && (d.rightValue == null || d.rightValue === '')) {
        errors.push(`${label}.lineDatas[#${i}]: rightType=custom 需要 rightValue`);
      }
      if (!d.color) {
        warnings.push(`${label}.lineDatas[#${i}]: 建议设置 color`);
      }
      normalizedLines.push({
        index: d.index != null ? d.index : i,
        leftType,
        leftValue: d.leftValue != null ? d.leftValue : '',
        rightType,
        rightValue: d.rightValue != null ? d.rightValue : '',
        gradient,
        color: d.color || '#6495ED',
        negativeFillColor: d.negativeFillColor || '#FF0000',
      });
    }
  }

  // —— 图标集 iconDatas ——
  const iconDatas = parseMaybe(rule.iconDatas, []);
  const normalizedIcons = [];
  if (rule.iconDatas != null && !Array.isArray(iconDatas)) {
    errors.push(`${label}: iconDatas 必须是数组`);
  } else if (Array.isArray(iconDatas)) {
    for (let i = 0; i < iconDatas.length; i++) {
      const d = iconDatas[i] || {};
      if (d.iconSetType == null || d.iconSetType === '') {
        errors.push(`${label}.iconDatas[#${i}]: 缺 iconSetType（字符串，如 \"0\"）`);
      }
      const criteria = parseMaybe(d.iconCriteria, []);
      if (d.iconCriteria != null && !Array.isArray(criteria)) {
        errors.push(`${label}.iconDatas[#${i}]: iconCriteria 必须是数组`);
      }
      normalizedIcons.push({
        index: d.index != null ? d.index : i,
        iconSetType: String(d.iconSetType),
        iconCriteria: Array.isArray(criteria) ? criteria : [],
      });
    }
  }

  if (rule.iconSets != null) {
    warnings.push(
      `${label}: 检测到 iconSets 键名；落库请用 iconDatas（引擎字段名）`
    );
  }

  return {
    ok: errors.length === 0,
    errors,
    warnings,
    suggestions,
    normalized: {
      ...rule,
      highlightDatas: normalizedHighlights,
      ...(normalizedLines.length ? { lineDatas: normalizedLines } : {}),
      ...(normalizedIcons.length ? { iconDatas: normalizedIcons } : {}),
    },
  };
}

/** 简易自然语言试映射（不落库） */
function mapNaturalPhrase(phrase) {
  const s = String(phrase || '').trim();
  const suggestions = [];
  const errors = [];

  if (/实心\s*数据条|数据条.*实心/.test(s)) {
    suggestions.push({
      lineDatas: [
        {
          index: 0,
          leftType: 'min',
          rightType: 'max',
          gradient: 'solid',
          color: '#6495ED',
          negativeFillColor: '#FF0000',
        },
      ],
      note: '数据条 → conditionRule.lineDatas；禁止下载 SpreadJS 探结构',
    });
    return { ok: true, errors, suggestions, phrase: s };
  }
  if (/数据条|databar|data\s*bar/i.test(s)) {
    suggestions.push({
      lineDatas: [
        {
          index: 0,
          leftType: 'min',
          rightType: 'max',
          gradient: 'gradient',
          color: '#6495ED',
          negativeFillColor: '#FF0000',
        },
      ],
      note: '数据条 → conditionRule.lineDatas',
    });
    return { ok: true, errors, suggestions, phrase: s };
  }
  if (/图标集|icon\s*set|三色箭头/i.test(s)) {
    suggestions.push({
      iconDatas: [
        {
          index: 0,
          iconSetType: '0',
          iconCriteria: [
            { iconValue: '67', isGreaterThanOrEqualTo: true, iconValueType: 1 },
            { iconValue: '33', isGreaterThanOrEqualTo: true, iconValueType: 1 },
          ],
        },
      ],
      note: '图标集 → conditionRule.iconDatas（勿写 iconSets）',
    });
    return { ok: true, errors, suggestions, phrase: s };
  }

  // 介于 / 1-5 / 1～5 / 大于 x 且小于 y / 介于 1 5
  let m =
    s.match(/介于\s*([\d.]+)\s*(?:和|与|,|，|~|-|–|—|\s+)\s*([\d.]+)/) ||
    s.match(/([\d.]+)\s*[-~～–—]\s*([\d.]+)/) ||
    s.match(/大于\s*([\d.]+)\s*(?:且|and|AND)\s*小于\s*([\d.]+)/i);
  if (m) {
    suggestions.push({
      relation: 'highlight:interval',
      value1: m[1],
      value2: m[2],
      note: '区间必须用一条 interval（介于），禁止 between，禁止拆成两条 greater+less',
    });
    return { ok: true, errors, suggestions, phrase: s };
  }

  m = s.match(/大于等于\s*([\d.]+)/) || s.match(/≥\s*([\d.]+)/);
  if (m) {
    suggestions.push({ relation: 'highlight:greaterAndEquals', value1: m[1], value2: '' });
    return { ok: true, errors, suggestions, phrase: s };
  }
  m = s.match(/小于等于\s*([\d.]+)/) || s.match(/≤\s*([\d.]+)/);
  if (m) {
    suggestions.push({ relation: 'highlight:lessAndEquals', value1: m[1], value2: '' });
    return { ok: true, errors, suggestions, phrase: s };
  }
  m = s.match(/大于\s*([\d.]+)/) || s.match(/>\s*([\d.]+)/);
  if (m) {
    suggestions.push({ relation: 'highlight:greater', value1: m[1], value2: '' });
    return { ok: true, errors, suggestions, phrase: s };
  }
  m = s.match(/小于\s*([\d.]+)/) || s.match(/<\s*([\d.]+)/);
  if (m) {
    suggestions.push({ relation: 'highlight:less', value1: m[1], value2: '' });
    return { ok: true, errors, suggestions, phrase: s };
  }
  m = s.match(/等于\s*(.+)/);
  if (m) {
    suggestions.push({ relation: 'highlight:equals', value1: m[1].trim(), value2: '' });
    return { ok: true, errors, suggestions, phrase: s };
  }

  errors.push(
    `无法映射「${s}」。支持：大于/小于/介于、数据条、图标集等。请用户确认，禁止下载 SpreadJS 黑盒逆向。`
  );
  return { ok: false, errors, suggestions, phrase: s };
}

function validateFields(fields) {
  const allErrors = [];
  const allWarnings = [];
  const allSuggestions = [];
  const cells = [];

  for (const f of fields || []) {
    const rule = parseMaybe(f.conditionRule, null);
    if (!rule || (typeof rule === 'object' && !Object.keys(rule).length)) continue;
    if (rule.highlightDatas && parseMaybe(rule.highlightDatas, []).length === 0 && !rule.lineDatas && !rule.iconDatas) {
      continue;
    }
    const cellLabel = `(${f.x},${f.y}) ${f.text || f.cellType || ''}`;
    const r = validateConditionRule(rule, { cellLabel });
    cells.push({ x: f.x, y: f.y, text: f.text, ...r });
    allErrors.push(...r.errors);
    allWarnings.push(...r.warnings);
    allSuggestions.push(...r.suggestions);
  }

  return {
    ok: allErrors.length === 0,
    cells,
    errors: allErrors,
    warnings: allWarnings,
    suggestions: allSuggestions,
  };
}

function eteamsId() {
  return require('./eb_auth.js').eteamsId();
}

function get(host, urlPath, appId) {
  return new Promise((resolve, reject) => {
    const u = new URL(host + urlPath);
    const sid = eteamsId();
    https
      .get(
        {
          hostname: u.hostname, port: u.port || 443, path: u.pathname + u.search,
          headers: {
            eteamsid: sid,
            Cookie: `ETEAMSID=${sid}`,
            ebBusinessId: appId || '',
            Accept: 'application/json',
            'User-Agent': 'Mozilla/5.0 AgentType=WorkBuddy,IsAgent=true',
          },
          rejectUnauthorized: false,
        },
        (res) => {
          let d = '';
          res.on('data', (c) => (d += c));
          res.on('end', () => {
            try {
              resolve(JSON.parse(d));
            } catch {
              reject(new Error(d.slice(0, 300)));
            }
          });
        }
      )
      .on('error', reject);
  });
}

async function validateRemote(reportId, appId) {
  const host = resolveE10Host();
  let app = appId || '';
  if (!app) {
    const base = await get(host, `/api/bs/edc/report/baseInfo?id=${reportId}&useTag=backend`, '');
    app = String(base.data?.appId || '');
  }
  const dev = await get(host, `/api/bs/edc/report/getReportDevInfo?reportId=${reportId}`, app);
  if (dev.code !== 200) {
    return { ok: false, reportId, errors: [`getReportDevInfo: ${dev.msg || dev.code}`], warnings: [], suggestions: [] };
  }
  const checked = validateFields(dev.data?.fields || []);

  // 查询条件「显示方式」回显自检（§2.1）：queryType 必须以 "[" 开头（JSON 数组字符串）
  const echo = await checkQueryEcho(host, app, reportId);
  const errors = [...(checked.errors || []), ...echo.errors];
  const warnings = [...(checked.warnings || []), ...echo.warnings];
  return {
    reportId,
    appId: app,
    ok: errors.length === 0,
    errors,
    warnings,
    suggestions: [...(checked.suggestions || []), ...echo.suggestions],
    queryEcho: echo.conditions,
  };
}

/**
 * 回读查询条件，校验 queryType 是否为「数组短码」形态。
 * 规则见 references/query-condition-api-guide.md §2.1：
 *   前端只按首字符是否 "[" 决定是否 JSON.parse；长码 "advancedSearch" → 退化为字符串 → UI 不勾选。
 * 修复：edc-report query fix-echo --report-id <id> --app-id <appId>
 */
async function checkQueryEcho(host, appId, reportId) {
  const errors = [];
  const warnings = [];
  const suggestions = [];
  const conditions = [];
  let list = [];
  try {
    const r = await postMultipart(host, '/api/bs/edc/report/getQueryItemNew', { reportId: String(reportId), query: '{}' }, appId);
    list = r?.data?.list || [];
  } catch (e) {
    warnings.push(`查询条件回读失败（跳过回显校验）：${e.message || e}`);
    return { errors, warnings, suggestions, conditions };
  }
  for (const q of list) {
    const qt = q.queryType;
    const isArr = typeof qt === 'string' && qt.trim().startsWith('[');
    const text = q.text || '(未命名)';
    conditions.push({ text, queryType: qt, echoOk: isArr });
    if (!isArr) {
      const fixed = qt === 'filter' ? '["filter"]' : '["advance"]';
      errors.push(
        `查询条件「${text}」显示方式无法回显：queryType=${JSON.stringify(qt)} 不是数组短码 → 设计器不勾选；应为 ${fixed}`
      );
    }
  }
  if (errors.length) {
    suggestions.push(`执行 edc-report query fix-echo --report-id ${reportId} --app-id ${appId || '<appId>'} 一键修正`);
  }
  return { errors, warnings, suggestions, conditions };
}

/** POST multipart（用于 getQueryItemNew 等必须 multipart 的读接口） */
function postMultipart(host, urlPath, fields, appId) {
  return new Promise((resolve, reject) => {
    const boundary = '----edc' + Date.now().toString(16);
    const parts = [];
    for (const [k, v] of Object.entries(fields)) {
      parts.push(Buffer.from(`--${boundary}\r\nContent-Disposition: form-data; name="${k}"\r\n\r\n${v}\r\n`, 'utf8'));
    }
    parts.push(Buffer.from(`--${boundary}--\r\n`, 'utf8'));
    const body = Buffer.concat(parts);
    const u = new URL(host + urlPath);
    const sid = eteamsId();
    const req = https.request(
      {
        hostname: u.hostname, port: u.port || 443, path: u.pathname + u.search,
        method: 'POST',
        headers: {
          eteamsid: sid,
          Cookie: `ETEAMSID=${sid}`,
          ebBusinessId: appId || '',
          ebbusinessid: appId || '',
          'Content-Type': `multipart/form-data; boundary=${boundary}`,
          'Content-Length': body.length,
          Accept: 'application/json',
          'User-Agent': 'Mozilla/5.0 AgentType=WorkBuddy,IsAgent=true',
        },
        rejectUnauthorized: false,
      },
      (res) => {
        let d = '';
        res.on('data', (c) => (d += c));
        res.on('end', () => {
          try {
            resolve(JSON.parse(d));
          } catch {
            reject(new Error(d.slice(0, 300)));
          }
        });
      }
    );
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help || args.h) {
    console.log(`Usage:
  node validate_condition_format.js --file rule.json
  node validate_condition_format.js --inline '{"highlightDatas":[...]}'
  node validate_condition_format.js --report-id <id> [appId]
  node validate_condition_format.js --map "介于 1 5"`);
    process.exit(0);
  }

  let result;
  if (args.map != null) {
    result = mapNaturalPhrase(args.map === true ? args._[0] : args.map);
  } else if (args['report-id'] || args.reportId) {
    const rid = args['report-id'] || args.reportId;
    const appId = args['app-id'] || args.appId || args._[0] || '';
    result = await validateRemote(rid, appId);
  } else if (args.file) {
    const raw = fs.readFileSync(args.file, 'utf8').replace(/^\uFEFF/, '');
    result = validateConditionRule(JSON.parse(raw));
  } else if (args.inline) {
    result = validateConditionRule(JSON.parse(args.inline));
  } else if (args._[0] && fs.existsSync(args._[0])) {
    result = validateConditionRule(
      JSON.parse(fs.readFileSync(args._[0], 'utf8').replace(/^\uFEFF/, ''))
    );
  } else {
    console.error('需要 --file / --inline / --report-id / --map');
    process.exit(2);
  }

  console.log(JSON.stringify(result, null, 2));
  process.exit(result.ok ? 0 : 1);
}

if (require.main === module) {
  main().catch((e) => {
    console.error(e.message || e);
    process.exit(1);
  });
}

module.exports = {
  ALLOWED,
  ALIAS_FIX,
  validateConditionRule,
  validateFields,
  mapNaturalPhrase,
  validateRemote,
};
