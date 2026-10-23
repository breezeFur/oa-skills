#!/usr/bin/env node
/**
 * verify_field_bind.js
 * 强制校验：报表 Field 单元格的 name / fieldKey 末段 ∈ fieldsAndOriginFields.fieldsKey[].name
 *
 * Usage:
 *   node verify_field_bind.js <reportId> [appId] [--strict]
 *
 * 校验：① name/fieldKey 末段 ∈ fieldsKey.name（失败即 FAIL/exit 1）
 *      ② 单元格文案 vs 字段真实显示名（需用户确认，--strict 时 exit 2）
 *      ③ 同 sourceId 重复挂载（左侧重复分组根因）、数据集回显名 vs 源级名
 *
 * Exit 0 = pass；非 0 = 字段匹配失败（禁止交付）或（--strict）存在待确认项
 *
 * 依赖：系统已安装 e10-login；无浏览器自动化依赖。
 */

const https = require('https');
const path = require('path');
const { resolveE10Host } = require('./resolve_e10_host');

const HOST = resolveE10Host();
const REPORT_ID = process.argv[2];
let APP_ID = process.argv[3] || process.env.E10_APP_ID || '';
const STRICT = process.argv.includes('--strict');

if (!REPORT_ID) {
  console.error('Usage: node verify_field_bind.js <reportId> [appId]');
  process.exit(2);
}

function eteamsId() {
  return require('./eb_auth.js').eteamsId();
}

function request(method, urlPath, headers) {
  return new Promise((resolve, reject) => {
    const u = new URL(HOST + urlPath);
    const req = https.request(
      {
        method,
        hostname: u.hostname, port: u.port || 443, path: u.pathname + u.search,
        headers,
        rejectUnauthorized: false,
      },
      (res) => {
        let data = '';
        res.on('data', (c) => (data += c));
        res.on('end', () => {
          try {
            resolve({ status: res.statusCode, json: JSON.parse(data), raw: data });
          } catch (e) {
            reject(new Error(`parse fail ${res.statusCode}: ${data.slice(0, 300)}`));
          }
        });
      }
    );
    req.on('error', reject);
    req.end();
  });
}

function isBareSnowflake(s) {
  return /^\d{15,}$/.test(String(s || ''));
}

/** 显示名归一化（去空白 + 全角括号） */
function norm(s) {
  return String(s == null ? '' : s)
    .replace(/\s+/g, '')
    .replace(/（/g, '(')
    .replace(/）/g, ')')
    .trim();
}

