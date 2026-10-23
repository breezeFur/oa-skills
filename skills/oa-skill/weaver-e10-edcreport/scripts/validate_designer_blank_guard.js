#!/usr/bin/env node
/**
 * 设计器空白防护门禁 — references/designer-blank-prevention-guide.md
 *
 * Usage:
 *   node validate_designer_blank_guard.js --report-id <id> [appId]
 *   node validate_designer_blank_guard.js --inline '{"snapshot":{...},"showLocation":0}'
 *
 * Exit 0 = PASS（可有 warnings）；errors → exit 1
 */
'use strict';

const fs = require('fs');

const https = require('https');
const { resolveE10Host } = require('./resolve_e10_host');

let validateGridlinePayload;
try {
  ({ validateGridlinePayload } = require('./validate_gridline.js'));
} catch {
  validateGridlinePayload = null;
}

const MAX_SAFE = Number.MAX_SAFE_INTEGER;

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

/** 雪花 ID：禁止 Number 化；检测是否已被截断 */
function assertSnowflakeId(label, value, expectReportId) {
  const errors = [];
  const warnings = [];
  if (value == null || value === '') {
    errors.push(`${label} 为空`);
    return { errors, warnings };
  }
  if (typeof value === 'number') {
    errors.push(
      `${label} 为 number（${value}）：雪花 ID 禁止 Number()，会截断导致设计区空白。必须 String(...)`
    );
    if (expectReportId && String(value) !== String(expectReportId)) {
      errors.push(
        `${label}=${value} 与 reportId=${expectReportId} 不一致（疑似精度截断）`
      );
    }
    return { errors, warnings };
  }
  const s = String(value);
  if (!/^\d{15,}$/.test(s)) {
    warnings.push(`${label}=${s} 不像雪花 ID`);
  }
  // 若有人先 Number 再 String，会得到截断值
  if (expectReportId && s !== String(expectReportId)) {
    const truncated = String(Number(expectReportId));
    if (s === truncated && truncated !== String(expectReportId)) {
      errors.push(
        `${label}=${s} 等于 Number(reportId) 截断值，与真实 reportId=${expectReportId} 不符 → 会导致设计区空白`
      );
    } else {
      errors.push(`${label}=${s} 与 reportId=${expectReportId} 不一致`);
    }
  }
  if (Number(s) > MAX_SAFE && String(Number(s)) !== s) {
    // value is string of large id — OK; Number would corrupt
    warnings.push(`${label} 超过 MAX_SAFE_INTEGER：写入时务必保持字符串，勿 Number()`);
  }
  return { errors, warnings };
}

function defaultSnapshotName(reportName) {
  const name = String(reportName || '报表').replace(/[\r\n]/g, '').trim() || '报表';
  return `${name}-{date}-{time}`;
}

function validateSnapshotPatch(snapshot, { reportId, reportName } = {}) {
  const errors = [];
  const warnings = [];
  const normalized = {};

  if (!snapshot || typeof snapshot !== 'object') {
    return { ok: true, errors, warnings, normalized: null };
  }

  if (snapshot.enableSnapshot) {
    const idCheck = assertSnowflakeId('snapshot.sheetId', snapshot.sheetId, reportId);
    errors.push(...idCheck.errors);
    warnings.push(...idCheck.warnings);

    if (snapshot.id != null) {
      const c = assertSnowflakeId('snapshot.id', snapshot.id);
      errors.push(...c.errors);
      warnings.push(...c.warnings);
    }
    if (snapshot.jobId != null) {
      const c = assertSnowflakeId('snapshot.jobId', snapshot.jobId);
      errors.push(...c.errors);
      warnings.push(...c.warnings);
    }

    let name = snapshot.snapshotName;
    if (!name || !String(name).trim()) {
      name = defaultSnapshotName(reportName);
      warnings.push(`未指定 snapshotName，已规范为默认：${name}`);
    }
    normalized.snapshotName = name;
    normalized.sheetId = String(reportId || snapshot.sheetId);
    normalized.enableSnapshot = true;
    normalized.cron = snapshot.cron || '';
  }

  return { ok: errors.length === 0, errors, warnings, normalized };
}

