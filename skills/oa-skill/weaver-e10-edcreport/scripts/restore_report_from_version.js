/**
 * Restore report layout from version snapshot (fields -> safe saveReportDevInfo).
 * For full DB restore use GET rollbackReport (see safe-partial-save-guide.md §四).
 *
 * Usage:
 *   node restore_report_from_version.js --origin <reportId> --version <versionSnapshotId>
 */
const zlib = require('zlib');

const https = require('https');
const {
  DEFAULT_HOST,
  mergeWorkbookSafe,
  encodeWorkbook,
  assertLayoutNotEmptyBeforeSave,
  verifyLayoutPreserved,
  buildMultipart,
  apiHeaders,
} = require('./safe_report_save');

function parseArgs() {
  const out = { origin: '', version: '', host: '' };
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--origin') out.origin = argv[++i];
    else if (argv[i] === '--version') out.version = argv[++i];
    else if (argv[i] === '--host') out.host = argv[++i];
  }
  if (!out.origin || !out.version) throw new Error('--origin and --version are required');
  if (!out.host) out.host = DEFAULT_HOST();
  return out;
}

function eteamsId() {
  return require('./eb_auth.js').eteamsId();
}

function req(method, url, body, headers) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const r = https.request(
      { method, hostname: u.hostname, port: u.port || 443, path: u.pathname + u.search, headers, rejectUnauthorized: false },
      (res) => {
        let b = '';
        res.on('data', (c) => (b += c));
        res.on('end', () => {
          try {
            resolve({ status: res.statusCode, json: JSON.parse(b) });
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

async function getJson(host, path, et, reportId, appId) {
  const { json } = await req('GET', `${host}${path}`, null, apiHeaders(host, et, reportId, appId));
  return json;
}

async function postMultipart(host, urlPath, form, et, reportId, appId) {
  const { body, contentType } = buildMultipart(form);
  return req('POST', `${host}${urlPath}`, body, {
    ...apiHeaders(host, et, reportId, appId),
    'Content-Type': contentType,
    'Content-Length': body.length,
  });
}

async function main() {
  const { origin, version, host } = parseArgs();
  const et = eteamsId();

  const base = await getJson(host, `/api/bs/edc/report/baseInfo?id=${origin}&useTag=backend`, et, origin, '');
  const appId = String(base.data?.appId || '0');
  const name = base.data?.name || '报表';

  const versionDev = await getJson(host, `/api/bs/edc/report/getReportDevInfo?reportId=${version}`, et, origin, appId);
  if (versionDev.code !== 200) throw new Error(`version getReportDevInfo failed: ${versionDev.msg}`);
  const versionFields = versionDev.data?.fields || [];
  if (!versionFields.length) throw new Error(`version ${version} has no fields — use rollbackReport instead`);

  const originDev = await getJson(host, `/api/bs/edc/report/getReportDevInfo?reportId=${origin}`, et, origin, appId);
  const before = assertLayoutNotEmptyBeforeSave(originDev.data || {}, { allowEmpty: true });

  console.log(`Restoring ${versionFields.length} fields: ${version} -> ${origin} (before: ${before.fields} fields)`);

  const wb = mergeWorkbookSafe({ ...versionDev.data, fields: versionFields });
  const wb64 = encodeWorkbook(wb);

  const dsList = await getJson(host, `/api/bs/edc/dataset/list?hasField=true&reportId=${origin}`, et, origin, appId);
  const datasets = (dsList.data || []).map((d) => ({
    id: String(d.id),
    name: d.originalName || d.name,
    sourceId: String(d.sourceId),
    sourceType: 'LOGIC',
    sourceGroup: d.sourceGroup || 'weaver-ebuilder-form-service',
    sourceName: d.originalName || d.name,
    appid: appId,
  }));

  const r1 = await postMultipart(
    host,
    '/api/bs/edc/report/saveReportWithCacheConfig',
    {
      reportId: origin,
      name,
      workbook: wb64,
      dataset: JSON.stringify(datasets),
      datasetFilter: '[]',
      datasetAgg: '[]',
      datasetOrder: '[]',
      appId,
      groupId: '0',
      pageSetting: JSON.stringify({ 0: { rowHeader: 0, colHeader: 0, gridLine: 0, pagination: false } }),
    },
    et,
    origin,
    appId
  );
  console.log('saveReportWithCacheConfig:', r1.json?.code, r1.json?.msg || r1.json?.data);

  const r2 = await postMultipart(
    host,
    '/api/bs/edc/report/saveReportDevInfo',
    {
      groupId: '0',
      appId,
      reportId: origin,
      name,
      nameLabelId: '-1',
      designKey: originDev.data?.designKey,
      workbook: wb64,
    },
    et,
    origin,
    appId
  );
  console.log('saveReportDevInfo:', r2.json?.code, r2.json?.msg || r2.json?.data);
  if (r2.json?.code !== 200) {
    console.error('Prefer: GET rollbackReport?sheetId=' + version + '&originSheetId=' + origin);
    throw new Error(`save failed: ${r2.json?.msg}`);
  }

  const verify = await getJson(host, `/api/bs/edc/report/getReportDevInfo?reportId=${origin}`, et, origin, appId);
  verifyLayoutPreserved({ fields: Math.max(before.fields, 1) }, verify.data, { minFields: versionFields.length });
  console.log('Verified fields:', verify.data?.fields?.length);
}

main().catch((e) => {
  console.error(e.message || e);
  process.exit(1);
});
