/**
 * 多表关联键推断（需求未写明时）→ 输出候选 + needConfirm
 * Usage:
 *   node suggest_join_fields.js --app-id <appId> --parent-source <id> --child-source <id>
 *   node suggest_join_fields.js --app-id <appId> --parent-form "销售单" --child-form "明细"
 */
'use strict';


const https = require('https');
const { findFormInApp } = require('./find_form_in_app');
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

function parseArgs(argv) {
  const o = {};
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
    }
  }
  return o;
}

function normLabel(s) {
  return String(s || '')
    .trim()
    .toLowerCase()
    .replace(/[\s_\-]/g, '')
    .replace(/(编号|名称|姓名|id|ids|代码|编码)$/i, '');
}

function pickFields(payload) {
  const raw =
    payload?.data?.fields ||
    payload?.data?.fieldsKey ||
    payload?.data?.originFields ||
    payload?.fields ||
    [];
  const list = Array.isArray(raw) ? raw : [];
  return list
    .map((f) => ({
      name: String(f.name || f.fieldName || f.id || ''),
      text: String(f.text || f.title || f.showName || f.label || f.name || ''),
      type: String(f.type || f.compType || f.fieldType || ''),
    }))
    .filter((f) => f.name);
}

function scorePair(a, b) {
  const reasons = [];
  let score = 0;
  if (a.text && b.text && a.text === b.text) {
    score += 100;
    reasons.push('显示名全等');
  }
  if (a.name && b.name && a.name === b.name) {
    score += 90;
    reasons.push('系统名全等');
  }
  const na = normLabel(a.text || a.name);
  const nb = normLabel(b.text || b.name);
  if (na && nb && na === nb) {
    score += 70;
    reasons.push('去后缀名相同');
  }
  const idLike = /id$/i.test(a.name) || /id$/i.test(a.text) || /编号|主键/.test(a.text);
  const fkLike = /id$/i.test(b.name) || /编号|外键|关联/.test(b.text);
  if (idLike && fkLike && na && nb && (na.includes(nb) || nb.includes(na))) {
    score += 50;
    reasons.push('主键/外键命名近似');
  }
  if (a.text && b.text && (a.text.includes(b.text) || b.text.includes(a.text)) && a.text !== b.text) {
    score += 35;
    reasons.push('显示名包含');
  }
  return { score, reasons };
}

function suggestJoins(parentFields, childFields, { top = 5 } = {}) {
  const scored = [];
  for (const p of parentFields) {
    for (const c of childFields) {
      const { score, reasons } = scorePair(p, c);
      if (score < 35) continue;
      scored.push({
        parent: { name: p.name, text: p.text },
        child: { name: c.name, text: c.text },
        score,
        reasons,
      });
    }
  }
  scored.sort((x, y) => y.score - x.score);
  const out = [];
  const seen = new Set();
  for (const s of scored) {
    const k = `${s.parent.name}|${s.child.name}`;
    if (seen.has(k)) continue;
    seen.add(k);
    out.push(s);
    if (out.length >= top) break;
  }
  return out;
}

async function loadFormFields(host, appId, sourceId) {
  // 优先 eb form 字段；失败再试 ds 元数据（无 report 时）
  try {
    const j = await get(host, `/api/bs/ebuilder/form/obj/getForm/${sourceId}`, { apid: appId }, appId);
    const fields = pickFields(j);
    if (fields.length) return { fields, via: 'getForm' };
  } catch (_) {
    /* fallthrough */
  }
  try {
    const j = await get(
      host,
      `/api/bs/edc/report/ds/fieldsAndOriginFields`,
      { sourceId, isFront: true },
      appId
    );
    const fields = pickFields(j);
    if (fields.length) return { fields, via: 'fieldsAndOriginFields' };
  } catch (_) {
    /* fallthrough */
  }
  throw new Error(`无法读取字段: sourceId=${sourceId}`);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const appId = args['app-id'] || args.appId;
  const host = resolveE10Host({ host: args.host });
  if (!appId) {
    console.error(
      'Usage: node suggest_join_fields.js --app-id <id> (--parent-source <id> --child-source <id> | --parent-form <名> --child-form <名>)'
    );
    process.exit(1);
  }

  let parentSource = args['parent-source'] || args.parentSource;
  let childSource = args['child-source'] || args.childSource;
  let parentForm = args['parent-form'] || args.parentForm;
  let childForm = args['child-form'] || args.childForm;

  if ((!parentSource || !childSource) && parentForm && childForm) {
    const p = await findFormInApp(host, appId, parentForm);
    const c = await findFormInApp(host, appId, childForm);
    if (!p || !c) {
      console.log(
        JSON.stringify(
          {
            ok: false,
            needConfirm: true,
            error: 'form_not_found',
            parent: p,
            child: c,
            hint: '请确认表名或直接传 --parent-source / --child-source',
          },
          null,
          2
        )
      );
      process.exit(2);
    }
    parentSource = p.id;
    childSource = c.id;
    parentForm = p.name;
    childForm = c.name;
  }

  if (!parentSource || !childSource) {
    console.error('需要 --parent-source/--child-source 或 --parent-form/--child-form');
    process.exit(1);
  }

  const parentMeta = await loadFormFields(host, appId, parentSource);
  const childMeta = await loadFormFields(host, appId, childSource);
  const candidates = suggestJoins(parentMeta.fields, childMeta.fields);
  const best = candidates[0] || null;
  const ambiguous = candidates.length >= 2 && candidates[1].score >= (best?.score || 0) - 10;

  const result = {
    ok: true,
    needConfirm: true,
    reason: '需求未写明关联时，推断结果必须经用户确认',
    parent: { sourceId: String(parentSource), formName: parentForm || null, fieldVia: parentMeta.via },
    child: { sourceId: String(childSource), formName: childForm || null, fieldVia: childMeta.via },
    best,
    ambiguous,
    candidates,
    userPrompt: best
      ? `【关联待确认】表「${parentForm || parentSource}」与「${childForm || childSource}」未在需求中写明关联字段。已按字段匹配推断：父.${best.parent.text || best.parent.name} Equals 子.${best.child.text || best.child.name}。请确认是否正确；若不正确请给出正确关联。`
      : `【关联待确认】未能自动匹配「${parentForm || parentSource}」与「${childForm || childSource}」的关联字段，请提供 A.字段 = B.字段。`,
  };

  console.log(JSON.stringify(result, null, 2));
  if (!best) process.exit(3);
}

if (require.main === module) {
  main().catch((e) => {
    console.error(e.message || e);
    process.exit(1);
  });
}

module.exports = { suggestJoins, scorePair, pickFields };
