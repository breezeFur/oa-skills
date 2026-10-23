'use strict';
/**
 * 设计器数据集侧栏操作 — references/dataset-sidebar-ops-guide.md
 *
 * rename | agg-get|agg-save|agg-clear | sort-get|sort-save|sort-clear
 * replace | check-used | delete | preview
 */
const fs = require('fs');
const https = require('https');

const { parseJsonSnowflakeSafe } = require('./json_snowflake');
const { resolveE10Host } = require('./resolve_e10_host');

function parseArgs(argv) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      out[a.slice(2).replace(/-/g, '_')] = argv[++i];
    } else out._.push(a);
  }
  return out;
}

function eteamsId() {
  return require('./eb_auth.js').eteamsId();
}

function hostOf(args) {
  return resolveE10Host({ host: args.host });
}

function request(host, method, urlPath, { appId, reportId, body, form } = {}) {
  return new Promise((resolve, reject) => {
    const sid = eteamsId();
    const headers = {
      accept: 'application/json, text/plain, */*',
      eteamsid: sid,
      Cookie: `ETEAMSID=${sid}`,
      'User-Agent': 'Mozilla/5.0 AgentType=WorkBuddy,IsAgent=true',
      origin: host,
      referer: `${host}/sp/edc/report/designer/${reportId || ''}`,
    };
    if (appId) {
      headers.ebBusinessId = String(appId);
      headers.ebbusinessid = String(appId);
    }
    let payload = null;
    if (body) {
      payload = Buffer.from(JSON.stringify(body), 'utf8');
      headers['Content-Type'] = 'application/json;charset=UTF-8';
      headers['Content-Length'] = payload.length;
    }
    if (form) {
      const boundary = '----DsOps' + Date.now();
      const parts = Object.entries(form).map(
        ([k, v]) => `--${boundary}\r\nContent-Disposition: form-data; name="${k}"\r\n\r\n${v}\r\n`
      );
      parts.push(`--${boundary}--\r\n`);
      payload = Buffer.from(parts.join(''), 'utf8');
      headers['Content-Type'] = `multipart/form-data; boundary=${boundary}`;
      headers['Content-Length'] = payload.length;
    }
    const u = new URL(host + urlPath);
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

function readJson(file) {
  const o = JSON.parse(fs.readFileSync(file, 'utf8'));
  delete o._comment;
  if (Array.isArray(o)) return o;
  if (Array.isArray(o.example)) return o.example;
  return o;
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const cmd = args._[0];
  const host = hostOf(args);
  const appId = args.app_id;
  const reportId = args.report_id;
  const datasetId = args.dataset_id;

  if (!cmd || cmd === 'help') {
    console.log(`Usage:
  dataset_ops.js rename --dataset-id <id> --name "显示名" [--name-label-id -1] [--report-id] [--app-id]
  dataset_ops.js agg-get|agg-clear --dataset-id <id>
  dataset_ops.js agg-save --dataset-id <id> --file aggre.json
  dataset_ops.js sort-get|sort-clear --dataset-id <id>
  dataset_ops.js sort-save --dataset-id <id> --file sort.json
  dataset_ops.js replace --file body.json [--app-id]
  dataset_ops.js check-used --report-id <rid> --dataset-id <did>
  dataset_ops.js delete --report-id <rid> --dataset-id <did> [--force]
  dataset_ops.js preview --dataset-id <id>`);
    process.exit(cmd ? 0 : 1);
  }

  if (cmd === 'rename') {
    if (!datasetId || !args.name) throw new Error('--dataset-id and --name required');
    const q = new URLSearchParams({
      datasetId: String(datasetId),
      name: args.name,
      nameLabelId: args.name_label_id || '-1',
    });
    const r = await request(host, 'GET', `/api/bs/edc/dataset/rename?${q}`, { appId, reportId });
    console.log(JSON.stringify({ ok: true, action: 'rename', datasetId, name: args.name, response: r.json }, null, 2));
    return;
  }

  if (cmd === 'agg-get') {
    if (!datasetId) throw new Error('--dataset-id required');
    const r = await request(host, 'GET', `/api/bs/edc/dataset/aggregationGet?datasetId=${datasetId}`, {
      appId,
      reportId,
    });
    console.log(JSON.stringify({ ok: true, action: 'agg_get', data: r.json?.data ?? r.json }, null, 2));
    return;
  }

  if (cmd === 'agg-save' || cmd === 'agg-clear') {
    if (!datasetId) throw new Error('--dataset-id required');
    const aggreData =
      cmd === 'agg-clear' ? '[]' : JSON.stringify(readJson(args.file || ''));
    if (cmd === 'agg-save' && !args.file) throw new Error('--file required');
    const r = await request(host, 'POST', '/api/bs/edc/dataset/aggregationSave', {
      appId,
      reportId,
      form: { datasetId: String(datasetId), aggreData },
    });
    console.log(JSON.stringify({ ok: true, action: cmd.replace('-', '_'), response: r.json }, null, 2));
    return;
  }

  if (cmd === 'sort-get') {
    if (!datasetId) throw new Error('--dataset-id required');
    const r = await request(host, 'GET', `/api/bs/edc/dataset/sortGet?datasetId=${datasetId}`, {
      appId,
      reportId,
    });
    console.log(JSON.stringify({ ok: true, action: 'sort_get', data: r.json?.data ?? r.json }, null, 2));
    return;
  }

  if (cmd === 'sort-save' || cmd === 'sort-clear') {
    if (!datasetId) throw new Error('--dataset-id required');
    const sortData = cmd === 'sort-clear' ? '[]' : JSON.stringify(readJson(args.file || ''));
    if (cmd === 'sort-save' && !args.file) throw new Error('--file required');
    const r = await request(host, 'POST', '/api/bs/edc/dataset/sortSave', {
      appId,
      reportId,
      form: { datasetId: String(datasetId), sortData },
    });
    console.log(JSON.stringify({ ok: true, action: cmd.replace('-', '_'), response: r.json }, null, 2));
    return;
  }

  if (cmd === 'replace') {
    if (!args.file) throw new Error('--file required');
    const body = readJson(args.file);
    const r = await request(host, 'POST', '/api/bs/edc/dataset/replaceDataset', {
      appId: appId || body.appid || body.appId,
      reportId: reportId || body.reportId,
      body,
    });
    const newId = r.json?.data != null ? String(r.json.data) : null;
    console.log(JSON.stringify({ ok: !!newId, action: 'replace', newDatasetId: newId, response: r.json }, null, 2));
    if (!newId) process.exit(1);
    return;
  }

  if (cmd === 'check-used') {
    if (!reportId || !datasetId) throw new Error('--report-id and --dataset-id required');
    const q = new URLSearchParams({ reportId: String(reportId), datasetId: String(datasetId) });
    const r = await request(host, 'GET', `/api/bs/edc/dataset/checkDataSetUsed?${q}`, { appId, reportId });
    const used = r.json?.data === true || r.json?.data === 'true';
    console.log(JSON.stringify({ ok: true, used, canDelete: !used, response: r.json }, null, 2));
    return;
  }

  if (cmd === 'delete') {
    if (!reportId || !datasetId) throw new Error('--report-id and --dataset-id required');
    if (!process.argv.includes('--force')) {
      const q = new URLSearchParams({ reportId: String(reportId), datasetId: String(datasetId) });
      const chk = await request(host, 'GET', `/api/bs/edc/dataset/checkDataSetUsed?${q}`, { appId, reportId });
      if (chk.json?.data === true || chk.json?.data === 'true') {
        console.log(
          JSON.stringify(
            {
              ok: false,
              action: 'delete_blocked',
              message: '数据集仍被引用，无法移除。先清除画布字段引用，或显式 --force',
              response: chk.json,
            },
            null,
            2
          )
        );
        process.exit(1);
      }
    }
    const r = await request(host, 'POST', '/api/bs/edc/report/delDataset', {
      appId,
      reportId,
      form: { reportId: String(reportId), sourceIds: String(datasetId) },
    });
    console.log(
      JSON.stringify(
        { ok: true, action: 'delete', reportId, datasetId, note: 'sourceIds 参数实为 datasetId', response: r.json },
        null,
        2
      )
    );
    return;
  }

  if (cmd === 'preview') {
    if (!datasetId) throw new Error('--dataset-id required');
    const q = new URLSearchParams({ dataSetId: String(datasetId), isFront: 'true' });
    const r = await request(host, 'GET', `/api/bs/edc/dataset/getPreviewData?${q}`, { appId, reportId });
    console.log(JSON.stringify({ ok: true, action: 'preview', data: r.json?.data ?? r.json }, null, 2));
    return;
  }

  throw new Error(`Unknown command: ${cmd}`);
}

main().catch((e) => {
  console.error(JSON.stringify({ ok: false, error: String(e.message || e) }, null, 2));
  process.exit(1);
});
