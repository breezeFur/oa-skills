/**
 * 应用内找表单 sourceId（强制：仅当前应用，无 sleep / 无浏览器自动化 / 禁 ds/group）
 *
 *   node find_form_in_app.js <appId> <表单名>
 *   node find_form_in_app.js <appId> --list
 *   node find_form_in_app.js <appId> --suggest "资产,信息,台账"
 *
 * 硬规则（未指定准确表名 / 模糊命中）：
 *   只在当前应用 getList 检索 → 输出候选 → needConfirm=true → **禁止**自动 addDataset
 *   仅「用户给出准确表名 + exact 唯一命中」才可 autoBind=true
 *
 * 见 references/app-datasource-lookup-guide.md §2.0
 */
'use strict';

const https = require('https');
const { resolveE10Host } = require('./resolve_e10_host');

function eteamsId() {
  return require('./eb_auth.js').eteamsId();
}

function get(host, path, query, appId) {
  return new Promise((resolve, reject) => {
    const u = new URL(host + path);
    for (const [k, v] of Object.entries(query || {})) u.searchParams.set(k, String(v));
    const sid = eteamsId();
    const h = {
      accept: 'application/json',
      eteamsid: sid,
      ebBusinessId: appId,
      ebbusinessid: appId,
      Cookie: `ETEAMSID=${sid}`,
      'User-Agent': 'Mozilla/5.0 AgentType=WorkBuddy,IsAgent=true',
    };
    https
      .get({ hostname: u.hostname, port: u.port || 443, path: u.pathname + u.search, headers: h, rejectUnauthorized: false }, (res) => {
        let d = '';
        res.on('data', (c) => (d += c));
        res.on('end', () => {
          try {
            resolve(JSON.parse(d));
          } catch (e) {
            reject(new Error(d.slice(0, 300)));
          }
        });
      })
      .on('error', reject);
  });
}

function rowsOf(j) {
  if (Array.isArray(j)) return j;
  if (Array.isArray(j?.data)) return j.data;
  return j?.data?.list || j?.data?.records || [];
}

async function listFormsInApp(host, appId) {
  const j = await get(host, `/api/bs/ebuilder/form/obj/getList/${appId}`, { apid: appId }, appId);
  const rows = rowsOf(j);
  return rows.map((r) => ({
    id: String(r.id),
    name: r.name || '',
    tableName: r.tableName || r.table_name || '',
  }));
}

function scoreForm(form, keywords) {
  const name = String(form.name || '');
  const lower = name.toLowerCase();
  let score = 0;
  const hits = [];
  for (const raw of keywords) {
    const kw = String(raw || '').trim();
    if (!kw) continue;
    if (name === kw) {
      score += 100;
      hits.push(kw);
    } else if (name.includes(kw) || lower.includes(kw.toLowerCase())) {
      score += 40;
      hits.push(kw);
    } else if (kw.includes(name) && name.length >= 2) {
      score += 20;
      hits.push(kw);
    }
  }
  return { ...form, score, hits };
}

/**
 * 未指定准确表名：应用内检索候选，强制二次确认。
 */
async function suggestFormsInApp(host, appId, keywords, { topN = 8 } = {}) {
  const forms = await listFormsInApp(host, appId);
  const kws = (Array.isArray(keywords) ? keywords : String(keywords || '').split(/[,，\s]+/)).filter(
    Boolean
  );
  let ranked;
  if (!kws.length) {
    ranked = forms.map((f) => ({ ...f, score: 0, hits: [] }));
  } else {
    ranked = forms
      .map((f) => scoreForm(f, kws))
      .filter((f) => f.score > 0)
      .sort((a, b) => b.score - a.score || a.name.localeCompare(b.name, 'zh'));
    if (!ranked.length) {
      ranked = forms.map((f) => ({ ...f, score: 0, hits: [] })).slice(0, topN);
    }
  }
  const candidates = ranked.slice(0, topN);
  return {
    ok: true,
    appId: String(appId),
    scope: 'app',
    api: 'form/obj/getList',
    appFormCount: forms.length,
    keywords: kws,
    needConfirm: true,
    autoBind: false,
    message:
      '用户未指定准确表名或仅为模糊匹配：已在当前应用检索。请向用户展示候选并二次确认后再 addDataset。禁止静默绑定。',
    confirmPrompt:
      '请确认要用哪张表（回复表名或 sourceId）。候选见 candidates；若都不是请给出准确表名。',
    candidates,
    id: null,
    name: null,
    match: kws.length ? 'suggest' : 'list',
  };
}