async function main() {
  const et = eteamsId();
  const baseHeaders = {
    eteamsid: et,
    Cookie: `langType=zh_CN; LOGIN_TYPE=pc_account; ETEAMSID=${et}`,
    Accept: 'application/json',
    'User-Agent': 'Mozilla/5.0 AgentType=WorkBuddy,IsAgent=true',
    Referer: `${HOST}/sp/edc/report/designer/${REPORT_ID}`,
  };

  if (!APP_ID) {
    const base = await request(
      'GET',
      `/api/bs/edc/report/baseInfo?id=${REPORT_ID}&useTag=backend`,
      baseHeaders
    );
    APP_ID = String(base.json?.data?.appId || base.json?.data?.appid || '');
  }
  if (!APP_ID) throw new Error('cannot resolve appId; pass as 2nd arg');

  const h = { ...baseHeaders, ebBusinessId: APP_ID, ebbusinessid: APP_ID };

  const dsList = await request(
    'GET',
    `/api/bs/edc/dataset/list?hasField=true&reportId=${REPORT_ID}`,
    h
  );
  const datasets = (dsList.json?.data || []).filter((d) => d && d.id);
  if (!datasets.length) throw new Error('no datasets on report');

  const legalByDs = new Map();
  const textByDs = new Map();
  const metaByDs = new Map();
  const warnings = [];
  const confirmations = [];
  for (const ds of datasets) {
    const dsId = String(ds.id);
    const fr = await request(
      'GET',
      `/api/bs/edc/dataset/fieldsAndOriginFields?datasetId=${dsId}&hasField=true&isFront=true&reportId=${REPORT_ID}`,
      h
    );
    const keys = fr.json?.data?.fieldsKey || [];
    legalByDs.set(dsId, new Set(keys.map((f) => f.name).filter(Boolean)));
    textByDs.set(
      dsId,
      new Map(keys.map((f) => [String(f.name), String(f.text || f.showName || '')]))
    );
    const biz = keys.filter(
      (f) => /^\d{15,}$/.test(String(f.name)) || /^field_\d{15,}$/.test(String(f.name))
    );
    const withPrefix = biz.filter((f) => String(f.name).startsWith('field_')).length;
    const bare = biz.filter((f) => /^\d{15,}$/.test(String(f.name))).length;
    metaByDs.set(dsId, {
      sourceId: String(ds.sourceId || ''),
      sourceGroup: String(ds.sourceGroup || ''),
      type: String(ds.type || ''),
      name: ds.originalName || ds.name || '',
      withPrefix,
      bare,
    });
    console.log(
      `dataset ${dsId} (${ds.originalName || ds.name || ''}) fieldsKey=${keys.length} field_=${withPrefix} bareSnow=${bare} type=${ds.type || ''} group=${ds.sourceGroup || ''}`
    );
    // 同 sourceId：若存在 LOGIC/field_ 实例，而本条多为裸雪花 → 注册错误提示
    // 跳过 systemField（数据更新时间等）—— 其 name 形态不是表单业务字段
    if (String(ds.type) !== 'systemField' && bare > withPrefix && biz.length > 0) {
      warnings.push(
        `dataset ${dsId} (${ds.originalName || ds.name || ''}) fieldsKey 业务字段多为裸雪花（field_=${withPrefix}, bare=${bare}）。` +
          `普通应用应使用 addDataset sourceType=LOGIC + sourceGroup=weaver-ebuilder-form-service；` +
          `见 add-dataset-registration-guide.md。当前 type=${ds.type || '?'} sourceGroup=${ds.sourceGroup || '?'}`
      );
    }
  }

  // 同 sourceId 多实例：提示优先用 field_ 那条
  const bySource = new Map();
  for (const [dsId, m] of metaByDs) {
    if (!m.sourceId) continue;
    if (!bySource.has(m.sourceId)) bySource.set(m.sourceId, []);
    bySource.get(m.sourceId).push({ dsId, ...m });
  }
  for (const [sid, arr] of bySource) {
    if (arr.length < 2) continue;
    const good = arr.filter((a) => a.withPrefix > a.bare);
    const bad = arr.filter((a) => a.bare > a.withPrefix);
    if (good.length && bad.length) {
      warnings.push(
        `sourceId=${sid} 存在多数据集：优先绑定 field_ 实例 [${good.map((g) => g.dsId).join(',')}]，` +
          `避免裸雪花实例 [${bad.map((b) => b.dsId).join(',')}]`
      );
    }
    // 【2026-09-11 事故】同源重复挂载 → 左侧出现重复数据源分组（dataset-sidebar-ops-guide.md §5.3）
    confirmations.push({
      type: 'duplicate_dataset_mount',
      sourceId: sid,
      datasetIds: arr.map((a) => a.dsId),
      names: arr.map((a) => a.name),
      message:
        `同一数据源被重复挂载 ${arr.length} 次（datasetId=${arr.map((a) => a.dsId).join(',')}）→ ` +
        '设计器左侧会出现重复数据源分组。需先清画布上游离单元格引用，再 delDataset 去重。',
      fix: [
        'edc-report dataset check-used --report-id <rid> --dataset-id <重复datasetId>',
        'edc-report dataset delete --report-id <rid> --dataset-id <重复datasetId>',
      ],
    });
  }

  // 数据集回显名 vs 源级名（listWithPageReport）：缺业务模块/物理表标识时提示
  try {
    const lw = await request(
      'GET',
      `/api/bs/edc/dataset/listWithPageReport?hasField=true&reportId=${REPORT_ID}`,
      h
    );
    const srcRows = Array.isArray(lw.json?.data) ? lw.json.data : [];
    const srcNameById = new Map(srcRows.map((r) => [String(r.id), String(r.name || '')]));
    for (const [dsId, m] of metaByDs) {
      const srcName = srcNameById.get(m.sourceId);
      if (!srcName || !m.name) continue;
      const bareSrc = srcName.replace(/[（(][^)）]*[)）]\s*$/, '').trim();
      if (m.name === srcName || m.name === bareSrc) continue;
      confirmations.push({
        type: 'dataset_name_mismatch',
        datasetId: dsId,
        datasetName: m.name,
        sourceName: srcName,
        message:
          `数据集回显名「${m.name}」与源级名「${srcName}」（来源：表单/数据源定义）不一致。` +
          '面板分组名以源级名为准；若用户要求带业务模块后缀，可 rename 对齐。',
        fix: [`edc-report dataset rename --dataset-id ${dsId} --name "${srcName}"`],
      });
    }
  } catch (_) {
    /* 源级名仅为增强提示，失败不阻断 */
  }

  const allLegal = new Set();
  for (const s of legalByDs.values()) for (const n of s) allLegal.add(n);

  const dev = await request('GET', `/api/bs/edc/report/getReportDevInfo?reportId=${REPORT_ID}`, h);
  const fields = (dev.json?.data?.fields || []).filter((f) => f.cellType === 'Field');
  console.log(`Field cells: ${fields.length}`);

  const errors = [];
  if (!fields.length) errors.push('无 Field 单元格');

  for (const f of fields) {
    const name = String(f.name || '');
    const last = String(f.fieldKey || '').split('.')[2] || '';
    const dsId = String(f.dataSetId || '');
    const legal = legalByDs.get(dsId) || allLegal;

    if (!name) errors.push(`x=${f.x} y=${f.y} text=${f.text}: name 为空`);
    else if (!legal.has(name)) {
      // 权威是 fieldsKey[].name：有的表单是 field_雪花，有的是裸雪花；禁止凭记忆加/去前缀
      const hint = isBareSnowflake(name) && legal.has(`field_${name}`)
        ? `（fieldsKey 中存在 field_${name}，勿用裸雪花）`
        : name.startsWith('field_') && legal.has(name.slice(6))
          ? `（fieldsKey 中存在裸雪花 ${name.slice(6)}，勿加 field_ 前缀）`
          : '';
      errors.push(
        `x=${f.x} y=${f.y} text=${f.text}: name=${name} 不在 dataset ${dsId} 的 fieldsKey${hint}`
      );
    }

    // 【2026-09-11 事故】单元格文案 ≠ 绑定字段真实显示名 → 需用户确认（禁止静默改写列语义）
    const realText = (textByDs.get(dsId) || new Map()).get(name);
    if (realText && norm(realText) !== norm(f.text)) {
      confirmations.push({
        type: 'display_mismatch',
        cell: `(${f.x},${f.y})`,
        cellText: f.text,
        field: name,
        realDisplayName: realText,
        datasetId: dsId,
        message:
          `单元格文案「${f.text}」与绑定字段真实显示名「${realText}」(${name}) 不一致：` +
          '若是有意改列名可忽略；否则应改绑字段（禁止用系统字段兜底）。',
      });
    }

    if (!last) errors.push(`x=${f.x} y=${f.y}: fieldKey 缺失 (${f.fieldKey})`);
    else if (last !== name) {
      errors.push(`x=${f.x} y=${f.y}: fieldKey 末段 ${last} !== name ${name}`);
    } else if (!legal.has(last)) {
      errors.push(`x=${f.x} y=${f.y}: fieldKey 末段 ${last} 不在 fieldsKey`);
    }
  }

  if (errors.length) {
    console.error('\nFAIL — 字段匹配失败（禁止交付）:');
    for (const e of errors) console.error(' -', e);
    if (warnings.length) {
      console.error('\n注册/数据集提示:');
      for (const w of warnings) console.error(' -', w);
    }
    if (confirmations.length) {
      console.error('\n需用户确认:');
      for (const c of confirmations) console.error(' -', c.message);
    }
    process.exit(1);
  }
  if (warnings.length) {
    console.log('\nWARN — addDataset / 多实例提示（绑定已 PASS，请核对注册）:');
    for (const w of warnings) console.log(' -', w);
  }
  if (confirmations.length) {
    console.log('\n⚠ 需用户确认（不阻断 PASS；--strict 时返回 2）:');
    for (const c of confirmations) {
      console.log(` - [${c.type}] ${c.message}`);
      for (const f of c.fix || []) console.log(`     fix: ${f}`);
    }
    if (STRICT) {
      console.log('\nSTRICT：存在待确认项 → 返回 2');
      process.exit(2);
    }
  }
  console.log('\nPASS — 全部 Field 的 name/fieldKey 均∈ fieldsKey.name');
}

main().catch((e) => {
  console.error(e.message || e);
  process.exit(1);
});