function validateShowLocation(loc) {
  const errors = [];
  const warnings = [];
  let n = loc == null || loc === '' ? 2 : Number(loc);
  if (n === 0) {
    errors.push('showLocation=0 禁止（会导致设计区空白/布局异常）；须为 1（居左）或 2（居中）');
    n = 2;
  } else if (n !== 1 && n !== 2) {
    errors.push(`showLocation=${loc} 非法；仅允许 1 或 2`);
    n = 2;
  }
  return { ok: errors.length === 0, errors, warnings, normalized: n };
}

function validateScrollPage(split) {
  const errors = [];
  const warnings = [];
  if (!split || typeof split !== 'object') {
    return { ok: true, errors, warnings, normalized: null };
  }
  const scroll = String(split.scrollPage == null ? '0' : split.scrollPage);
  const content = split.scrollContentField;
  const emptyContent =
    content == null ||
    content === '' ||
    (Array.isArray(content) && content.length === 0);

  if (scroll === '1' && emptyContent) {
    errors.push(
      'scrollPage=1 但 scrollContentField 为空：禁止落库（设计器异常/空白风险）。请补内容字段或设 scrollPage=0'
    );
  }
  return {
    ok: errors.length === 0,
    errors,
    warnings,
    normalized: { scrollPage: scroll, scrollContentField: content },
  };
}

function validatePayload(obj, ctx = {}) {
  const errors = [];
  const warnings = [];
  const normalized = {};

  if (obj.snapshot) {
    const r = validateSnapshotPatch(obj.snapshot, ctx);
    errors.push(...r.errors);
    warnings.push(...r.warnings);
    if (r.normalized) normalized.snapshot = { ...obj.snapshot, ...r.normalized };
  }

  if (obj.showLocation != null || obj.sheetProps) {
    const loc =
      obj.showLocation != null
        ? obj.showLocation
        : obj.sheetProps?.[0]?.showLocation;
    const r = validateShowLocation(loc);
    errors.push(...r.errors);
    warnings.push(...r.warnings);
    normalized.showLocation = r.normalized;
  }

  if (obj.pageSetting || obj.split) {
    const arr = Array.isArray(obj.pageSetting) ? obj.pageSetting : null;
    const split = obj.split || arr?.[0]?.split;
    const r = validateScrollPage(split);
    errors.push(...r.errors);
    warnings.push(...r.warnings);
  }

  // Number(reportId) smell in any stringified payload
  if (ctx.reportId && String(Number(ctx.reportId)) !== String(ctx.reportId)) {
    const bad = String(Number(ctx.reportId));
    const blob = JSON.stringify(obj);
    if (blob.includes(bad) && !blob.includes(`"${ctx.reportId}"`) && blob.includes('sheetId')) {
      warnings.push(
        `payload 中出现截断 ID ${bad}：请确认 sheetId 是否误用 Number(reportId)`
      );
    }
  }

  // 网格线：默认关；禁止畸形（与 validate_gridline 同源）
  if (typeof validateGridlinePayload === 'function') {
    const g = validateGridlinePayload(obj, { strictDefaultOff: Boolean(ctx.strictGridline) });
    errors.push(...g.errors);
    warnings.push(...g.warnings);
    if (g.normalized) normalized.gridline = g.normalized;
  }

  return { ok: errors.length === 0, errors, warnings, normalized };
}

function eteamsId() {
  return require('./eb_auth.js').eteamsId();
}

function request(host, method, urlPath, headers) {
  return new Promise((resolve, reject) => {
    const u = new URL(host + urlPath);
    const r = https.request(
      {
        method,
        hostname: u.hostname, port: u.port || 443, path: u.pathname + u.search,
        headers,
        rejectUnauthorized: false,
      },
      (res) => {
        let d = '';
        res.on('data', (c) => (d += c));
        res.on('end', () => {
          try {
            resolve(JSON.parse(d));
          } catch {
            resolve({ raw: d.slice(0, 300) });
          }
        });
      }
    );
    r.on('error', reject);
    r.end();
  });
}

