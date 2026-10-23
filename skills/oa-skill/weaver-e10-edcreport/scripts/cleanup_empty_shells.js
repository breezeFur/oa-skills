#!/usr/bin/env node
/**
 * 失败/中止清理空壳报表 — failure-cleanup-and-nonblocking-guide.md §一
 *
 * Usage:
 *   node cleanup_empty_shells.js --app-id <appId> --report-id <id>[,id2]
 *   node cleanup_empty_shells.js --app-id <appId> --ids-file <ids.txt>
 *   node cleanup_empty_shells.js --app-id <appId> --prefix __build_   # 按名前缀删（慎用）
 */
'use strict';


const fs = require('fs');
const https = require('https');
const { resolveE10Host } = require('./resolve_e10_host');

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

function eteamsId() {
  return require('./eb_auth.js').eteamsId();
}

function request(method, urlPath, headers, host) {
  return new Promise((resolve, reject) => {
    const u = new URL(host + urlPath);
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
          } catch {
            resolve({ status: res.statusCode, raw: data });
          }
        });
      }
    );
    req.on('error', reject);
    req.end();
  });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const appId = args['app-id'] || args.appId;
  const host = resolveE10Host({ host: args.host });
  if (!appId) {
    console.error(
      'Usage: node cleanup_empty_shells.js --app-id <appId> (--report-id <id[,id2]> | --ids-file <f> | --prefix __build_)'
    );
    process.exit(2);
  }

  const et = eteamsId();
  const headers = {
    eteamsid: et,
    ebBusinessId: appId,
    ebbusinessid: appId,
    Cookie: `langType=zh_CN; LOGIN_TYPE=pc_account; ETEAMSID=${et}`,
    Accept: 'application/json',
    'User-Agent': 'Mozilla/5.0 AgentType=WorkBuddy,IsAgent=true',
  };

  const isAudit = Boolean(args.list || args['dry-run']);

  // ── 只读自查（--list / --dry-run）：只统计，不删任何东西 ──
  if (isAudit && !(args['report-id'] || args.reportId || args['ids-file'])) {
    const list = await request(
      'GET',
      `/api/bs/edc/report/list?appId=${appId}&appid=${appId}&groupid=-1&objId=-1&pageNo=1&pageSize=300`,
      headers,
      host
    );
    const rows = list.json?.data?.list || list.json?.data?.records || list.json?.data || [];
    const prefix = args.prefix ? String(args.prefix) : null;
    const out = [];
    for (const r of Array.isArray(rows) ? rows : []) {
      const id = String(r.id);
      const name = String(r.name || '');
      if (prefix && !name.startsWith(prefix)) continue;
      let fields = -1;
      try {
        const d = await request(
          'GET',
          `/api/bs/edc/report/getReportDevInfo?reportId=${id}`,
          headers,
          host
        );
        fields = ((d.json && d.json.data && d.json.data.fields) || []).length;
      } catch (e) {
        fields = 'ERR';
      }
      out.push({ reportId: id, name, fields, empty: fields === 0 });
    }
    const empties = out.filter((x) => x.empty);
    console.log(
      JSON.stringify(
        {
          audit: true,
          appId,
          prefix,
          total: out.length,
          emptyShells: empties,
          verdict: empties.length === 0 ? '✅ 无空壳报表' : `⚠️ 存在 ${empties.length} 个空壳，需清理`,
        },
        null,
        2
      )
    );
    process.exit(0);
  }

  let ids = [];
  if (args['report-id'] || args.reportId) {
    ids = String(args['report-id'] || args.reportId)
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
  } else if (args['ids-file']) {
    ids = fs
      .readFileSync(args['ids-file'], 'utf8')
      .split(/\r?\n/)
      .map((s) => s.trim())
      .filter(Boolean);
  } else if (args.prefix) {
    const list = await request(
      'GET',
      `/api/bs/edc/report/list?appId=${appId}&appid=${appId}&groupid=-1&objId=-1&pageNo=1&pageSize=200`,
      headers,
      host
    );
    const rows = list.json?.data?.list || list.json?.data?.records || list.json?.data || [];
    const prefix = String(args.prefix);
    ids = (Array.isArray(rows) ? rows : [])
      .filter((r) => String(r.name || '').startsWith(prefix))
      .map((r) => String(r.id));
    console.log(JSON.stringify({ matched: ids.length, prefix, ids }, null, 2));
  }

  if (!ids.length) {
    console.error('没有可删除的 reportId');
    process.exit(2);
  }

  const results = [];
  for (const id of ids) {
    const res = await request('GET', `/api/bs/edc/report/deleteReport?id=${id}`, headers, host);
    results.push({
      reportId: id,
      code: res.json?.code,
      msg: res.json?.msg,
      ok: res.json?.code === 200,
    });
  }
  console.log(JSON.stringify({ deleted: results.filter((r) => r.ok).length, results }, null, 2));
  process.exit(results.every((r) => r.ok) ? 0 : 1);
}

main().catch((e) => {
  console.error(e.message || e);
  process.exit(1);
});
