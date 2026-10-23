/**
 * POST /api/bs/edc/report/saveAsVersion
 *
 * 版本名称默认与设计器一致：{报表名称}-{YYYY-MM-DD}-{HH-mm-ss}
 *
 * Usage:
 *   node save_as_version.js --report-id <id>                    # 存为新版本
 *   node save_as_version.js --report-id <id> --list-only        # 仅列版本，不保存
 *   node save_as_version.js --report-id <id> --version-name "自定义名"
 */

const https = require('https');
const { parseJsonSnowflakeSafe, extractIdFromRaw } = require('./json_snowflake');
const { resolveE10Host } = require('./resolve_e10_host');

const HOST = resolveE10Host();

function parseArgs() {
  const out = { reportId: '', versionName: '', appId: '', listOnly: false };
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--report-id') out.reportId = argv[++i];
    else if (argv[i] === '--version-name') out.versionName = argv[++i];
    else if (argv[i] === '--app-id') out.appId = argv[++i];
    else if (argv[i] === '--list-only') out.listOnly = true;
  }
  return out;
}

/** 与设计器「存为新版本」默认命名一致：报表名-日期-时间 */
function defaultVersionName(reportName) {
  const now = new Date();
  const pad = (n) => String(n).padStart(2, '0');
  const date = `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
  const time = `${pad(now.getHours())}-${pad(now.getMinutes())}-${pad(now.getSeconds())}`;
  return `${reportName}-${date}-${time}`;
}

function eteamsId() {
  return require('./eb_auth.js').eteamsId();
}

function request(method, urlPath, { form, appId, reportId } = {}) {
  return new Promise((resolve, reject) => {
    const headers = {
      accept: 'application/json, text/plain, */*',
      eteamsid: eteamsId(),
      ebBusinessId: appId || '',
      Cookie: `ETEAMSID=${eteamsId()}`,
      'User-Agent': 'Mozilla/5.0 AgentType=WorkBuddy,IsAgent=true',
      origin: HOST,
      referer: `${HOST}/sp/edc/report/designer/${reportId || ''}`,
      langType: 'zh_CN',
    };
    let payload = null;
    if (form) {
      payload = Buffer.from(new URLSearchParams(form).toString(), 'utf8');
      headers['Content-Type'] = 'application/x-www-form-urlencoded;charset=UTF-8';
      headers['Content-Length'] = payload.length;
    }
    const u = new URL(HOST + urlPath);
    const req = https.request(
      { hostname: u.hostname, port: u.port || 443, path: u.pathname + u.search, method, headers, rejectUnauthorized: false },
      (res) => {
        let data = '';
        res.on('data', (c) => (data += c));
        res.on('end', () => resolve({ status: res.statusCode, json: parseJsonSnowflakeSafe(data), raw: data }));
      }
    );
    req.on('error', reject);
    if (payload) req.write(payload);
    req.end();
  });
}

async function main() {
  const args = parseArgs();
  if (!args.reportId) throw new Error('--report-id required');

  const base = await request('GET', `/api/bs/edc/report/baseInfo?id=${args.reportId}&useTag=backend`, {
    reportId: args.reportId,
  });
  const appId = args.appId || String(base.json?.data?.appId || base.json?.data?.appid || '');
  const name = base.json?.data?.name || '';
  if (!appId) throw new Error('appId not found');

  if (args.listOnly) {
    await printVersionList(args, appId, name);
    return;
  }

  const versionName = args.versionName || defaultVersionName(name);

  const save = await request('POST', '/api/bs/edc/report/saveAsVersion', {
    appId,
    reportId: args.reportId,
    form: { sheetId: args.reportId, versionName },
  });

  const newId = extractIdFromRaw(save.raw, ['id', 'reportId']) || save.json?.data?.id;
  console.log(JSON.stringify({
    ok: save.json?.code === 200,
    reportName: name,
    originReportId: args.reportId,
    versionName,
    newVersionReportId: newId,
    api: save.json,
  }, null, 2));

  await printVersionList(args, appId, name);
}

async function printVersionList(args, appId, name) {
  const verList = await request('POST', '/api/bs/edc/report/getVersionWithPage', {
    appId,
    reportId: args.reportId,
    form: {
      pageNo: '1',
      pageSize: '10',
      dateRange: '["",""]',
      sheetId: args.reportId,
      versionName: '',
      creators: '[]',
    },
  });
  const records = verList.json?.data?.records || verList.json?.data?.list || [];
  if (records.length) {
    console.log(`Version history for "${name}" (${args.reportId}):`);
    records.slice(0, 10).forEach((r) => {
      console.log(` - ${r.reportVersion || r.version}  ${r.versionName || ''}  snapshotId=${r.reportId || r.id}`);
    });
  } else {
    console.log('No version records.');
  }
}

main().catch((e) => {
  console.error('ERROR:', e.message);
  process.exit(1);
});
