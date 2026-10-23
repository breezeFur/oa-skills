'use strict';
/**
 * 报表列表页操作 — references/report-list-page-ops-guide.md
 *
 * group list|add|delete|save
 * move --report-id --group-id --app-id
 * transfer --report-id --app-id|--app-name [--confirm-app-id]
 * app-search --name
 * matrix list|save|delete
 */
const fs = require('fs');
const https = require('https');

const { parseJsonSnowflakeSafe } = require('./json_snowflake');
const { resolveE10Host } = require('./resolve_e10_host');

const SENTINEL_GROUP = new Set(['-1', '-2', '-3', '']);

function parseArgs(argv) {
  const out = { _: [] };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a.startsWith('--')) {
      const key = a.slice(2).replace(/-/g, '_');
      out[key] = argv[i + 1];
      i++;
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

function request(host, method, urlPath, { appId, body, form, referer } = {}) {
  return new Promise((resolve, reject) => {
    const sid = eteamsId();
    const headers = {
      accept: 'application/json, text/plain, */*',
      eteamsid: sid,
      Cookie: `ETEAMSID=${sid}`,
      'User-Agent': 'Mozilla/5.0 AgentType=WorkBuddy,IsAgent=true',
      origin: host,
      referer: referer || `${host}/sp/ebdapp/detail/${appId || ''}/report`,
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
      const boundary = '----ListOps' + Date.now();
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
        res.on('end', () => {
          resolve({ status: res.statusCode, raw: data, json: parseJsonSnowflakeSafe(data) });
        });
      }
    );
    req.on('error', reject);
    if (payload) req.write(payload);
    req.end();
  });
}

function asArray(data) {
  if (Array.isArray(data)) return data;
  if (Array.isArray(data?.list)) return data.list;
  if (Array.isArray(data?.records)) return data.records;
  if (Array.isArray(data?.data)) return data.data;
  return [];
}

function groupIdOf(g) {
  return String(g?.id ?? g?.groupId ?? '');
}

function groupNameOf(g) {
  return String(g?.name ?? g?.content ?? g?.groupName ?? '');
}

function isUserGroup(g) {
  const id = groupIdOf(g);
  return id && !SENTINEL_GROUP.has(id);
}

function movableGroups(list) {
  return (list || []).filter(isUserGroup).map((g) => ({
    id: groupIdOf(g),
    name: groupNameOf(g),
    showOrder: g.showOrder,
  }));
}

async function listGroups(host, appId, groupType = '0') {
  const r = await request(
    host,
    'GET',
    `/api/bs/edc/report/group/list?appid=${encodeURIComponent(appId)}&groupType=${groupType}`,
    { appId }
  );
  const rows = asArray(r.json?.data ?? r.json);
  return { raw: r, rows, movable: movableGroups(rows) };
}

async function saveGroups(host, appId, groups, groupType = '0') {
  const cleaned = (groups || []).filter(isUserGroup);
  return request(host, 'POST', '/api/bs/edc/report/group/save', {
    appId,
    form: {
      appid: String(appId),
      groupType: String(groupType),
      groups: JSON.stringify(cleaned),
    },
  });
}

function isAppEnabled(row) {
  if (row == null) return false;
  if (row.enable === false || row.enable === 0 || row.enable === '0') return false;
  if (row.enabled === false || row.enabled === 0) return false;
  if (row.status === 0 || row.status === '0' || row.status === 'disable' || row.status === 'disabled')
    return false;
  if (row.isEnable === false || row.isEnable === 0) return false;
  return true;
}

async function searchApps(host, name, pageNo = 1, pageSize = 20) {
  const q = new URLSearchParams({
    name: name || '',
    pageNo: String(pageNo),
    pageSize: String(pageSize),
  });
  const r = await request(host, 'GET', `/api/bs/ebuilder/app/list?${q}`, {
    referer: `${host}/sp/ebdapp/home`,
  });
  const rows = asArray(r.json?.data ?? r.json);
  const apps = rows
    .map((a) => ({
      id: String(a.id ?? a.appId ?? ''),
      name: String(a.name ?? a.appName ?? ''),
      folder: a.folderName || a.belongFolder || a.parentName || '',
      creator: a.creatorName || a.createName || a.creator || '',
      enable: isAppEnabled(a),
      rawFlags: {
        enable: a.enable,
        enabled: a.enabled,
        status: a.status,
        isEnable: a.isEnable,
      },
    }))
    .filter((a) => a.id);
  return {
    total: r.json?.data?.total ?? r.json?.total ?? apps.length,
    apps,
    enabled: apps.filter((a) => a.enable),
    response: r.json,
  };
}

