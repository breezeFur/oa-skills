'use strict';
/**
 * 新建报表三模式 — references/report-create-modes-guide.md
 *
 *   node create_report.js models [--host URL]
 *   node create_report.js blank --app-id <id> --name "报表名" [--host URL]
 *   node create_report.js template --app-id <id> --name "报表名" --model-id <模板ID>
 *   node create_report.js quick --app-id <id> --name "报表名" --quickly-file path.json
 *   node create_report.js quick ... --quickly-json "{...}"
 */
const fs = require('fs');
const https = require('https');
const { resolveE10Host } = require('./resolve_e10_host');

function arg(name, fallback) {
  const i = process.argv.indexOf(name);
  if (i < 0) return fallback;
  return process.argv[i + 1];
}

function hasFlag(name) {
  return process.argv.includes(name);
}

function eteamsCreds() {
  const A = require('./eb_auth.js');
  const sid = A.eteamsId(); // 缺凭证时抛 EbAuthError，附带完整获取指引
  return { sid, cookie: A.cookieHeader() };
}

function hostOf() {
  return resolveE10Host({ host: arg('--host') });
}

function request(method, urlStr, { headers, body } = {}) {
  return new Promise((resolve, reject) => {
    const u = new URL(urlStr);
    const opts = {
      method,
      hostname: u.hostname, port: u.port || 443, path: u.pathname + u.search,
      headers: headers || {},
      rejectUnauthorized: false,
    };
    const req = https.request(opts, (res) => {
      let d = '';
      res.on('data', (c) => (d += c));
      res.on('end', () => {
        let json;
        try {
          json = JSON.parse(d);
        } catch {
          json = { raw: d.slice(0, 500) };
        }
        resolve({ status: res.statusCode, json, text: d });
      });
    });
    req.on('error', reject);
    if (body) req.write(body);
    req.end();
  });
}

function multipart(fields) {
  const boundary = '----EdcCreate' + Date.now();
  const parts = [];
  for (const [k, v] of fields) {
    parts.push(
      `--${boundary}\r\nContent-Disposition: form-data; name="${k}"\r\n\r\n${v}\r\n`
    );
  }
  parts.push(`--${boundary}--\r\n`);
  const body = Buffer.from(parts.join(''), 'utf8');
  return { body, contentType: `multipart/form-data; boundary=${boundary}` };
}

function authHeaders(appId, host, reportId) {
  const { sid, cookie } = eteamsCreds();
  const h = {
    accept: 'application/json, text/plain, */*',
    eteamsid: sid,
    Cookie: cookie,
    'User-Agent': 'Mozilla/5.0 AgentType=WorkBuddy,IsAgent=true',
    origin: host,
    referer: reportId
      ? `${host}/sp/edc/report/design/${reportId}?appId=${appId}`
      : `${host}/sp/ebdapp/detail/${appId}/report`,
  };
  if (appId) {
    h.ebBusinessId = String(appId);
    h.ebbusinessid = String(appId);
  }
  return h;
}

function extractReportId(obj) {
  const data = obj && obj.data;
  const raw =
    data == null
      ? ''
      : typeof data === 'object'
        ? String(data.reportId || data.id || '')
        : String(data);
  if (/^\d{6,}$/.test(raw) || /^[0-9a-fA-F]{8}-[0-9a-fA-F\-]{20,}$/.test(raw)) return raw;
  return null;
}

async function getModels(host) {
  const headers = authHeaders(null, host);
  const r = await request('GET', `${host}/api/bs/edc/report/getReportModels`, { headers });
  return r.json;
}

async function createBaseInfo({ host, appId, name, reportModel, quicklyParam }) {
  const fields = [
    ['appId', String(appId)],
    ['id', '0'],
    ['name', name],
    ['nameLabelId', '-1'],
    ['groupId', '0'],
    ['showOrder', '1'],
    ['permission', '[]'],
    ['reportModel', String(reportModel || '0')],
  ];
  if (quicklyParam != null && String(quicklyParam).trim() !== '') {
    fields.push(['quicklyParam', typeof quicklyParam === 'string' ? quicklyParam : JSON.stringify(quicklyParam)]);
  }
  const { body, contentType } = multipart(fields);
  const headers = authHeaders(appId, host);
  headers['Content-Type'] = contentType;
  const r = await request('POST', `${host}/api/bs/edc/report/baseInfo`, { headers, body });
  const rid = extractReportId(r.json);
  return {
    ok: !!rid,
    reportId: rid,
    mode:
      Number(reportModel) > 0 ? 'template' : quicklyParam ? 'quick' : 'blank',
    designerUrl: rid
      ? `${host}/sp/edc/report/design/${rid}?appId=${appId}&type=1&from=management`
      : null,
    response: r.json,
    httpStatus: r.status,
  };
}

async function main() {
  const sub = process.argv[2];
  const host = hostOf();

  if (!sub || sub === '-h' || sub === '--help') {
    console.log(`Usage:
  create_report.js models [--host URL]
  create_report.js blank --app-id <id> --name "报表名"
  create_report.js template --app-id <id> --name "报表名" --model-id <模板ID>
  create_report.js quick --app-id <id> --name "报表名" --quickly-file <json>
  create_report.js quick --app-id <id> --name "报表名" --quickly-json "{...}"`);
    process.exit(sub ? 0 : 1);
  }

  if (sub === 'models') {
    const j = await getModels(host);
    const list = Array.isArray(j?.data) ? j.data : Array.isArray(j) ? j : [];
    console.log(
      JSON.stringify(
        {
          ok: true,
          count: list.length,
          models: list.map((m) => ({
            id: String(m.id ?? m.reportId ?? ''),
            name: m.name || m.reportName || '',
          })),
          rawHint: list.length ? undefined : j,
        },
        null,
        2
      )
    );
    return;
  }

  const appId = arg('--app-id') || arg('--appId');
  const name = arg('--name');
  if (!appId || !name) {
    throw new Error('--app-id and --name required');
  }

  if (sub === 'blank') {
    console.log(JSON.stringify(await createBaseInfo({ host, appId, name, reportModel: '0' }), null, 2));
    return;
  }

  if (sub === 'template') {
    const modelId = arg('--model-id') || arg('--modelId') || arg('--report-model');
    if (!modelId || modelId === '0') throw new Error('--model-id required (template report id >0)');
    console.log(
      JSON.stringify(await createBaseInfo({ host, appId, name, reportModel: modelId }), null, 2)
    );
    return;
  }

  if (sub === 'quick') {
    let quickly;
    const file = arg('--quickly-file') || arg('--file');
    const inline = arg('--quickly-json') || arg('--json');
    if (file) quickly = JSON.parse(fs.readFileSync(file, 'utf8'));
    else if (inline) quickly = JSON.parse(inline);
    else throw new Error('--quickly-file or --quickly-json required');
    delete quickly._comment;
    console.log(
      JSON.stringify(
        await createBaseInfo({ host, appId, name, reportModel: '0', quicklyParam: quickly }),
        null,
        2
      )
    );
    return;
  }

  throw new Error(`Unknown subcommand: ${sub}. Use models|blank|template|quick`);
}

main().catch((e) => {
  console.error(JSON.stringify({ ok: false, error: String(e.message || e) }, null, 2));
  process.exit(1);
});
