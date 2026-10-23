'use strict';
/**
 * saveQueryItem — multipart 单对象（防 500）+ 显示方式强制默认高级搜索
 * 对应 query-condition-api-guide.md §二 / §2.1
 *
 *   node save_query_item.js --report-id <id> --app-id <appId> --item <queryItem.json>
 *   node save_query_item.js --report-id <id> --app-id <appId> --list
 *   node save_query_item.js --report-id <id> --app-id <appId> --type [--show-where 高级搜索|筛选]
 *   node save_query_item.js --report-id <id> --app-id <appId> --check-echo     # 回读回显自检
 *   node save_query_item.js --report-id <id> --app-id <appId> --fix-echo       # 长码→数组 一键修正
 *   node save_query_item.js --validate-show-where --file item.json
 *   node save_query_item.js --map-show-where "筛选"
 *
 * 强制：显示方式默认「高级搜索」（条件级落 queryType='["advance"]' JSON 数组字符串；报表级 updateQueryType 走长码）；
 *       用户点名筛选才 '["filter"]'。showWhere 一律写 ""（遗留字段）。
 * 说明：条件级 queryType 必须是含 "[" 的 JSON 数组字符串，设计器 UI 才会勾选对应显示方式（详见 query-condition-api-guide.md §2.1）。
 * save 成功后自动 POST updateQueryType（报表级 + 批量覆盖所有条件，入参同为数组短码 '["advance"]'）。
 */

const fs = require('fs');
const https = require('https');
const { resolveE10Host } = require('./resolve_e10_host');

const SHOW_WHERE_MAP = {
  高级搜索: 'advancedSearch',
  高级: 'advancedSearch',
  advancedsearch: 'advancedSearch',
  advancedSearch: 'advancedSearch',
  advanced: 'advancedSearch',
  筛选: 'filter',
  顶部筛选: 'filter',
  筛选条件: 'filter',
  filter: 'filter',
};

function parseArgs(argv) {
  const o = { _: [] };
  const flags = new Set(['list', 'type', 'skip-query-type', 'validate-show-where', 'skip-display-type', 'check-echo', 'fix-echo', 'no-verify-echo']);
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const key = a.slice(2);
      if (flags.has(key) || i + 1 >= argv.length || String(argv[i + 1]).startsWith('--')) {
        o[key] = true;
      } else {
        o[key] = argv[++i];
      }
    } else o._.push(a);
  }
  return o;
}

function eteamsId() {
  return require('./eb_auth.js').eteamsId();
}

/**
 * 解析显示方式输入短语 → 内部语义 token（'advancedSearch' / 'filter'）。
 * 注意：这只是**输入侧**的规范化 token，不是落库值。
 *   落库时统一经 resolveQueryType() 转成数组短码 '["advance"]' / '["filter"]'（条件级 + 报表级同形态）。
 */
function resolveShowWhere(hint) {
  if (hint == null || hint === '' || hint === true) return 'advancedSearch';
  const raw = String(hint).trim();
  if (SHOW_WHERE_MAP[raw]) return SHOW_WHERE_MAP[raw];
  const lower = raw.toLowerCase();
  if (SHOW_WHERE_MAP[lower]) return SHOW_WHERE_MAP[lower];
  if (/筛选|filter/i.test(raw) && !/高级搜索|advanced/i.test(raw)) return 'filter';
  if (/高级搜索|advanced/i.test(raw)) return 'advancedSearch';
  // 短码容错（前端枚举值，用户可能照 UI 源码/抓包直填）→ 归一到长码
  if (raw === 'advance' || raw === 'advanced') return 'advancedSearch';
  if (raw === 'filter') return 'filter';
  return null;
}

/**
 * 显示方式 → 条件级 queryType（前端唯一能回显勾选的形态）
 *
 * ✅ 2026-09-11 终局定案（以「设计器人工配置的条件」为金标准反推）：
 *   - 落库必须是 **JSON 数组字符串**：'["advance"]'（高级搜索）/ '["filter"]'（筛选），
 *     可双选 '["advance","filter"]'。
 *   - 前端回显唯一判据（_src/route_DatasetList.js · initCondition）：
 *       t.queryType = (t.queryType?.indexOf("[") > -1)
 *           ? JSON.parse(t.queryType || "[]")   // 含 "[" → 解析为数组
 *           : t.queryType || [];                // 不含 → 原样保留为字符串
 *     复选框选项 id 是短码（lib.js: advance="advance" / filter="filter"），
 *     CheckboxGroup **严格相等**比数组元素 vs 选项 id：
 *       '["advance"]'  → ["advance"] → "advance" === "advance" → ☑ 勾选 ✅
 *       "advancedSearch" → 字符串 → "advancedSearch" !== "advance" → ☐ 不勾 ❌
 *   - 新建条件前端默认值也是数组：`this.fieldKey || (i.queryType = ["advance"])`；
 *     抓包确认设计器上行 payload 即 `"queryType":["advance"]`。
 *   - **服务端对取值不敏感**：'["advance"]' / '["filter"]' / '["advance","filter"]' /
 *     "advancedSearch" 全部返回 200 并原样落库；差别只在 UI 回显。
 *
 * ⚠️ 旧结论已推翻：曾误判「落库写长码 advancedSearch、写短码 500、UI 不勾是平台缺陷」。
 *     真实原因是早期用 JS 合成事件点到了左侧「字段属性」面板（非条件弹窗），读取了假信号；
 *     改用 CDP 真实鼠标事件点条件 tag + 以人工条件为金标准后定案如上。
 *     那个 500 与 queryType 取值无关，是手写 multipart payload 结构不被服务端封装接受。
 */
