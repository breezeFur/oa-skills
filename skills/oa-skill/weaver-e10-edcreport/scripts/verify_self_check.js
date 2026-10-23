#!/usr/bin/env node
/**
 * 落库自检（父格 / 超链接 Const / Field 数 / 可选绑定·条件格式·元数据）
 * 对应 report-self-check-guide.md · condition-format-guide.md · report-internal-error-guide.md
 *
 * Usage:
 *   node verify_self_check.js <reportId> [appId]
 *   node verify_self_check.js <reportId> [appId] --with-bind
 *   node verify_self_check.js <reportId> [appId] --with-condition
 *   node verify_self_check.js <reportId> [appId] --with-meta
 *   node verify_self_check.js <reportId> [appId] --with-bind --with-condition --with-meta [--with-blank]
 *
 * Exit 0 = PASS；非 0 = FAIL
 */
'use strict';

const { spawnSync } = require('child_process');
const fs = require('fs');
const https = require('https');
const path = require('path');
const { resolveE10Host } = require('./resolve_e10_host');

const HOST = resolveE10Host();
const REPORT_ID = process.argv[2];
const APP_ID_ARG = process.argv[3] && !process.argv[3].startsWith('--') ? process.argv[3] : '';
const WITH_BIND = process.argv.includes('--with-bind');
const WITH_CONDITION = process.argv.includes('--with-condition');
const WITH_META = process.argv.includes('--with-meta');
const WITH_BLANK = process.argv.includes('--with-blank');