async function moveReport(host, appId, reportId, groupId) {
  const { movable } = await listGroups(host, appId);
  if (!movable.length) {
    return {
      ok: false,
      action: 'move_blocked_no_groups',
      message: '当前应用无自建分组，无可选移动位置。请先「分组设置 → 添加分组」',
      movable: [],
    };
  }
  if (!movable.some((g) => g.id === String(groupId))) {
    return {
      ok: false,
      action: 'move_invalid_group',
      message: `groupId=${groupId} 不在自建分组列表中`,
      movable,
    };
  }
  const r = await request(host, 'POST', '/api/bs/edc/report/removeReport', {
    appId,
    form: { reportId: String(reportId), groupId: String(groupId) },
  });
  return { ok: true, action: 'moved', reportId, groupId, response: r.json, movable };
}

async function transferReport(host, reportIds, targetAppId, fromAppId) {
  const form = { appId: String(targetAppId) };
  // multipart multi reportIds: append as repeated keys in one string field if needed
  const boundary = '----Transfer' + Date.now();
  const parts = [];
  for (const rid of reportIds) {
    parts.push(`--${boundary}\r\nContent-Disposition: form-data; name="reportIds"\r\n\r\n${rid}\r\n`);
  }
  parts.push(`--${boundary}\r\nContent-Disposition: form-data; name="appId"\r\n\r\n${targetAppId}\r\n`);
  parts.push(`--${boundary}--\r\n`);
  const body = Buffer.from(parts.join(''), 'utf8');
  const sid = eteamsId();
  const headers = {
    accept: 'application/json, text/plain, */*',
    eteamsid: sid,
    Cookie: `ETEAMSID=${sid}`,
    'User-Agent': 'Mozilla/5.0 AgentType=WorkBuddy,IsAgent=true',
    origin: host,
    referer: `${host}/sp/ebdapp/detail/${fromAppId || ''}/report`,
    'Content-Type': `multipart/form-data; boundary=${boundary}`,
    'Content-Length': body.length,
  };
  if (fromAppId) {
    headers.ebBusinessId = String(fromAppId);
    headers.ebbusinessid = String(fromAppId);
  }
  const r = await new Promise((resolve, reject) => {
    const u = new URL(`${host}/api/bs/edc/report/transferReport`);
    const req = https.request(
      { hostname: u.hostname, port: u.port || 443, path: u.pathname, method: 'POST', headers, rejectUnauthorized: false },
      (res) => {
        let data = '';
        res.on('data', (c) => (data += c));
        res.on('end', () => resolve({ status: res.statusCode, json: parseJsonSnowflakeSafe(data), raw: data }));
      }
    );
    req.on('error', reject);
    req.write(body);
    req.end();
  });
  return {
    ok: r.json?.code === 200 || r.json?.data === true || r.status === 200,
    reportIds,
    targetAppId,
    note: '转移后目标应用下 group_id=-1（未分组）',
    response: r.json,
  };
}

async function matrixList(host, appId, reportId, type = '1') {
  const r = await request(host, 'POST', '/api/bs/edc/report/permission/matrix/list', {
    appId,
    body: { target: String(reportId), type: String(type) },
    referer: `${host}/sp/edc/report/designer/${reportId}`,
  });
  return { type, rows: asArray(r.json?.data ?? r.json), response: r.json };
}

async function matrixSaveUse(host, appId, reportId, viewMatrixRight) {
  // 全量替换使用矩阵：先读通用权限，保留 viewRight/disableRight
  const gen = await request(host, 'POST', '/api/bs/edc/report/permission/table/list/new', {
    appId,
    body: {
      permissionId: 'report_view',
      id: String(reportId),
      current: 1,
      pageSize: 200,
      permissionType: 1,
      params: { appId: String(appId) },
    },
  });
  const dis = await request(host, 'POST', '/api/bs/edc/report/permission/table/list/new', {
    appId,
    body: {
      permissionId: 'report_view',
      id: String(reportId),
      current: 1,
      pageSize: 200,
      permissionType: -1,
      params: { appId: String(appId) },
    },
  });
  const viewRight = asArray(gen.json?.data?.records ?? gen.json?.data ?? gen.json);
  const disableRight = asArray(dis.json?.data?.records ?? dis.json?.data ?? dis.json);
  const body = {
    [String(reportId)]: {
      viewRight,
      disableRight,
      viewMatrixRight: viewMatrixRight || [],
    },
  };
  return request(host, 'POST', '/api/bs/edc/report/permission/table/savePermissions', {
    appId,
    body,
    referer: `${host}/sp/edc/report/designer/${reportId}`,
  });
}