function resolveQueryType(showWhere) {
  return showWhere === 'filter' ? '["filter"]' : '["advance"]';
}

/**
 * 数组短码 queryType → 显示方式短名（filter / advancedSearch）。
 * 只处理「单一意图」的两种形态；双选 `["advance","filter"]` 返回 null（调用方应原样保留入参）。
 */
function qtToShowWhere(qt) {
  if (typeof qt !== 'string' || !qt.trim().startsWith('[')) return null;
  try {
    const a = JSON.parse(qt);
    if (!Array.isArray(a)) return null;
    const hasF = a.includes('filter');
    const hasA = a.includes('advance');
    if (hasF && !hasA) return 'filter';
    if (hasA && !hasF) return 'advancedSearch';
    return null;
  } catch (e) { return null; }
}

function normalizeShowWhere(item, hintFromCli) {
  const errors = [];
  const warnings = [];
  const fromCli = hintFromCli != null && hintFromCli !== true ? resolveShowWhere(hintFromCli) : null;
  const fromItem =
    item && item.showWhere != null && item.showWhere !== ''
      ? resolveShowWhere(item.showWhere)
      : null;
  // 入参自带数组 queryType（回读对象派生）→ 以它为准，避免被默认值 advancedSearch 覆盖。
  // ⚠️ 历史 bug：保存一条「筛选」条件时，入参 queryType='["filter"]' 被强行改成 '["advance"]'
  // → 静默把该条件的显示方式从「筛选」改成「高级搜索」。
  const fromItemQt = qtToShowWhere(item && item.queryType);

  let showWhere = fromCli || fromItem || fromItemQt || 'advancedSearch';
  if (fromCli == null && hintFromCli != null && hintFromCli !== true && String(hintFromCli).trim()) {
    errors.push(`无法映射显示方式「${hintFromCli}」。支持：高级搜索/筛选（advancedSearch/filter）`);
  }
  if (item && item.showWhere != null && item.showWhere !== '' && fromItem == null) {
    errors.push(`非法 showWhere=${item.showWhere}；须为 advancedSearch|filter`);
  }
  if (!showWhere) {
    errors.push('showWhere 不能为空；默认 advancedSearch');
    showWhere = 'advancedSearch';
  }
  if (item.showWhere == null) {
    // 注意：设计器恒写 showWhere:""（遗留字段）；传空串是**正确**值，不应再告警
    warnings.push('未指定 showWhere，已默认 advancedSearch（高级搜索）');
  } else if (fromCli && fromCli !== item.showWhere) {
    warnings.push(`CLI --show-where 覆盖为 ${showWhere}`);
  }
  return { ok: errors.length === 0, errors, warnings, showWhere };
}

/**
 * 关联类型 browserType 简写预设（**仅作兜底占位**）。
 *
 * ⚠️ 2026-09-11 实证定案：**简写不足以让 UI 正确回显**。
 *   落库（browserTypeStr）可用简写，但设计器「关联类型」会显示为空
 *   （前端拿不到 name 无法渲染标签，控件容器带 `is-empty`）。
 *   **要 UI 正确回显，必须写 13 键全字段富对象**，且富对象只能从服务端取：
 *
 *       GET /api/bcw/relevanceBrowser/browserBeanSearch?searchValue=<中文名>  (需 appId 头)
 *       → data.data[]   按 name 取「人员」「部门」…
 *
 *   实测取值：
 *     人员 = {"id":"3332180495306215441","tenantKey":"thfnde9fvr","deleteType":0,
 *             "dataId":"2005096031068185492","licenseModule":"hrm","labelId":"29511",
 *             "disable":0,"systemDefault":1,"ebuliderDataBrowser":false,
 *             "name":"人员","module":"hrm","type":"resource","groupId":"3332180495271315421"}
 *     部门 = 同结构，type:"department" / labelId:"52148" / id:"3332180495306215437"
 *
 *   下方简写仅用于「字段类型推导」与 `browserTypeStr` 生成，勿当作最终 browserType 写入。
 *   详见 query-condition-api-guide.md §2.1.2.1。
 */
const BROWSER_PRESET = {
  employee: [{ id: 'HrmEmployeeComInfo' }],
  department: [{ id: 'HrmDepartmentComInfo' }],
  departmentallpath: [{ id: 'HrmDepartmentAllPathComInfo' }],
};
const BROWSER_STR_PRESET = BROWSER_PRESET;

