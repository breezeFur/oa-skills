#!/usr/bin/env node
/**
 * 报表 base 元数据规范校验（对齐平台默认值 + name/nameLabelId）
 * 见 references/report-baseinfo-defaults-guide.md
 *
 * Usage:
 *   node validate_report_base_meta.js --name "报表名" [--name-label-id -1] [--group-id 0] [--show-order 1]
 *   node validate_report_base_meta.js --report-id <id> [appId]     # 线上巡检
 *   node validate_report_base_meta.js --fix --name "..." ...      # 仅校验并打印规范化结果 JSON
 */
'use strict';


const https = require('https');
const { resolveE10Host } = require('./resolve_e10_host');

const DEFAULTS = {
  groupId: '0',
  showOrder: '1',
  nameLabelId: '-1',
  systemType: '1',
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

function hasControlChars(s) {
  return /[\u0000-\u001F\u007F]/.test(String(s));
}

function validateName(name) {
  const errors = [];
  if (name == null || String(name).length === 0) {
    errors.push('name 不能为空（平台 baseInfo 必填）');
    return { ok: false, errors, normalized: '' };
  }
  const raw = String(name);
  const normalized = raw.trim();
  if (!normalized) errors.push('name trim 后为空');
  if (hasControlChars(raw)) {
    errors.push('name 含控制字符（禁止 \\r\\n\\t 等）；须符合规范，勿额外加特殊符号');
  }
  if (raw !== normalized) {
    errors.push('name 含首尾空白，写入前必须 trim');
  }
  return { ok: errors.length === 0, errors, normalized };
}

function validateNameLabelId(label) {
  const errors = [];
  if (label == null || label === '') {
    errors.push('nameLabelId 禁止空；无多语言时必须显式传 "-1"（平台列表逻辑跳过 i18n）');
    return { ok: false, errors, normalized: DEFAULTS.nameLabelId };
  }
  const raw = String(label);
  if (hasControlChars(raw)) {
    errors.push('nameLabelId 含控制字符（如 "-1\\r\\n" 会导致列表 Long.parseLong 失败 → 报表内部错误）');
  }
  const normalized = raw.trim();
  if (normalized !== raw) errors.push('nameLabelId 含首尾空白');
  if (normalized === '-1') {
    return { ok: errors.length === 0, errors, normalized: '-1' };
  }
  if (!/^\d{6,}$/.test(normalized)) {
    errors.push('nameLabelId 必须是 "-1" 或纯数字多语言 ID，禁止空/脏串');
  }
  return { ok: errors.length === 0, errors, normalized };
}

function validateGroupId(groupId, { remote = false } = {}) {
  const errors = [];
  const warnings = [];
  if (groupId == null || groupId === '') {
    errors.push('groupId 禁止空；未指定分组时新建传平台默认 "0"；已有报表必须用 baseInfo.groupId 原值');
    return { ok: false, errors, warnings, normalized: DEFAULTS.groupId };
  }
  const raw = String(groupId).trim();
  if (!/^-?\d+$/.test(raw)) {
    errors.push('groupId 必须是整数数字字符串');
  }
  // 线上 baseInfo 常见返回 -1（默认分组展示桶）。禁止 Agent「擅自改成别的」；
  // 远程巡检：-1 记 warning，不判 FAIL（避免误伤平台默认）。
  // 本地新建入参：仍建议显式 "0"（Controller defaultValue），不要手写随意 ID。
  if (raw === '-1') {
    if (remote) {
      warnings.push(
        'baseInfo.groupId=-1：多为平台默认分组展示值；保存时原样回传，禁止擅自改成其它分组'
      );
    } else {
      warnings.push(
        '新建入参 groupId=-1 不推荐；未指定分组请用平台默认 "0"。已有报表则以 baseInfo 原值为准、勿乱改'
      );
    }
  }
  return { ok: errors.length === 0, errors, warnings, normalized: raw };
}

function validateShowOrder(showOrder) {
  const errors = [];
  if (showOrder == null || showOrder === '') {
    return { ok: true, errors: [], normalized: DEFAULTS.showOrder, note: '空则按平台默认 1' };
  }
  const raw = String(showOrder).trim();
  if (Number.isNaN(Number(raw))) errors.push('showOrder 必须是数字');
  return { ok: errors.length === 0, errors, normalized: raw };
}

function validateLocal({ name, nameLabelId, groupId, showOrder, remote = false }) {
  const n = validateName(name);
  const l = validateNameLabelId(nameLabelId != null ? nameLabelId : DEFAULTS.nameLabelId);
  const g = validateGroupId(groupId != null ? groupId : DEFAULTS.groupId, { remote });
  const s = validateShowOrder(showOrder);
  const errors = [...n.errors, ...l.errors, ...g.errors, ...s.errors];
  const warnings = [...(g.warnings || [])];
  return {
    ok: errors.length === 0,
    defaults: DEFAULTS,
    errors,
    warnings,
    normalized: {
      name: n.normalized,
      nameLabelId: l.normalized,
      groupId: g.normalized,
      showOrder: s.normalized,
    },
  };
}

function eteamsId() {
  return require('./eb_auth.js').eteamsId();
}

function get(host, path, appId) {
  return new Promise((resolve, reject) => {
    const u = new URL(host + path);
    const sid = eteamsId();
    const h = {
      eteamsid: sid,
      Cookie: `ETEAMSID=${sid}`,
      ebBusinessId: appId || '',
      Accept: 'application/json',
      'User-Agent': 'Mozilla/5.0 AgentType=WorkBuddy,IsAgent=true',
    };
    https
      .get({ hostname: u.hostname, port: u.port || 443, path: u.pathname + u.search, headers: h, rejectUnauthorized: false }, (res) => {
        let d = '';
        res.on('data', (c) => (d += c));
        res.on('end', () => {
          try {
            resolve(JSON.parse(d));
          } catch {
            reject(new Error(d.slice(0, 300)));
          }
        });
      })
      .on('error', reject);
  });
}

async function validateRemote(reportId, appId) {
  const host = resolveE10Host();
  const j = await get(host, `/api/bs/edc/report/baseInfo?id=${reportId}&useTag=backend`, appId);
  if (j.code !== 200 || !j.data) {
    return {
      ok: false,
      reportId,
      errors: [`baseInfo 失败: ${j.msg || j.code || 'no data'}（元数据损坏时也会导致列表 500）`],
    };
  }
  const d = j.data;
  const local = validateLocal({
    name: d.name,
    nameLabelId: d.nameLabelId != null ? d.nameLabelId : DEFAULTS.nameLabelId,
    groupId: d.groupId != null ? String(d.groupId) : DEFAULTS.groupId,
    showOrder: d.showOrder,
    remote: true,
  });
  return {
    ok: local.ok,
    reportId,
    appId: d.appId,
    remote: {
      name: d.name,
      nameLabelId: d.nameLabelId,
      groupId: d.groupId,
      showOrder: d.showOrder,
      systemType: d.systemType,
    },
    errors: local.errors,
    warnings: local.warnings || [],
    normalized: local.normalized,
    defaults: DEFAULTS,
  };
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help || args.h) {
    console.log(`Usage:
  node validate_report_base_meta.js --name "报表名" [--name-label-id -1] [--group-id 0] [--show-order 1]
  node validate_report_base_meta.js --report-id <id> [appId]
Defaults (from EdcReportDevBaseController): groupId=0 showOrder=1 nameLabelId=-1`);
    process.exit(0);
  }

  let result;
  if (args['report-id'] || args.reportId) {
    const rid = args['report-id'] || args.reportId;
    const appId = args['app-id'] || args.appId || args._[0] || '';
    result = await validateRemote(rid, appId);
  } else if (args.name != null || args._[0]) {
    result = validateLocal({
      name: args.name != null ? args.name : args._[0],
      nameLabelId: args['name-label-id'] != null ? args['name-label-id'] : args.nameLabelId,
      groupId: args['group-id'] != null ? args['group-id'] : args.groupId,
      showOrder: args['show-order'] != null ? args['show-order'] : args.showOrder,
    });
  } else {
    console.error('需要 --name 或 --report-id');
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
  DEFAULTS,
  validateLocal,
  validateName,
  validateNameLabelId,
  validateGroupId,
};