async function findFormInApp(host, appId, formName) {
  if (!appId) throw new Error('appId required — 禁止无应用上下文去扫全系统 /ds/group');
  const forms = await listFormsInApp(host, appId);
  const rows = forms;

  if (!formName || !String(formName).trim()) {
    return suggestFormsInApp(host, appId, []);
  }

  const exactHits = rows.filter((r) => r.name === formName);
  if (exactHits.length === 1) {
    return {
      id: String(exactHits[0].id),
      name: exactHits[0].name,
      match: 'exact',
      scope: 'app',
      api: 'form/obj/getList',
      appFormCount: rows.length,
      needConfirm: false,
      autoBind: true,
      message: '准确表名唯一命中，可绑定（仍建议口头确认一次）。',
    };
  }
  if (exactHits.length > 1) {
    return {
      id: null,
      name: null,
      match: 'exact-ambiguous',
      scope: 'app',
      api: 'form/obj/getList',
      appFormCount: rows.length,
      needConfirm: true,
      autoBind: false,
      message: '同名多条，必须二次确认。',
      confirmPrompt: '应用内存在多张同名表，请选择 sourceId。',
      candidates: exactHits.map((r) => ({ id: r.id, name: r.name, score: 100, hits: [formName] })),
    };
  }

  const fuzzy = rows.filter(
    (r) => String(r.name || '').includes(formName) || formName.includes(String(r.name || ''))
  );
  if (fuzzy.length === 1) {
    return {
      id: String(fuzzy[0].id),
      name: fuzzy[0].name,
      match: 'fuzzy',
      scope: 'app',
      api: 'form/obj/getList',
      appFormCount: rows.length,
      needConfirm: true,
      autoBind: false,
      message: '模糊命中 1 条：必须向用户二次确认后再绑定，禁止静默 addDataset。',
      confirmPrompt: `是否使用表「${fuzzy[0].name}」(sourceId=${fuzzy[0].id})？`,
      candidates: [{ id: fuzzy[0].id, name: fuzzy[0].name, score: 40, hits: [formName] }],
    };
  }
  if (fuzzy.length > 1) {
    return {
      id: null,
      name: null,
      match: 'fuzzy-multi',
      scope: 'app',
      api: 'form/obj/getList',
      appFormCount: rows.length,
      needConfirm: true,
      autoBind: false,
      message: '模糊命中多条：展示候选，等用户确认。',
      confirmPrompt: '请选择要用的表（表名或 sourceId）。',
      candidates: fuzzy.slice(0, 10).map((r) => ({
        id: r.id,
        name: r.name,
        score: 40,
        hits: [formName],
      })),
    };
  }

  return {
    id: null,
    name: null,
    match: null,
    scope: 'app',
    api: 'form/obj/getList',
    appFormCount: rows.length,
    needConfirm: true,
    autoBind: false,
    message: '应用内未命中。禁止立刻 /ds/group；请问用户准确表名/sourceId，或 --suggest 关键词。',
    hint: '应用内未命中。禁止立刻 /ds/group；可带关键字问用户或有限次应用内 listByPage',
    candidates: [],
  };
}

async function waitDatasetBySource(getListFn, sourceId, { tries = 8, gapMs = 100 } = {}) {
  for (let i = 0; i < tries; i++) {
    const list = await getListFn();
    const hit = (list || []).find((d) => String(d.sourceId) === String(sourceId));
    if (hit) return hit;
    await new Promise((r) => setTimeout(r, gapMs));
  }
  throw new Error(`dataset not ready for sourceId=${sourceId}`);
}

module.exports = {
  findFormInApp,
  suggestFormsInApp,
  listFormsInApp,
  waitDatasetBySource,
  eteamsId,
};

if (require.main === module) {
  const argv = process.argv.slice(2);
  const host = resolveE10Host();
  const appId = argv[0];
  const flag = argv[1];
  const t0 = Date.now();

  function done(r, exitIfNoId = false) {
    console.log(JSON.stringify({ ...r, ms: Date.now() - t0 }, null, 2));
    if (exitIfNoId && (!r || !r.id)) process.exit(2);
    if (r && r.needConfirm && !r.autoBind) process.exit(3); // 3 = 须二次确认
  }

  if (!appId) {
    console.error('Usage:');
    console.error('  node find_form_in_app.js <appId> <表单名>');
    console.error('  node find_form_in_app.js <appId> --list');
    console.error('  node find_form_in_app.js <appId> --suggest "关键词1,关键词2"');
    console.error('强制：仅查当前应用；未指定准确表名 / 模糊命中 → needConfirm，禁止静默绑定');
    process.exit(1);
  }

  if (flag === '--list' || flag === 'list') {
    suggestFormsInApp(host, appId, [])
      .then((r) => done(r))
      .catch((e) => {
        console.error(e.message || e);
        process.exit(1);
      });
  } else if (flag === '--suggest' || flag === 'suggest') {
    const kws = argv.slice(2).join(' ') || '';
    suggestFormsInApp(host, appId, kws)
      .then((r) => done(r))
      .catch((e) => {
        console.error(e.message || e);
        process.exit(1);
      });
  } else {
    const name = argv.slice(1).join(' ');
    if (!name) {
      suggestFormsInApp(host, appId, [])
        .then((r) => done(r))
        .catch((e) => {
          console.error(e.message || e);
          process.exit(1);
        });
      return;
    }
    findFormInApp(host, appId, name)
      .then((r) => done(r, r.autoBind === true))
      .catch((e) => {
        console.error(e.message || e);
        process.exit(1);
      });
  }
}