/**
 * 从关联浏览分类接口抓取完整富对象（需联网；失败时返回 null，由调用方降级为简写 + WARN）。
 *
 * ⚠️ 2026-09-14 实测修正：**本环境（及其它产品版本）`POST .../getBrowserBean` 返回 500**
 *    （前端其实把 `browserBeanSearch` 请求本地拦截了 —— 见 lib.js 的 relationList 分支），
 *    真正可用的是 **GET**：
 *
 *        GET /api/bcw/relevanceBrowser/browserBeanSearch?searchValue=<中文名>
 *        → data.data[]  每条 = 13 键富对象（id/tenantKey/dataId/labelId/name/type/module/
 *          groupId/licenseModule/title/systemDefault/disable/deleteType/ebuliderDataBrowser）
 *
 *    实测（租户 tmxislnm9p）：searchValue=部门 → id=2005096031068185488 type=department；
 *                              searchValue=人员 → id=2005096031068185492 type=resource。
 *    searchValue 用**中文分类名**（拼音检索服务端不支持，`bm`/`ry` 返回 0 条）。
 *
 * @param {object} http  { get(path, params) | post(path, params) } 适配器，或 null 走离线模式
 * @param {string} name  分类显示名，如 '人员' / '部门'
 * @param {string} appId 应用 id（写 ebbusinessid 头）
 */
async function fetchBrowserTypeBean(http, name, appId) {
  if (!http || typeof http.get !== 'function') return null;
  try {
    const r = await http.get(
      `/api/bcw/relevanceBrowser/browserBeanSearch?searchValue=${encodeURIComponent(name)}`,
      { appId }
    );
    const list = ((((r || {}).data || {}).data) || []);
    const hit = list.find((x) => x && x.name === name);
    if (hit) return hit;
  } catch (e) { /* 接口不可用 → 降级 */ }
  return null;
}

/** originFieldType → 关联分类中文名（富对象检索用） */
const BROWSER_LABEL = {
  employee: '人员',
  department: '部门',
  departmentallpath: '部门（全路径）',
};

/**
 * 按字段 originFieldType 推导 displayType / browserType / relation。
 * 仅当 item 未显式给出 displayType 时生效（显式优先，尊重用户/上游取值）。
 * 见 query-condition-api-guide.md §3.1、cell-transform-guide.md §1.1。
 */
function resolveQueryDisplayType(item, fieldMeta) {
  const explicitlySet = !!item.displayType;
  const ft = String((fieldMeta && fieldMeta.fieldType) || '').toLowerCase();
  const oft = String((fieldMeta && fieldMeta.originFieldType) || '').toLowerCase();
  const fmt = String((fieldMeta && ((fieldMeta.config && fieldMeta.config.format) || fieldMeta.format)) || '');
  const name = String(item.text || '') + ' ' + String((fieldMeta && fieldMeta.text) || '');

  let r = null;
  if (oft === 'employee') {
    r = { displayType: 'browser', browserType: BROWSER_PRESET.employee, relation: 'Equals' };
  } else if (oft === 'department') {
    r = { displayType: 'browser', browserType: BROWSER_PRESET.department, relation: 'Equals' };
  } else if (oft === 'departmentallpath') {
    r = { displayType: 'browser', browserType: BROWSER_PRESET.departmentallpath, relation: 'Equals' };
  } else if (/年月/.test(name) || fmt === 'yyyy-MM') {
    r = { displayType: 'date.ym', relation: 'between' };
  } else if (/年份|年度|^年$/.test(name) || fmt === 'yyyy') {
    r = { displayType: 'date', relation: 'between' };
  } else if (/日期|时间|时段|期间/.test(name) || ['date', 'datetime', 'time', 'timestamp'].includes(ft) ||
             ['date', 'datetime', 'time'].includes(oft)) {
    r = { displayType: fmt.startsWith('yyyy-MM-dd') || !fmt ? 'date.ymd' : 'date', relation: 'between' };
  } else if (oft === 'select') {
    r = { displayType: 'select', relation: 'Equals' };
  } else {
    r = { displayType: 'text', relation: 'Contain' };
  }
  if (explicitlySet) {
    // 显式 displayType 优先，但保留正确的 browserType / relation 供校验
    r.displayType = item.displayType;
    if (item.conditions && item.conditions.length && item.conditions[0].relation) {
      r.relation = item.conditions[0].relation;
    }
  }
  return r;
}

/**
 * 对单条查询条件补齐 displayType/browserType/relation。
 * @returns {{item:object, changes:string[], warnings:string[]}}
 */
