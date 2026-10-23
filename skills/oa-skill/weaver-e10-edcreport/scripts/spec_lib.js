/**
 * spec_lib.js —— 声明式搭表公共库（性能优先）
 *
 * 性能三要点（实测 7.9s → 3.2s，见 session-build-performance-guide.md §六补充）：
 *   1. 单条 HTTPS keep-alive 连接（http(s).Agent keepAlive:true）
 *   2. ETEAMSID 本地缓存（e10-login status ≈0.9s，只解析一次）
 *   3. 省掉可选接口（designKey 预读 / fillDatasetConfig / dataset 轮询 sleep）
 */
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const zlib = require('zlib');
const https = require('https');

const DEFAULT_HOST = process.env.E10_HOST || process.env.EB_HOST || process.env.E10_BASE_URL || '';

/** 全局 keep-alive agent：本进程所有请求复用 */
const AGENT = new https.Agent({ keepAlive: true, maxSockets: 1, rejectUnauthorized: false });

function host() {
  const h = process.env.E10_HOST || process.env.EB_HOST || process.env.E10_BASE_URL || DEFAULT_HOST;
  if (!h) throw new Error('Missing E10 host: set EB_HOST / E10_HOST / E10_BASE_URL env, or pass --host');
  return h.replace(/^https?:\/\//, '');
}

/**
 * ⚠️ 不能把 `host()`（含 `:port`）直接当 `hostname` 传给 https.request ——
 * Node 会把它整串当域名解析 → `getaddrinfo ENOTFOUND host:5001`。
 * 非 443 环境（如 :5001）必须拆成 hostname + port。（pitfalls ENV-1）
 */
function hostParts() {
  const raw = host().replace(/\/.*$/, '');
  const i = raw.lastIndexOf(':');
  if (i > 0) {
    const port = Number(raw.slice(i + 1));
    if (Number.isFinite(port) && port > 0) return { hostname: raw.slice(0, i), port };
  }
  return { hostname: raw, port: 443 };
}

/** ETEAMSID：统一走 eb_auth.js（env 优先 → 最多一次 CLI → 快速失败 + 明确获取指引） */
function eteamsId() {
  return require('./eb_auth.js').eteamsId();
}

function headers(appId, refererSuffix) {
  const sid = eteamsId();
  return {
    Accept: 'application/json, text/plain, */*',
    eteamsid: sid,
    ebBusinessId: appId,
    ebbusinessid: appId,
    Cookie: 'langType=zh_CN; LOGIN_TYPE=pc_account; ETEAMSID=' + sid,
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AgentType=WorkBuddy,IsAgent=true',
    Origin: 'https://' + host(),
    Referer: 'https://' + host() + '/sp/edc/report/designer/' + (refererSuffix || ''),
    timezoneoffset: '-480',
  };
}

function multipart(fields) {
  const b = '----SpecBuild' + Math.random().toString(16).slice(2);
  const parts = [];
  for (const [k, v] of fields) {
    parts.push(
      `--${b}\r\nContent-Disposition: form-data; name="${k}"\r\n\r\n${v == null ? '' : String(v)}\r\n`
    );
  }
  parts.push(`--${b}--\r\n`);
  return { body: Buffer.from(parts.join(''), 'utf8'), ctype: `multipart/form-data; boundary=${b}` };
}

function request(method, p, { appId, form, referer, query }) {
  return new Promise((resolve, reject) => {
    let pathname = p;
    if (query && Object.keys(query).length) {
      pathname += '?' + Object.keys(query).map((k) => `${k}=${encodeURIComponent(query[k])}`).join('&');
    }
    let body;
    const h = headers(appId, referer);
    if (form) {
      const { body: b, ctype } = multipart(form);
      body = b;
      h['Content-Type'] = ctype;
      h['Content-Length'] = b.length;
    }
    const req = https.request(
      { method, ...hostParts(), path: pathname, headers: h, agent: AGENT, rejectUnauthorized: false },
      (res) => {
        let d = '';
        res.setEncoding('utf8');
        res.on('data', (c) => (d += c));
        res.on('end', () => resolve({ status: res.statusCode, raw: d, json: safeJson(d) }));
      }
    );
    req.on('error', reject);
    if (body) req.write(body);
    req.end();
  });
}

function safeJson(s) {
  try {
    // 雪花 ID 防精度丢失
    return JSON.parse(s.replace(/":\s*(\d{16,})/g, '": "$1"'));
  } catch (_) {
    return null;
  }
}

const get = (p, o) => request('GET', p, o || {});
const post = (p, o) => request('POST', p, o || {});

const { findFormInApp, suggestFormsInApp } = require('./find_form_in_app.js');

/**
 * 应用内定源（强制二次确认语义）
 * - exact 唯一 → autoBind
 * - fuzzy / 多命中 / 未命中 → needConfirm，禁止静默绑表
 * - 已给 sourceId 或 --confirmed / formConfirmed → 直接用
 *
 * @returns {Promise<{id,name,match,needConfirm,autoBind,candidates?,message?,appFormCount?}>}
 */
async function resolveFormSourceId(appId, formName, opts = {}) {
  const confirmed =
    opts.confirmedSourceId ||
    opts.sourceId ||
    (opts.formConfirmed && /^\d{15,}$/.test(String(formName)) ? formName : null);

  if (confirmed && /^\d{15,}$/.test(String(confirmed))) {
    return {
      id: String(confirmed),
      name: opts.formName || formName || '',
      match: 'confirmed',
      needConfirm: false,
      autoBind: true,
      message: '使用已确认/指定的 sourceId',
    };
  }

  if (/^\d{15,}$/.test(String(formName))) {
    return {
      id: String(formName),
      name: String(formName),
      match: 'id',
      needConfirm: false,
      autoBind: true,
      message: 'form 为 sourceId',
    };
  }

  const hostUrl = 'https://' + host();
  const name = String(formName || '').trim();

  // 未给表名 → 列表/建议，强制确认
  if (!name || opts.suggestOnly) {
    const kws = opts.keywords || name || '';
    return suggestFormsInApp(hostUrl, appId, kws);
  }

  // 用户已确认模糊表名（formConfirmed + 非 ID）
  if (opts.formConfirmed) {
    const r = await findFormInApp(hostUrl, appId, name);
    if (r.id && (r.match === 'exact' || opts.formConfirmed)) {
      return {
        ...r,
        needConfirm: false,
        autoBind: true,
        message: r.message || '用户已确认表单，继续搭建',
      };
    }
    return r;
  }

  return findFormInApp(hostUrl, appId, name);
}

/** 报表已挂载数据集列表 */
async function listDatasets(reportId, appId) {
  const r = await get('/api/bs/edc/dataset/list', {
    appId,
    referer: reportId,
    query: { hasField: 'true', reportId },
  });
  return (r.json && r.json.data) || [];
}

/**
 * 数据集解析（**同名同源只挂一次**）
 *
 * 关键门禁（2026-09-11 事故：报表演出「重复数据源分组」+ 面板名缺后缀）：
 *  1. 本报表已存在同 sourceId 数据集 → **必须复用**，禁止再次 addDataset（会产生重复挂载）
 *  2. `sourceName` 强制 `{表单名}(业务模块)` / `{表单名}(表单)`（裸表单名 → 回显缺后缀）
 *  3. 发现同 sourceId 多实例（存量脏数据）→ 回传 `duplicates`，由 Agent 提示用户清理
 *
 * @param {object} opt - { reportId, sourceId, appId, datasetId?, sourceType?, sourceGroup?, sourceName? }
 */
async function resolveDataset(opt) {
  const sourceType = opt.sourceType || 'LOGIC';
  const sourceGroup = opt.sourceGroup || 'weaver-ebuilder-form-service';
  const wantName = normalizeDatasetName(opt.sourceName, sourceType);

  // 回传 name/sourceType/tableText → 供 tableName 拼接（勿删，历史回归点）
  const shape = (row) => ({
    id: String(row.id),
    name: row.name || '',
    sourceType: row.type || sourceType,
    sourceGroup: row.sourceGroup || sourceGroup,
    tableText: row.tableText || '',
  });
  const shapeWith = (row, extra) =>
    Object.assign(shape(row), {
      requestedName: wantName,
      nameNormalized: row.name === wantName,
      ...extra,
    });

  // —— 门禁 1：同报表已有同 sourceId → 复用（禁止重复挂载）——
  const existing = await listDatasets(opt.reportId, opt.appId);
  const sameSource = existing.filter((x) => String(x.sourceId) === String(opt.sourceId));
  if (opt.datasetId) {
    const hit = existing.find((x) => String(x.id) === String(opt.datasetId));
    if (hit) return shapeWith(hit, { reused: true, scope: 'same-report', duplicates: sameSource.slice(1).map((x) => String(x.id)) });
    // 跨报表不可复用：忽略外来 datasetId，本表重新解析
    console.warn(
      JSON.stringify({
        warn: 'dataset_not_on_report',
        datasetId: String(opt.datasetId),
        reportId: String(opt.reportId),
        message: '数据集不可跨报表复用，已忽略外来 datasetId，将在本报表解析/新建',
      })
    );
  }
  if (sameSource.length) {
    // 同 sourceId 多条：优先 sourceGroup=weaver-ebuilder-form-service，其次取首条
    const preferred =
      sameSource.find(
        (x) => String(x.sourceGroup) === 'weaver-ebuilder-form-service' && String(x.type).toLowerCase() === 'logic'
      ) ||
      sameSource.find((x) => String(x.sourceGroup) === 'weaver-ebuilder-form-service') ||
      sameSource[0];
    return shapeWith(preferred, {
      reused: true,
      scope: 'same-report',
      duplicates: sameSource.filter((x) => String(x.id) !== String(preferred.id)).map((x) => String(x.id)),
    });
  }

  await post('/api/bs/edc/report/addDataset', {
    appId: opt.appId,
    referer: opt.reportId,
    form: [
      ['reportId', opt.reportId],
      ['sourceType', sourceType],
      ['sourceIds', opt.sourceId],
      ['sourceName', wantName],
      ['appid', opt.appId],
      ['sourceGroup', sourceGroup],
    ],
  });
  for (let i = 0; i < 8; i++) {
    const r = await get('/api/bs/edc/dataset/list', {
      appId: opt.appId,
      referer: opt.reportId,
      query: { hasField: 'true', reportId: opt.reportId },
    });
    const rows = (r.json && r.json.data) || [];
    // 同 sourceId 多条时优先 LOGIC/weaver-ebuilder-form-service（带 field_ 的那条）
    const hits = rows.filter((x) => String(x.sourceId) === String(opt.sourceId));
    const hit =
      hits.find((x) => String(x.sourceGroup) === 'weaver-ebuilder-form-service') || hits[0];
    if (hit) {
      return shapeWith(hit, {
        reused: false,
        scope: 'same-report',
        created: true,
        duplicates: hits.filter((x) => String(x.id) !== String(hit.id)).map((x) => String(x.id)),
      });
    }
  }
  throw new Error('addDataset 后未能在 dataset/list 命中 sourceId=' + opt.sourceId);
}

/** fieldsKey 权威字段清单 */
async function fieldsKeyOf(datasetId, reportId, appId, dsMeta) {
  const r = await get('/api/bs/edc/dataset/fieldsAndOriginFields', {
    appId,
    referer: reportId,
    query: { datasetId, hasField: 'true', isFront: 'true', reportId },
  });
  const fk = (r.json && r.json.data && r.json.data.fieldsKey) || [];
  if (!fk.length) throw new Error('fieldsKey 为空 —— 检查 addDataset 注册契约（field_ 前缀门禁）');
  // 注入数据集显示名/类型：服务端 fieldsKey 的 datasetName/tableText 常为空，
  // 而 tableName 是属性面板回显必需项 → 由 resolveDataset 回传的 dsMeta 兜底。
  const meta = dsMeta || {};
  const label = meta.label || '';
  const st = meta.sourceType || 'logic';
  return fk.map((f) =>
    Object.assign({ datasetLabel: label, datasetSourceType: st }, f, {
      datasetName: f.datasetName || label,
      tableText: f.tableText || label,
      sourceType: f.sourceType || st,
    })
  );
}

/**
 * 平台系统字段（非表单业务字段）。**禁止**作为「精确匹配失败」时的兜底绑定：
 * 它们的中文显示名（标题/数据ID/…）与业务列标题几乎不可能一致，
 * 静默回退会造成「单元格显示名与真实字段名不符」（历史事故：B3 文案「姓名」实绑 `name`→「标题」）。
 */
const SYSTEM_FIELD_NAMES = new Set([
  'name',
  'id',
  'creator',
  'create_time',
  'update_time',
  'updater',
  'data_status',
  'flow_status',
  'current_step',
  'flow_system_number',
  'flow_id',
  'data_read_status',
  'batchmytags',
  'batchpubtags',
  'add_batch_id',
  'update_batch_id',
]);

function isSystemField(f) {
  return SYSTEM_FIELD_NAMES.has(String((f && f.name) || ''));
}

/** 显示名归一化：去空白、全角括号→半角（避免「（年）」全半角导致匹配失败） */
function normText(s) {
  return String(s == null ? '' : s)
    .replace(/\s+/g, '')
    .replace(/（/g, '(')
    .replace(/）/g, ')')
    .trim();
}

/** 字段显示名 / 技术名统一读取 */
function fieldTextOf(f) {
  return String((f && (f.text || f.showName)) || '');
}

/**
 * 字段绑定严格解析（**核心门禁 · 禁止静默兜底**）
 *
 * 匹配顺序（命中即止，**不做模糊自动绑定**）：
 *   1. 显式指定：column.fieldName / column.field 命中 fieldsKey.name，或 spec.fieldMap[列标题]
 *   2. 列标题 === fieldsKey.text/showName（归一化后精确相等）
 *   3. column.field === fieldsKey.text/showName（归一化后精确相等）
 *   4. 都不中 → `unmatched[]`（附模糊候选，仅供**用户挑选**），禁止自动绑定系统字段
 *
 * 显式指定但与 fieldsKey.text 不一致时 → `display_mismatch`，需 `confirmDisplayMismatch`/`--field-confirmed`。
 *
 * @returns {{ok:boolean, bindings:Array, unmatched:Array, fieldCount:number}}
 */
function resolveFieldBindings(fieldsKey, columns, opts = {}) {
  const fk = (fieldsKey || []).filter(Boolean);
  const map = opts.fieldMap || {};
  const confirmedTitles = new Set(
    (opts.fieldConfirmed || opts.confirmedColumns || []).map((x) => normText(x))
  );
  const confirmedAll = !!opts.confirmDisplayMismatch;

  const byText = new Map();
  const byName = new Map();
  for (const f of fk) {
    const t = normText(fieldTextOf(f));
    if (t && !byText.has(t)) byText.set(t, f);
    const n = String(f.name || '');
    if (n && !byName.has(n)) byName.set(n, f);
  }

  const bindings = [];
  const unmatched = [];
  const allTexts = fk.map((f) => ({ name: String(f.name || ''), text: fieldTextOf(f), system: isSystemField(f) }));

  (columns || []).forEach((c, index) => {
    if (!c || c.formula) return; // 公式列无字段绑定
    const title = String(c.title != null ? c.title : c.field || '');
    const nTitle = normText(title);
    const explicit = c.fieldName || map[title] || map[nTitle] || null;
    const confirmMismatch =
      confirmedAll || c.confirmDisplayMismatch === true || confirmedTitles.has(nTitle);

    let hit = null;
    let how = '';
    let requested = '';

    if (explicit) {
      requested = String(explicit);
      hit = byName.get(requested) || byText.get(normText(requested)) || null;
      how = 'explicit';
      if (!hit) {
        unmatched.push({
          index,
          title,
          reason: 'explicit_not_found',
          requested,
          message: `列「${title}」显式指定的字段「${requested}」不在该数据源 fieldsKey 中（禁止臆造）。`,
          candidates: fuzzyCandidates(allTexts, nTitle, 8),
        });
        return;
      }
    } else {
      hit = byText.get(nTitle) || null;
      how = 'title';
      if (!hit && c.field) {
        const nf = normText(c.field);
        hit = byText.get(nf) || byName.get(String(c.field)) || null;
        how = hit ? 'field-text' : '';
      }
      if (!hit) {
        unmatched.push({
          index,
          title,
          reason: 'no_exact_match',
          message:
            `列「${title}」在该数据源 fieldsKey 中**没有精确匹配的显示名**。` +
            '禁止自动兜底到系统字段（标题/数据ID…），请用户从候选或全量字段中指定。',
          candidates: fuzzyCandidates(allTexts, nTitle, 8),
          allFields: allTexts,
        });
        return;
      }
    }

    const realText = fieldTextOf(hit);
    if (normText(realText) !== nTitle && !confirmMismatch) {
      unmatched.push({
        index,
        title,
        reason: 'display_mismatch',
        resolvedName: String(hit.name || ''),
        resolvedText: realText,
        message:
          `列「${title}」将绑定到字段「${realText}」(${hit.name})，与列文案不一致：` +
          `确认请加 spec.fieldConfirmed:["${title}"] 或 --field-confirmed "标题1,标题2"。`,
        candidates: fuzzyCandidates(allTexts, nTitle, 8),
      });
      return;
    }

    bindings.push({ index, title, field: hit, how, displayText: realText, mismatchConfirmed: normText(realText) !== nTitle });
  });

  return { ok: unmatched.length === 0, bindings, unmatched, fieldCount: fk.length };
}

/** 模糊候选（**仅供用户挑选**，绝不自动绑定） */
function fuzzyCandidates(allTexts, nTitle, topN = 8) {
  if (!nTitle) return [];
  const scored = [];
  for (const f of allTexts) {
    const t = normText(f.text);
    const n = normText(f.name);
    let score = 0;
    if (t && t.includes(nTitle)) score = 80;
    else if (nTitle.includes(t) && t.length >= 2) score = 60;
    else if (n.includes(nTitle)) score = 40;
    if (score > 0) scored.push({ name: f.name, text: f.text, system: !!f.system, score });
  }
  if (!scored.length) {
    // 兜底：按「共有汉字」相似度排序（如「党组织」→「所属党委」），仅作为用户挑选依据
    const chars = new Set(nTitle.split(''));
    for (const f of allTexts) {
      if (f.system) continue;
      const t = normText(f.text);
      if (!t) continue;
      let shared = 0;
      for (const ch of new Set(t.split(''))) if (chars.has(ch)) shared++;
      if (shared > 0) scored.push({ name: f.name, text: f.text, system: false, score: shared * 10 });
    }
  }
  return scored.sort((a, b) => b.score - a.score).slice(0, topN);
}

/**
 * 字段列表归一化（**统一两种返回格式 · 以 fieldsAndOriginFields 为准**）
 *
 * 2026-09-11 实测对照（同表单 sourceId 双接口，30/30 逐条比对）：
 *
 * | 接口 | 信封 | 字段元素 |
 * |---|---|---|
 * | `fieldsBySource` | `data` = **裸数组** `[{...}]` | 18 键，与 fieldsKey **完全一致**，唯 `dataSetId="0"`（未落库） |
 * | `fieldsAndOriginFields` | `data` = **对象** `{fieldsKey:[...], originFieldsKey:[...]}` | `dataSetId` = 真实 datasetId |
 *
 * 逐键差异统计：`dataSetId` 30/30 不同，其余 17 键（`name`/`text`/`config`/`originField`/`tableText`/…）**全一致**。
 * ⇒ **一律取「字段元素数组」这一层**，上层信封在 `normalizeFieldList` 里抹平；
 *    `dataSetId` 必须由调用方用**本报表真实 datasetId** 覆盖（`fieldsBySource` 恒为 `0`，直接落库会绑错数据集）。
 *
 * @param {any} payload - 接口原始响应（`{json}` 或 `res.json` 或 `json.data`）
 * @param {{datasetId?:string}} [opts]
 * @returns {{fields:Array, originFields:Array, shape:string, dataSetIdInjected:boolean}}
 */
function normalizeFieldList(payload, opts = {}) {
  let node = payload && payload.json && !payload.data ? payload.json : payload;
  if (node && node.data !== undefined) node = node.data;
  if (node && node.data && (node.data.fieldsKey || node.data.originFieldsKey)) node = node.data;

  let fields = [];
  let originFields = [];
  let shape = 'empty';

  if (Array.isArray(node)) {
    // fieldsBySource：data = 裸数组（每个元素 shape 与 fieldsKey 元素一致）
    fields = node;
    shape = 'bare-array';
  } else if (node && (node.fieldsKey || node.originFieldsKey)) {
    // fieldsAndOriginFields：data = { fieldsKey, originFieldsKey }
    fields = node.fieldsKey || node.originFieldsKey || [];
    originFields = node.originFieldsKey || [];
    shape = 'fieldsKey-object';
  } else if (node && Array.isArray(node.fields)) {
    fields = node.fields;
    shape = 'fields-array';
  }

  const injectDs = opts.datasetId != null && String(opts.datasetId) !== '';
  if (injectDs) {
    fields = fields.map((f) =>
      Object.assign({}, f, {
        dataSetId: String(opts.datasetId),
        // 源级 dataSetId=0 时补全，供 cellType 落库（否则属性面板绑不上数据集）
        rawDataSetId: String((f && f.dataSetId) != null ? f.dataSetId : ''),
      })
    );
  }
  return { fields, originFields, shape, dataSetIdInjected: injectDs };
}

/**
 * 源级字段预检（**建表前**可用，避免为校验而建壳）
 * GET /api/bs/edc/dataset/fieldsBySource
 * 与 addDataset 后 `fieldsAndOriginFields.fieldsKey` **元素同形**（含 field_ 前缀与系统字段），
 * 差异仅：① `data` 为裸数组（无 `{fieldsKey}` 信封）② `dataSetId="0"`。
 * 统一走 `normalizeFieldList` 抹平，调用方拿到的一定是「字段元素数组」。
 */
async function fieldsBySource(sourceId, appId, opts = {}) {
  const r = await get('/api/bs/edc/dataset/fieldsBySource', {
    appId,
    referer: opts.reportId || '',
    query: {
      sourceId,
      sourceType: opts.sourceType || 'logic',
      groupId: opts.sourceGroup || 'weaver-ebuilder-form-service',
    },
  });
  return normalizeFieldList(r, { datasetId: opts.datasetId }).fields;
}

/**
 * 数据集解析确认门禁（**规则 B · 强制**）
 *
 * 触发条件（任一）：
 *   1. 需求**未指明具体表**（formName 为空 / 只给业务关键词）
 *   2. 应用内检索**非完全精准匹配**（模糊命中、多条命中、未命中）
 *
 * 行为：**不建表**，返回 `needConfirm:true` + `candidates`，由用户自行选取指定表。
 * 仅「唯一精确命中」或「已带 --confirmed/sourceId」才放行（`autoBind:true`）。
 *
 * @returns {Promise<{ok:boolean, needConfirm:boolean, candidates:Array, form?:object, exitCode:number, reason:string, message:string}>}
 */
async function resolveFormWithPrompt(appId, formName, opts = {}) {
  const ask = (reason, message, candidates) => ({
    ok: false,
    needConfirm: true,
    candidates: candidates || [],
    exitCode: 3,
    reason,
    message,
  });

  const raw = String(formName == null ? '' : formName).trim();

  // 触发 1：未指明表名 —— 不猜、不建表
  if (!raw && !opts.sourceId && !opts.confirmedSourceId) {
    const sug = await suggestFormsInApp('https://' + host(), appId, opts.keywords || '');
    return ask(
      'form_unspecified',
      '需求未指明具体表：请从候选中**指定表单**后再搭建（禁止按关键词猜表、禁止先建空壳试探）。',
      (sug && (sug.candidates || sug.forms)) || []
    );
  }

  const r = await resolveFormSourceId(appId, raw, opts);

  // 触发 2：非完全精准匹配 —— 交用户指定
  if (r && r.needConfirm && !r.autoBind) {
    const reason = !r.match || r.match === 'none' ? 'form_not_found' : 'form_fuzzy_match';
    const msg =
      reason === 'form_not_found'
        ? `应用内**未找到**与「${raw}」匹配的表：请从候选或全量表单中指定。`
        : `「${raw}」**非完全精准匹配**（match=${r.match}${r.hits ? ' · 命中 ' + r.hits + ' 条' : ''}）：请用户确认要哪张表。`;
    return ask(reason, msg, r.candidates || []);
  }

  return {
    ok: true,
    needConfirm: false,
    candidates: [],
    form: { id: String(r.id), name: r.name || raw, match: r.match },
    exitCode: 0,
    reason: r.match || 'exact',
    message: r.message || '表单已精确命中/已确认',
  };
}

/**
 * 数据集回显名规范化（**强制**）
 * LOGIC（普通应用业务模块）→ `{表单名}(业务模块)`；form（共享表）→ `{表单名}(表单)`
 */
function normalizeDatasetName(formName, sourceType) {
  const base = String(formName || '').trim();
  if (!base) return base;
  const suffix = datasetSuffixOf(sourceType);
  if (/[（(].+[)）]\s*$/.test(base)) return base;
  return base + suffix;
}

function datasetSuffixOf(sourceType) {
  return String(sourceType || 'logic').toLowerCase() === 'form' ? '(表单)' : '(业务模块)';
}

/**
 * 保留旧名（兼容其它脚本）：**已取消模糊兜底**
 * 需要模糊候选请用 resolveFieldBindings().unmatched[].candidates
 */
function matchField(fk, title, opts = {}) {
  const plan = resolveFieldBindings(fk, [{ title, fieldName: opts.fieldName }], opts);
  if (plan.ok && plan.bindings.length) return plan.bindings[0].field;
  const u = plan.unmatched[0] || {};
  const cands = (u.candidates || []).map((c) => `${c.text}(${c.name})`).join('、');
  throw new Error(
    `字段「${title}」未在 fieldsKey 精确命中（reason=${u.reason || 'unknown'}）。` +
      `候选（需用户指定）：${cands || '无'}`
  );
}

function deleteReport(reportId, appId) {
  // 实测：仅 GET 有效，POST 返回 405
  return get('/api/bs/edc/report/deleteReport', { appId, referer: reportId, query: { id: reportId } });
}

function renameReport(reportId, name, appId) {
  return post('/api/bs/edc/report/baseInfo', {
    appId,
    referer: reportId,
    form: [
      ['id', reportId],
      ['name', name],
      ['nameLabelId', '-1'],
      ['groupId', '0'],
      ['showOrder', '1'],
      ['appId', appId],
    ],
  });
}

module.exports = {
  AGENT,
  host,
  eteamsId,
  headers,
  multipart,
  request,
  get,
  post,
  resolveFormSourceId,
  resolveFormWithPrompt,
  resolveDataset,
  listDatasets,
  fieldsKeyOf,
  matchField,
  resolveFieldBindings,
  fuzzyCandidates,
  fieldsBySource,
  normalizeFieldList,
  normalizeDatasetName,
  datasetSuffixOf,
  isSystemField,
  normText,
  fieldTextOf,
  SYSTEM_FIELD_NAMES,
  deleteReport,
  renameReport,
};