async function verifyReport(reportId, appId) {
  const host = resolveE10Host();
  const et = eteamsId();
  const headers = {
    eteamsid: et,
    ebBusinessId: appId || '',
    Cookie: `langType=zh_CN; LOGIN_TYPE=pc_account; ETEAMSID=${et}`,
    Accept: 'application/json',
    Referer: `${host}/sp/edc/report/designer/${reportId}`,
    'User-Agent': 'Mozilla/5.0 AgentType=WorkBuddy,IsAgent=true',
  };
  const base = await request(
    host,
    'GET',
    `/api/bs/edc/report/baseInfo?id=${reportId}&useTag=backend`,
    headers
  );
  appId = String(base.data?.appId || appId || '');
  headers.ebBusinessId = appId;
  const info = await request(
    host,
    'GET',
    `/api/bs/edc/report/getReportDevInfo?reportId=${reportId}`,
    headers
  );
  const page = await request(
    host,
    'GET',
    `/api/bs/edc/report/allPageSetting?sheetId=${reportId}`,
    headers
  );

  const data = info.data || {};
  const fields = data.fields || [];
  const errors = [];
  const warnings = [];

  if (fields.length === 0) {
    errors.push('fields.length=0：设计区无单元格（真清空）；优先 rollbackReport');
  }

  const loc = data.sheetProps?.[0]?.showLocation;
  const locR = validateShowLocation(loc);
  errors.push(...locR.errors);
  warnings.push(...locR.warnings);

  const snap = data.snapshot;
  if (snap?.enableSnapshot) {
    // API 可能把 sheetId 以 number 返回（JSON 已截断）；用原始比对风险提示
    if (typeof snap.sheetId === 'number') {
      errors.push(
        `线上 snapshot.sheetId 为 number=${snap.sheetId}（相对 reportId=${reportId}）：疑似曾 Number() 写入，易致设计区空白。请 disable 后按 String(reportId) 重配`
      );
    } else if (String(snap.sheetId) !== String(reportId)) {
      errors.push(`snapshot.sheetId=${snap.sheetId} ≠ reportId=${reportId}`);
    }
    if (!snap.snapshotName) {
      warnings.push(`snapshotName 为空，建议默认 ${defaultSnapshotName(base.data?.name)}`);
    }
  }

  const split = page.data?.[0]?.split;
  const scr = validateScrollPage(split);
  errors.push(...scr.errors);
  warnings.push(...scr.warnings);

  if (typeof validateGridlinePayload === 'function') {
    const g = validateGridlinePayload(
      {
        sheetProps: data.sheetProps || [],
        pageSetting: page.data || [],
        sheets: data.workbookProps?.sheets,
      },
      {}
    );
    errors.push(...g.errors);
    warnings.push(...g.warnings);
  }

  return {
    ok: errors.length === 0,
    errors,
    warnings,
    meta: {
      fields: fields.length,
      showLocation: loc,
      snapshot: snap && {
        enable: snap.enableSnapshot,
        sheetId: snap.sheetId,
        snapshotName: snap.snapshotName,
        cron: snap.cron,
      },
      scrollPage: split?.scrollPage,
      pageRowCount: split?.pageRowCount,
    },
  };
}

function main() {
  const args = parseArgs(process.argv.slice(2));

  if (args.inline || args.file) {
    const obj = args.file
      ? JSON.parse(fs.readFileSync(args.file, 'utf8'))
      : JSON.parse(args.inline);
    const reportId = args['report-id'] || obj.reportId || '';
    const reportName = args.name || obj.reportName || obj.name || '';
    const result = validatePayload(obj, { reportId, reportName });
    console.log(JSON.stringify({ ...result, defaultSnapshotName: defaultSnapshotName(reportName) }, null, 2));
    process.exit(result.ok ? 0 : 1);
  }

  const reportId = args['report-id'] || args._[0];
  const appId = args['app-id'] || args._[1];
  if (!reportId) {
    console.error(
      'Usage: validate_designer_blank_guard.js --report-id <id> | --inline "{...}" | --file patch.json'
    );
    process.exit(2);
  }

  verifyReport(reportId, appId).then((r) => {
    console.log(JSON.stringify(r, null, 2));
    process.exit(r.ok ? 0 : 1);
  });
}

module.exports = {
  defaultSnapshotName,
  validateSnapshotPatch,
  validateShowLocation,
  validateScrollPage,
  validatePayload,
  assertSnowflakeId,
};

if (require.main === module) main();