async function matrixSaveDisable(host, appId, reportId, rows) {
  return request(host, 'POST', '/api/bs/edc/report/permission/matrix/save', {
    appId,
    body: rows,
    referer: `${host}/sp/edc/report/designer/${reportId}`,
  });
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const cmd = args._[0];
  const host = hostOf(args);

  if (!cmd || cmd === 'help') {
    console.log(`Usage:
  report_list_ops.js group-list --app-id <id>
  report_list_ops.js group-add --app-id <id> --name "分组名"
  report_list_ops.js group-delete --app-id <id> --group-id <gid>
  report_list_ops.js move --app-id <id> --report-id <rid> --group-id <gid>
  report_list_ops.js transfer --report-id <rid> --app-id <targetAppId> [--from-app-id <id>]
  report_list_ops.js transfer --report-id <rid> --app-name "名" [--confirm-app-id <id>] [--from-app-id <id>]
  report_list_ops.js app-search --name "关键字" [--page 1] [--size 20]
  report_list_ops.js matrix-list --app-id <id> --report-id <rid> [--type 1|-1]
  report_list_ops.js matrix-save --app-id <id> --report-id <rid> --file row.json [--type 1|-1]
  report_list_ops.js matrix-delete --app-id <id> --report-id <rid> --matrix-id <mid> [--type 1|-1]`);
    process.exit(cmd ? 0 : 1);
  }

  if (cmd === 'group-list') {
    const appId = args.app_id;
    if (!appId) throw new Error('--app-id required');
    const { rows, movable } = await listGroups(host, appId, args.group_type || '0');
    console.log(JSON.stringify({ ok: true, count: rows.length, movableCount: movable.length, movable, groups: rows }, null, 2));
    return;
  }

  if (cmd === 'group-add') {
    const appId = args.app_id;
    const name = args.name;
    if (!appId || !name) throw new Error('--app-id and --name required');
    const { rows } = await listGroups(host, appId);
    const maxOrder = rows.reduce((m, g) => Math.max(m, Number(g.showOrder) || 0), 0);
    const next = [...rows.filter(isUserGroup), { id: '', name, showOrder: maxOrder + 1, nameLabelId: '-1' }];
    const saved = await saveGroups(host, appId, next);
    const after = await listGroups(host, appId);
    console.log(
      JSON.stringify(
        {
          ok: true,
          action: 'group_add',
          name,
          movable: after.movable,
          saveResponse: saved.json,
        },
        null,
        2
      )
    );
    return;
  }

  if (cmd === 'group-delete') {
    const appId = args.app_id;
    const gid = String(args.group_id || '');
    if (!appId || !gid) throw new Error('--app-id and --group-id required');
    if (SENTINEL_GROUP.has(gid)) throw new Error('cannot delete sentinel group');
    const { rows } = await listGroups(host, appId);
    const next = rows.filter((g) => isUserGroup(g) && groupIdOf(g) !== gid);
    const saved = await saveGroups(host, appId, next);
    const after = await listGroups(host, appId);
    console.log(
      JSON.stringify({ ok: true, action: 'group_delete', deleted: gid, movable: after.movable, saveResponse: saved.json }, null, 2)
    );
    return;
  }

  if (cmd === 'move') {
    const appId = args.app_id;
    const reportId = args.report_id;
    const groupId = args.group_id;
    if (!appId || !reportId || !groupId) throw new Error('--app-id --report-id --group-id required');
    const result = await moveReport(host, appId, reportId, groupId);
    console.log(JSON.stringify(result, null, 2));
    if (!result.ok) process.exit(1);
    return;
  }

  if (cmd === 'app-search') {
    const name = args.name || '';
    const found = await searchApps(host, name, Number(args.page || 1), Number(args.size || 20));
    console.log(JSON.stringify({ ok: true, query: name, ...found }, null, 2));
    return;
  }

  if (cmd === 'transfer') {
    const reportId = args.report_id;
    if (!reportId) throw new Error('--report-id required');
    let targetAppId = args.app_id || args.target_app_id;
    const appName = args.app_name;
    if (!targetAppId && appName) {
      const found = await searchApps(host, appName, 1, 50);
      const exact = found.enabled.filter((a) => a.name === appName);
      const fuzzy = exact.length ? exact : found.enabled.filter((a) => a.name.includes(appName));
      if (fuzzy.length === 0) {
        console.log(JSON.stringify({ ok: false, action: 'transfer_app_not_found', query: appName, candidates: found.enabled }, null, 2));
        process.exit(1);
      }
      if (fuzzy.length > 1 && !args.confirm_app_id) {
        console.log(
          JSON.stringify(
            {
              ok: false,
              action: 'transfer_need_confirm',
              message: '存在重名或多项匹配，请用户确认后传入 --confirm-app-id',
              candidates: fuzzy,
            },
            null,
            2
          )
        );
        process.exit(2);
      }
      targetAppId = args.confirm_app_id || fuzzy[0].id;
    }
    if (!targetAppId) throw new Error('--app-id or --app-name required');
    const result = await transferReport(
      host,
      String(reportId).split(',').map((s) => s.trim()).filter(Boolean),
      targetAppId,
      args.from_app_id || args.app_id_source
    );
    console.log(JSON.stringify(result, null, 2));
    if (!result.ok) process.exit(1);
    return;
  }

  if (cmd === 'matrix-list') {
    const appId = args.app_id;
    const reportId = args.report_id;
    if (!appId || !reportId) throw new Error('--app-id --report-id required');
    const result = await matrixList(host, appId, reportId, args.type || '1');
    console.log(JSON.stringify({ ok: true, ...result }, null, 2));
    return;
  }

  if (cmd === 'matrix-save') {
    const appId = args.app_id;
    const reportId = args.report_id;
    const file = args.file;
    if (!appId || !reportId || !file) throw new Error('--app-id --report-id --file required');
    let row = JSON.parse(fs.readFileSync(file, 'utf8'));
    if (Array.isArray(row)) {
      /* ok */
    } else row = [row];
    const type = String(args.type || row[0]?.rightsType || '1');
    row.forEach((r) => {
      r.targetId = String(reportId);
      r.rightsType = String(type);
      if (!r.id || !String(r.id).startsWith('tmp')) r.id = `tmp_${Date.now()}`;
    });
    let saved;
    if (type === '-1') {
      saved = await matrixSaveDisable(host, appId, reportId, row);
    } else {
      const cur = await matrixList(host, appId, reportId, '1');
      const merged = [...(cur.rows || []), ...row];
      saved = await matrixSaveUse(host, appId, reportId, merged);
    }
    console.log(JSON.stringify({ ok: true, action: 'matrix_save', type, response: saved.json }, null, 2));
    return;
  }

  if (cmd === 'matrix-delete') {
    const appId = args.app_id;
    const reportId = args.report_id;
    const matrixId = String(args.matrix_id || '');
    const type = String(args.type || '1');
    if (!appId || !reportId || !matrixId) throw new Error('--app-id --report-id --matrix-id required');
    const cur = await matrixList(host, appId, reportId, type);
    const remain = (cur.rows || []).filter((r) => String(r.id) !== matrixId);
    let saved;
    if (type === '-1') {
      const victim = (cur.rows || []).find((r) => String(r.id) === matrixId);
      if (!victim) throw new Error('matrix row not found');
      saved = await matrixSaveDisable(host, appId, reportId, [{ ...victim, deleteType: 1 }]);
    } else {
      saved = await matrixSaveUse(host, appId, reportId, remain);
    }
    console.log(
      JSON.stringify(
        { ok: true, action: 'matrix_delete', matrixId, type, remainCount: remain.length, response: saved.json },
        null,
        2
      )
    );
    return;
  }

  throw new Error(`Unknown command: ${cmd}`);
}

main().catch((e) => {
  console.error(JSON.stringify({ ok: false, error: String(e.message || e) }, null, 2));
  process.exit(1);
});