function applyQueryDisplayType(item, fieldMeta) {
  const changes = [];
  const warnings = [];
  const r = resolveQueryDisplayType(item, fieldMeta);
  if (!r) return { item, changes, warnings };

  const oft = String((fieldMeta && fieldMeta.originFieldType) || '').toLowerCase();

  if (!item.displayType) {
    item.displayType = r.displayType;
    changes.push(`displayType → ${r.displayType}`);
  }

  if (item.displayType === 'browser') {
    const expected = r.displayType === 'browser' ? r.browserType : null;
    const bt = Array.isArray(item.browserType) ? item.browserType : [];
    const btIds = bt.map((x) => String((x && x.id) || x));
    const wantLabel = BROWSER_LABEL[oft] || null;
    // 富对象（>1 键，如 designer 写入的 13 键对象）其 `id` 是业务 id（部门/人员 的数据 id），
    // **不等于** ComInfo 短 id；此时应以 `name` 判类型，不能按 id 比对 → 否则误报「不匹配」。
    const richOk = bt.some((x) => x && typeof x === 'object' && Object.keys(x).length > 1 &&
      (!wantLabel || String(x.name || '') === wantLabel));
    // 始终同步 browserTypeStr（落库判据；服务端存 [{"id":"HrmDepartmentComInfo"}] 形式）
    const btStrExpected = expected ? JSON.stringify(expected) : null;
    if (!bt.length && expected) {
      item.browserType = expected;
      changes.push(`browserType → ${JSON.stringify(expected)}`);
    } else if (!bt.length) {
      warnings.push('displayType=browser 但 browserType 为空 → 设计器关联类型**必为空**（实测），须补富对象');
    } else if (expected && !richOk && !btIds.some((id) => expected.map((e) => e.id).includes(id))) {
      warnings.push(
        `关联类型不匹配：字段为 ${oft || '未知'}，browserType=${JSON.stringify(btIds)}` +
          `（期望 ${expected.map((e) => e.id).join('/')}）→ 设计器关联类型将不正确`
      );
    }
    if (btStrExpected && item.browserTypeStr !== btStrExpected) {
      item.browserTypeStr = btStrExpected;
      changes.push(`browserTypeStr → ${btStrExpected}`);
    }
    // 富对象提示：仅 [{id}] 简写 → UI 关联类型必为空（实测：控件 is-empty + value=""）
    if (bt.length && bt.every((x) => x && Object.keys(x).length === 1)) {
      const label = oft === 'employee' ? '人员' : oft === 'department' ? '部门'
                  : oft === 'departmentallpath' ? '部门（全路径）' : null;
      warnings.push(
        'browserType 仅含 id 简写：落库（browserTypeStr）正确，但设计器「关联类型」**必为空**（实测）。' +
          '请改用富对象：GET /api/bcw/relevanceBrowser/browserBeanSearch?searchValue=<中文名> 取' +
          (label ? `「${label}」` : '对应分类') + '的 13 键全字段对象（见 query-condition-api-guide.md §2.1.2.1）'
      );
    }
  }

  if (Array.isArray(item.conditions)) {
    for (const c of item.conditions) {
      if (c && !c.relation) {
        c.relation = r.relation;
        changes.push(`conditions[].relation → ${r.relation}`);
      }
    }
  }
  return { item, changes, warnings };
}

/**
 * 从 conditions[0] 三段 fieldKey 解析 dataSetId/sourceId/fieldName，
 * 再查 fieldsAndOriginFields 取该字段的 fieldType/originFieldType。
 * 失败不阻断保存（仅告警）。
 */
async function fetchFieldMeta(host, headers, reportId, appId, item) {
  const cond = (item.conditions || [])[0];
  if (!cond || !cond.fieldId) throw new Error('conditions[0].fieldId 缺失');
  const parts = String(cond.fieldId).split('.');
  if (parts.length < 3) throw new Error(`fieldId 非三段式：${cond.fieldId}`);
  const [datasetId, sourceId, fieldName] = parts;

  const qs = `datasetId=${encodeURIComponent(datasetId)}&hasField=true&isFront=true` +
             `&reportId=${encodeURIComponent(reportId)}&appId=${encodeURIComponent(appId)}`;
  const res = await request('GET', `${host}/api/bs/edc/dataset/fieldsAndOriginFields?${qs}`, null, headers);
  const list = (res.json && res.json.data && res.json.data.fieldsKey) || [];
  const hit =
    list.find((f) => String(f.name) === String(fieldName)) ||
    list.find((f) => String(f.name) === String(fieldName).replace(/^field_/, ''));
  if (!hit) throw new Error(`fieldsKey 未命中 ${fieldName}`);
  if (parts[1] !== String(sourceId)) {
    // fieldKey 中段须与数据集 sourceId 一致，否则查询条件不会真正过滤
    console.error(`WARN fieldKey 中段 sourceId=${sourceId}，与数据集不符时条件将不过滤`);
  }
  return hit;
}

/**
 * GET 关联浏览分类 —— **富对象的权威来源**（见 fetchBrowserTypeBean 注释的 2026-09-14 修正）。
 * 本环境 POST .../getBrowserBean 恒 500；GET .../browserBeanSearch?searchValue=<中文名> 可用。
 */
async function fetchBrowserBeanSearch(host, headers, name) {
  const res = await request(
    'GET',
    `${host}/api/bcw/relevanceBrowser/browserBeanSearch?searchValue=${encodeURIComponent(name)}`,
    null,
    headers
  );
  const list = (((res.json || {}).data || {}).data) || [];
  return list.find((x) => x && x.name === name) || null;
}