if (!REPORT_ID) {
  console.error(
    'Usage: node verify_self_check.js <reportId> [appId] [--with-bind] [--with-condition] [--with-meta] [--with-blank]'
  );
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
            resolve({ status: res.statusCode, json: JSON.parse(data) });
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

function parseMaybe(v, fb) {
  if (v == null || v === '') return fb;
  if (typeof v === 'object') return v;
  try {
    return JSON.parse(v);
  } catch {
    return fb;
  }
}

function checkFields(fields) {
  const errors = [];
  const warnings = [];
  let fieldCount = 0;
  let constCount = 0;

  for (const f of fields || []) {
    const ct = f.cellType || '';
    const x = f.x;
    const y = f.y;
    const href = f.pcHreflink || f.h5Hreflink || '';
    const style = parseMaybe(f.style, {});
    const cellType = style.cellType || style.analysisFieldCellType || {};
    const leftX = f.leftX != null ? f.leftX : cellType.leftX;
    const leftY = f.leftY != null ? f.leftY : cellType.leftY;
    const topX = f.topX != null ? f.topX : cellType.topX;
    const topY = f.topY != null ? f.topY : cellType.topY;
    const cellText = f.cellText || cellType.cellText || '';
    const pcHref = href || cellType.pcHreflink || cellType.h5Hreflink || '';

    if (ct === 'Field') {
      fieldCount++;
      continue;
    }
    if (ct !== 'Const') continue;
    constCount++;

    const origin = leftX === 0 && leftY === 0 && topX === 0 && topY === 0;
    if (origin && !pcHref) {
      errors.push(`Const(${x},${y}) 父格(0,0)=伪自定义A1，应为-1,-1`);
    }
    if (!pcHref) continue;

    if (topX !== -1 || topY !== -1) {
      errors.push(`链接格(${x},${y}) 不需要上父格，top 应为 -1,-1（实际 ${topX},${topY}）`);
    }
    if (!cellText && !cellType.cellText) {
      errors.push(`链接格(${x},${y}) cellText 为空，超链接文案可能被冲掉`);
    }
    const workbookHref = cellType.pcHreflink || cellType.h5Hreflink || '';
    if (!workbookHref && !href) {
      errors.push(`链接格(${x},${y}) 缺 pcHreflink（须进 ConstCellType）`);
    }
    const link = workbookHref || href;
    if (/\{[LC]\d+\}/.test(link)) {
      if (leftX === -1 && leftY === -1) {
        errors.push(`链接格(${x},${y}) 含占位符但左父格为默认，应指向依赖数据格`);
      }
      if (leftX === 0 && leftY === 0) {
        errors.push(`链接格(${x},${y}) 左父格不能为(0,0)`);
      }
    }
  }

  return { errors, warnings, fieldCount, constCount };
}

// 仅用于调用同目录下白名单内的校验脚本；args 只允许 --report-id / --app-id 等业务 ID，禁止传递凭证
const ALLOWED_ARGS = /^(--report-id|--app-id|--type|--matrix-id|--file|--fix|--json|--apply|--dump|--spec|--host|--output|--restore-from|--show-where|--show-order|--set|--from|--prefix|--delete-id)$/;
const FORBIDDEN_VALUE = /(ETEAMSID|eteamsid|cookie|password|secret|token|private)/i;

function runSibling(scriptName, args) {
  const file = path.join(__dirname, scriptName);
  if (!fs.existsSync(file)) {
    throw new Error(`Script not found: ${file}`);
  }
  for (let i = 0; i < args.length; i += 1) {
    const a = String(args[i]);
    if (a.startsWith('--')) {
      if (!ALLOWED_ARGS.test(a)) throw new Error(`Disallowed argument: ${a}`);
      continue;
    }
    if (FORBIDDEN_VALUE.test(a)) throw new Error(`Argument looks like credential: ${a}`);
  }
  const r = spawnSync(process.execPath, [file, ...args], { stdio: 'inherit' });
  return r.status == null ? 1 : r.status;
}

async function main() {
  const et = eteamsId();
  let appId = APP_ID_ARG || process.env.E10_APP_ID || '';
  const baseHeaders = {
    eteamsid: et,
    Cookie: `langType=zh_CN; LOGIN_TYPE=pc_account; ETEAMSID=${et}`,
    Accept: 'application/json',
    'User-Agent': 'Mozilla/5.0 AgentType=WorkBuddy,IsAgent=true',
    Referer: `${HOST}/sp/edc/report/designer/${REPORT_ID}`,
  };
  if (appId) {
    baseHeaders.ebBusinessId = appId;
    baseHeaders.ebbusinessid = appId;
  }

  if (!appId) {
    const base = await request(
      'GET',
      `/api/bs/edc/report/baseInfo?id=${REPORT_ID}&useTag=backend`,
      baseHeaders
    );
    appId = String(base.json?.data?.appId || base.json?.data?.ebBusinessId || '');
  }

  const dev = await request(
    'GET',
    `/api/bs/edc/report/getReportDevInfo?reportId=${REPORT_ID}`,
    { ...baseHeaders, ebBusinessId: appId, ebbusinessid: appId }
  );
  if (dev.json?.code !== 200) {
    console.error('getReportDevInfo failed:', dev.json?.msg || dev.status);
    process.exit(1);
  }

  const fields = dev.json.data?.fields || [];
  const { errors, warnings, fieldCount, constCount } = checkFields(fields);

  const result = {
    ok: errors.length === 0,
    reportId: REPORT_ID,
    appId,
    fieldCount,
    constCount,
    errors,
    warnings,
  };
  console.log(JSON.stringify(result, null, 2));

  let exitCode = errors.length ? 1 : 0;

  if (WITH_META) {
    const st = runSibling('validate_report_base_meta.js', [
      '--report-id',
      REPORT_ID,
      ...(appId ? ['--app-id', appId] : []),
    ]);
    if (st !== 0) exitCode = st;
  }

  if (WITH_CONDITION) {
    const st = runSibling('validate_condition_format.js', [
      '--report-id',
      REPORT_ID,
      ...(appId ? ['--app-id', appId] : []),
    ]);
    if (st !== 0) exitCode = st;
  }

  if (WITH_BIND) {
    const st = runSibling('verify_field_bind.js', [REPORT_ID, appId].filter(Boolean));
    if (st !== 0) exitCode = st;
  }

  if (WITH_BLANK) {
    const st = runSibling('validate_designer_blank_guard.js', [
      '--report-id',
      REPORT_ID,
      ...(appId ? ['--app-id', appId] : []),
    ]);
    if (st !== 0) exitCode = st;
  }

  process.exit(exitCode);
}

main().catch((e) => {
  console.error(e.message || e);
  process.exit(1);
});