function buildMultipart(fieldsObj) {
  const boundary = `----EdcQuery${Date.now()}`;
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
      {
        method,
        hostname: u.hostname, port: u.port || 443, path: u.pathname + u.search,
        headers,
        rejectUnauthorized: false,
      },
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

/** 保存单条查询条件（已归一化的对象）。--check-echo/--fix-echo 复用。 */
async function saveOne(host, headers, reportId, item) {
  const { body, contentType } = buildMultipart({
    reportId: String(reportId),
    queryItems: JSON.stringify(item),
  });
  return request('POST', `${host}/api/bs/edc/report/saveQueryItem`, body, {
    ...headers,
    'Content-Type': contentType,
    'Content-Length': body.length,
  });
}

/**
 * 落库后回读自检：确认指定条件（或全部）的 queryType 是数组短码。
 * 规则见 references/query-condition-api-guide.md §2.1。
 */
async function verifyEcho(host, headers, reportId, itemId) {
  try {
    const { body, contentType } = buildMultipart({ reportId: String(reportId), query: '{}' });
    const res = await request('POST', `${host}/api/bs/edc/report/getQueryItemNew`, body, {
      ...headers,
      'Content-Type': contentType,
      'Content-Length': body.length,
    });
    const list = (res.json?.data?.list || []).filter((q) => !itemId || String(q.id) === String(itemId));
    const rows = list.map((q) => {
      const qt = q.queryType;
      const ok = typeof qt === 'string' && qt.trim().startsWith('[');
      return { text: q.text, queryType: qt, echoOk: ok };
    });
    const allOk = rows.length > 0 && rows.every((r) => r.echoOk);
    return {
      allOk,
      rows,
      hint: allOk ? null : `显示方式将无法回显；执行 edc-report query fix-echo --report-id ${reportId} --app-id <appId> 修正`,
    };
  } catch (e) {
    return { allOk: null, error: String(e.message || e) };
  }
}

/**
 * 报表级 updateQueryType —— ⚠️ 它同时**批量覆盖所有条件**的 queryType！
 *
 * ✅ 2026-09-11 实证（决定性根因）：
 *   对同一报表连续调用 updateQueryType，刚写入的数组短码会被**全量改写成入参值**：
 *     updateQueryType(queryType="advancedSearch")  → 条件级全部变 "advancedSearch"（回显丢失）
 *     updateQueryType(queryType='["advance"]')     → 条件级全部变 '["advance"]'（回显正常）
 *     updateQueryType(queryType="advance")         → 条件级全部变 "advance"（也丢）
 *   → **入参必须是数组短码字符串** `'["advance"]'` / `'["filter"]'`，与条件级同形态。
 *
 * 这正是历史 bug 的真正根因：旧版 CLI 在 save 后调用 updateQueryType("advancedSearch")，
 * 把刚写好的数组条件全部打回长码 → 设计器永不勾选；而人工在页面直接配的条件
 * 不经过该接口，所以 `["advance"]` 一直完好、回显正常。
 */
async function updateQueryType(host, headers, reportId, showWhere) {
  // 入参可以是短名（filter/advancedSearch）或**已是 JSON 数组短码字符串**（原样透传，避免信息丢失）
  const queryType = /^\s*\[/.test(String(showWhere)) ? String(showWhere)
    : (showWhere === 'filter' ? '["filter"]' : '["advance"]');
  const fields = {
    reportId: String(reportId),
    queryType,
  };
  // ⚠️ 禁止在此附带 advancedSearchType！
  // 旧实现曾在 queryType=advance 时追加 `advancedSearchType:'openCondition'`，
  // 把报表页查询区从「默认样式」改成「展开条件」——属于用户未点名的**展示格式**改动。
  // 本接口只负责批量对齐 `queryType`，不得夹带任何展示样式字段。
  const { body, contentType } = buildMultipart(fields);
  return request('POST', `${host}/api/bs/edc/report/updateQueryType`, body, {
    ...headers,
    'Content-Type': contentType,
    'Content-Length': body.length,
  });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));

  if (args['map-show-where'] != null) {
    const v = resolveShowWhere(args['map-show-where']);
    const out = {
      ok: !!v,
      showWhere: v || null,
      error: v ? null : `无法映射「${args['map-show-where']}」`,
      map: SHOW_WHERE_MAP,
    };
    console.log(JSON.stringify(out, null, 2));
    process.exit(v ? 0 : 1);
  }

  if (args['validate-show-where']) {
    let item = {};
    if (args.file) item = JSON.parse(fs.readFileSync(args.file, 'utf8'));
    else if (args.inline) item = JSON.parse(args.inline);
    const r = normalizeShowWhere(item, args['show-where']);
    console.log(
      JSON.stringify(
        {
          ok: r.ok,
          errors: r.errors,
          warnings: r.warnings,
          normalized: { showWhere: r.showWhere },
        },
        null,
        2
      )
    );
    process.exit(r.ok ? 0 : 1);
  }

  const reportId = args['report-id'] || args.reportId;
  const appId = args['app-id'] || args.appId;
  const host = resolveE10Host({ host: args.host });
  if (!reportId || !appId) {
    console.error(
      'Usage: save_query_item.js --report-id <id> --app-id <appId> (--item file | --list | --type | --check-echo | --fix-echo) [--show-where 高级搜索|筛选] [--skip-display-type]'
    );
    process.exit(2);
  }

  const et = eteamsId();
  const headers = {
    eteamsid: et,
    ebBusinessId: appId,
    ebbusinessid: appId,
    Cookie: `langType=zh_CN; LOGIN_TYPE=pc_account; ETEAMSID=${et}`,
    Accept: 'application/json',
    'User-Agent': 'Mozilla/5.0 AgentType=WorkBuddy,IsAgent=true',
    Referer: `${host}/sp/edc/report/designer/${reportId}`,
  };

  if (args.list) {
    const { body, contentType } = buildMultipart({ reportId: String(reportId), query: '{}' });
    const res = await request('POST', `${host}/api/bs/edc/report/getQueryItemNew`, body, {
      ...headers,
      'Content-Type': contentType,
      'Content-Length': body.length,
    });
    console.log(JSON.stringify(res.json, null, 2));
    process.exit(res.json?.code === 200 ? 0 : 1);
  }

  if (args.type) {
    // ⚠️ updateQueryType 是**报表级批量覆盖**接口：会把该报表所有条件的显示方式一起改。
    // 未显式传 --show-where = 用户没点名 → 只回读，绝不落库（最高优先级政策：仅改点名项）。
    const explicit = args['show-where'] != null && args['show-where'] !== true && String(args['show-where']).trim() !== '';
    if (!explicit) {
      const echo = await verifyEcho(host, headers, reportId, null);
      console.log(
        JSON.stringify(
          {
            ok: true,
            readOnly: true,
            hint: '未传 --show-where → 只回读，不调用 updateQueryType（它是批量覆盖接口，会把整表显示方式一起改）',
            current: echo,
            howToChange: 'edc-report query type --report-id <id> --app-id <id> --show-where 筛选|高级搜索',
          },
          null,
          2
        )
      );
      process.exit(0);
    }
    const sw = resolveShowWhere(args['show-where']);
    const res = await updateQueryType(host, headers, reportId, sw);
    // 该接口会批量覆盖所有条件的 queryType，落库后回读确认
    let echoCheck = null;
    if (res.json?.code === 200) echoCheck = await verifyEcho(host, headers, reportId, null);
    console.log(
      JSON.stringify(
        {
          ok: res.json?.code === 200,
          showWhere: sw,
          queryType: resolveQueryType(sw), // 数组短码（同时写入报表级并可被条件级沿用）
          scope: 'report-level + 批量覆盖所有条件',
          status: res.status,
          code: res.json?.code,
          msg: res.json?.msg,
          echoCheck,
        },
        null,
        2
      )
    );
    process.exit(res.json?.code === 200 ? 0 : 1);
  }

  // --check-echo：回读全部条件，报告「显示方式能否正确回显」；--fix-echo 顺带修正为数组
  if (args['check-echo'] || args['fix-echo']) {
    const { body, contentType } = buildMultipart({ reportId: String(reportId), query: '{}' });
    const res = await request('POST', `${host}/api/bs/edc/report/getQueryItemNew`, body, {
      ...headers,
      'Content-Type': contentType,
      'Content-Length': body.length,
    });
    const list = res.json?.data?.list || [];
    const report = [];
    let anyFixed = false;
    for (const q of list) {
      const qt = q.queryType;
      const isArr = typeof qt === 'string' && qt.trim().startsWith('[');
      const row = { text: q.text, id: q.id, queryType: qt, echoOk: isArr };
      if (!isArr && args['fix-echo']) {
        const fixed = qt === 'filter' ? '["filter"]' : '["advance"]';
        const it = { ...q, queryType: fixed };
        for (const k of Object.keys(it)) {
          if (/_Str$/.test(k) || k === 'handleDefaultValue' || k === 'updateTime') delete it[k];
        }
        const up = await saveOne(host, headers, reportId, it);
        row.fixedTo = fixed;
        row.fixCode = up.json?.code;
        if (up.json?.code === 200) anyFixed = true;
      }
      report.push(row);
    }
    // 修正后把报表级也对齐为数组形态，避免后续 updateQueryType 又把条件打回长码（§2.1.3）
    // ⚠️ 禁止硬编码 'advancedSearch'！updateQueryType 是**批量覆盖**接口，硬编码会把
    // 原本是「筛选」的条件一起改成「高级搜索」（擅改展示格式）。改为从**修正后的条件实际值**
    // 反推：全部一致才对齐，不一致就跳过（并说明）。
    let typeRes = null;
    if (anyFixed) {
      const vals = [...new Set(report.filter((r) => r.echoOk || r.fixCode === 200).map((r) => {
        const fixed = r.fixedTo || r.queryType;
        try { return JSON.stringify(JSON.parse(fixed)); } catch (e) { return null; }
      }).filter(Boolean))];
      if (vals.length === 1) {
        typeRes = await updateQueryType(host, headers, reportId, vals[0]); // 已是数组短码 → 原样透传
      } else {
        console.error(`NOTE 报表内条件显示方式不一致（${vals.join(' / ')}）→ 跳过报表级对齐，避免批量覆盖`);
      }
    }
    console.log(
      JSON.stringify(
        { reportId, total: list.length, report, updateQueryType: typeRes ? typeRes.json?.code : null },
        null,
        2
      )
    );
    process.exit(report.every((r) => r.echoOk || r.fixCode === 200) ? 0 : 1);
  }

  const itemPath = args.item;
  if (!itemPath || !fs.existsSync(itemPath)) {
    console.error('需要 --item <queryItem.json>（单条对象）');
    process.exit(2);
  }

  let item = JSON.parse(fs.readFileSync(itemPath, 'utf8'));
  if (Array.isArray(item)) {
    console.error('禁止 queryItems 为数组；请传单条对象。见 query-condition-api-guide.md §二点五');
    process.exit(2);
  }
  if (!item.conditions || !Array.isArray(item.conditions) || item.conditions.length === 0) {
    console.error('conditions 必须为非空数组，否则服务端 NPE → 500');
    process.exit(2);
  }

  const norm = normalizeShowWhere(item, args['show-where']);
  if (!norm.ok) {
    console.error(JSON.stringify(norm, null, 2));
    process.exit(1);
  }
  item.showWhere = ''; // 遗留字段，设计器一律写空；显示方式由 queryType 表达
  // ⚠️ 入参已自带合法数组 queryType（含双选）且用户**没有**显式 --show-where → **原样保留**，
  // 不得用默认值 advancedSearch 覆盖（历史 bug：保存筛选条件时把它改成高级搜索）。
  const payloadQt = typeof item.queryType === 'string' && item.queryType.trim().startsWith('[') ? item.queryType : null;
  if (payloadQt && !args['show-where']) {
    item.queryType = payloadQt;
    console.error(`NOTE 显示方式沿用入参 ${payloadQt}（未传 --show-where）。需改写请显式 --show-where <高级搜索|筛选>`);
  } else {
    item.queryType = resolveQueryType(norm.showWhere); // JSON 数组字符串，前端唯一能回显勾选的形态
  }
  // ⚠️ 禁止默认注入 advancedSearchType！
  // 历史 bug：此处曾无条件写 `'openCondition'`（=「展开条件」），把报表页查询区的
  // **原有展示样式**（默认样式/右上角搜索图标）改成了展开态 —— 用户从未要求过。
  // 后端 `SheetServiceImpl` 会取第一条高级搜索条件的 `advancedSearchType` 决定
  // `isOpenCondition`，一旦为 'openCondition' 即整片查询区展开。详见
  // `query-condition-api-guide.md` §2.1.8。
  // 规则：**入参没有该键 → 就不写该键**（保持线上原值/不设定）。
  // 确需展开条件时，调用方须显式传 `--advanced-search-type openCondition`。
  const ast = args['advanced-search-type'];
  if (ast !== undefined) {
    item.advancedSearchType = ast === 'none' || ast === 'default' ? '' : String(ast);
    console.error(`WARN advancedSearchType 由 CLI --advanced-search-type 显式写为 ${JSON.stringify(item.advancedSearchType)}`);
  }
  // ─── 默认值三件套（防"弹窗炸开"）────────────────────────────────────────────
  // `defaultValueType` 是设计器弹窗渲染默认值区的**驱动字段**。漏写 →
  // 「默认值类型」显示"请选择"、默认值区把所有控件变体同时铺开、其后的
  // 「日期类型/显示位置/条件必填/查询条件」被顶出可视区（用户会认为"样式被改坏了"）。
  // 设计器「新建条件」模板本身带 `defaultValueType:"default"` + `defaultValue:["",""]`，
  // 因此这里只**补缺失**、绝不覆盖已有值。详见 references/query-condition-api-guide.md §2.1.10。
  if (!item.defaultValueType || String(item.defaultValueType) === '') {
    item.defaultValueType = 'default';
    console.error(
      'WARN 入参缺 defaultValueType → 已按设计器模板补为 "default"（常规）。' +
        '需自定义默认值请用 fix query-default --set "<文本>=custom:<JSON值>"。'
    );
  }
  if (item.defaultValue == null || String(item.defaultValue) === '') {
    item.defaultValue = item.defaultValueType === 'custom'
      ? (item.type2DefaultValue || '["",""]')
      : (item.type1DefaultValue || '["",""]');
  }
  if (item.type1DefaultValue == null) item.type1DefaultValue = item.defaultValueType === 'default' ? item.defaultValue : '';
  if (item.type2DefaultValue == null) item.type2DefaultValue = item.defaultValueType === 'custom' ? item.defaultValue : '';
  if (!item.filterParam) {
    item.filterParam = {
      optionTile: {}, isTile: false, multiple: true, dataOptions: [],
      enableOption: false, required: false, dateSelectDefaultValue: '',
      numberSelectDefaultValue: '', eBuilderForm: '', titleField: '',
    };
  }
  // 关联类型必须区分人员/部门，留空 → 设计器退回「人员」（历史回归事故）
  let autoDisplay = { changes: [], warnings: [] };
  if (!args['skip-display-type']) {
    try {
      const meta = await fetchFieldMeta(host, headers, reportId, appId, item);
      const r = applyQueryDisplayType(item, meta);
      autoDisplay = r;
      // 关联浏览类：把 [{id}] 简写升级为富对象（设计器「关联类型」回显的唯一正确形态）
      const oft = String((meta && meta.originFieldType) || '').toLowerCase();
      const wantLabel = BROWSER_LABEL[oft];
      if (item.displayType === 'browser' && wantLabel) {
        const onlyShorthand = !Array.isArray(item.browserType) || !item.browserType.length ||
          item.browserType.every((x) => x && Object.keys(x).length === 1);
        if (onlyShorthand) {
          const bean = await fetchBrowserBeanSearch(host, headers, wantLabel);
          if (bean) {
            item.browserType = [bean];
            autoDisplay.changes.push(`browserType → 富对象(${wantLabel})`);
            autoDisplay.warnings = autoDisplay.warnings.filter((w) => !/仅含 id 简写|关联类型.*为空/.test(w));
          } else {
            autoDisplay.warnings.push(
              `未能取到「${wantLabel}」富对象（browserBeanSearch 无命中）→ 设计器关联类型可能显示为空`
            );
          }
        }
      }
    } catch (e) {
      autoDisplay.warnings.push(`字段元数据获取失败，未自动补齐 displayType：${e.message || e}`);
    }
  }
  if (autoDisplay.warnings.length) {
    for (const w of autoDisplay.warnings) console.error(`WARN ${w}`);
  }

  const { body, contentType } = buildMultipart({
    reportId: String(reportId),
    queryItems: JSON.stringify(item),
  });

  const res = await request('POST', `${host}/api/bs/edc/report/saveQueryItem`, body, {
    ...headers,
    'Content-Type': contentType,
    'Content-Length': body.length,
  });

  let typeRes = null;
  // ⚠️ 禁止在未点名时调用 updateQueryType！
  // 该接口是**报表级批量覆盖**：会把该报表**所有**条件的 queryType 一起改写。
  // 历史 bug：这里无条件调用，且传入的 `item.showWhere` 已被置空 → 映射为 `'["advance"]'`
  // → 只要保存任意一条条件，整张报表的显示方式都被打回「高级搜索」（把用户已配好的
  //   筛选/高级搜索设置静默改掉，属于擅改展示格式）。
  // 规则：只有**显式传 `--show-where`** 时才对齐报表级 + 批量覆盖；否则只保存本条。
  if (res.json?.code === 200 && args['show-where'] && !args['skip-query-type']) {
    typeRes = await updateQueryType(host, headers, reportId, norm.showWhere);
  } else if (res.json?.code === 200 && !args['show-where']) {
    console.error(
      'NOTE 未传 --show-where → 跳过 updateQueryType（该接口会批量覆盖报表内**所有**条件的显示方式）。' +
        '本条 queryType 已按入参写入。需批量对齐用：edc-report query type --show-where <高级搜索|筛选>'
    );
  }

  // 落库后回读自检：确认 queryType 确实是数组短码（否则设计器不勾选显示方式）
  let echoCheck = null;
  if (res.json?.code === 200 && !args['no-verify-echo']) {
    echoCheck = await verifyEcho(host, headers, reportId, item.id);
  }

  console.log(
    JSON.stringify(
      {
        status: res.status,
        code: res.json?.code,
        msg: res.json?.msg,
        data: res.json?.data,
        showWhere: item.showWhere,
        queryType: item.queryType,
        displayType: item.displayType,
        browserType: item.browserType,
        autoDisplayTypeChanges: autoDisplay.changes,
        warnings: [...norm.warnings, ...autoDisplay.warnings],
        echoCheck,
        updateQueryType:
          typeRes == null
            ? null
            : { code: typeRes.json?.code, msg: typeRes.json?.msg, status: typeRes.status },
      },
      null,
      2
    )
  );
  if (res.json?.code !== 200) {
    console.error('saveQueryItem 失败：勿死循环；提示用户后继续其它步骤（failure-cleanup §二）');
    process.exit(1);
  }
  if (typeRes && typeRes.json?.code !== 200) {
    console.error(
      'saveQueryItem 成功但 updateQueryType 失败：设计器显示方式勾选可能不回显；可重试 edc-report query type'
    );
    process.exit(1);
  }
}

module.exports = {
  resolveShowWhere,
  normalizeShowWhere,
  resolveQueryType,
  resolveQueryTypeArray: resolveQueryType, // 兼容旧引用
  SHOW_WHERE_MAP,
  BROWSER_PRESET,
  BROWSER_STR_PRESET,
  fetchBrowserTypeBean,
  fetchBrowserBeanSearch,
  BROWSER_LABEL,
  resolveQueryDisplayType,
  applyQueryDisplayType,
  fetchFieldMeta,
  updateQueryType,
};

if (require.main === module) {
  main().catch((e) => {
    console.error(e.message || e);
    process.exit(1);
  });
}
