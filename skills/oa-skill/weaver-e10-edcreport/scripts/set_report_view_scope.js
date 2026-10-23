/**
 * 设置报表「使用范围」通用权限（savePermissions 全量替换 viewRight）。
 *
 * Usage:
 *   node set_report_view_scope.js --report-id <id> --app-id <appId> \
 *     --scope "role:eb分权管理员,channel:测试-zc0813"
 *   node set_report_view_scope.js --report-id <id> --app-id <appId> --scope all
 *   node set_report_view_scope.js --report-id <id> --app-id <appId> --list
 *
 * scope 类型：role / channel|group / department / resource|user / all / allExternal
 * 群组 UI 称「群组」，API 用 channel（targetType 14），浏览器 /hrm/.../data/channel
 */

const https = require('https');
const { randomBytes } = require('crypto');
const { parseJsonSnowflakeSafe } = require('./json_snowflake');
const { resolveE10Host } = require('./resolve_e10_host');

const SHARE_META = {
  role: { objType: 'role', targetType: 10, valueKey: 'obj_id_role', entity: 'role', span: '角色', extra: { role_level: '0' } },
  channel: { objType: 'channel', targetType: 14, valueKey: 'obj_id_channel', entity: 'channel', span: '群组' },
  group: { objType: 'channel', targetType: 14, valueKey: 'obj_id_channel', entity: 'channel', span: '群组' },
  department: { objType: 'department', targetType: 2, valueKey: 'obj_id_department', entity: 'dept', span: '部门' },
  resource: { objType: 'resource', targetType: 1, valueKey: 'obj_id', entity: 'resource', span: '人员' },
  user: { objType: 'resource', targetType: 1, valueKey: 'obj_id', entity: 'resource', span: '人员' },
  all: { objType: 'all', targetType: 11, valueKey: null, entity: 'all', span: '所有人', targetId: '0' },
  allExternal: { objType: 'allExternal', targetType: 12, valueKey: null, entity: 'allExternal', span: '所有外部人', targetId: '0' },
};

function parseArgs(argv) {
  const out = { host: '', reportId: '', appId: '', scope: '', list: false };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--host') out.host = argv[++i];
    else if (a === '--report-id') out.reportId = argv[++i];
    else if (a === '--app-id') out.appId = argv[++i];
    else if (a === '--scope') out.scope = argv[++i];
    else if (a === '--list') out.list = true;
  }
  if (!out.host) out.host = resolveE10Host();
  return out;
}

function eteamsId() {
  return require('./eb_auth.js').eteamsId();
}

function request(host, method, urlPath, { body, appId, reportId } = {}) {
  return new Promise((resolve, reject) => {
    const headers = {
      accept: 'application/json, text/plain, */*',
      eteamsid: eteamsId(),
      ebBusinessId: appId || '',
      Cookie: `ETEAMSID=${eteamsId()}`,
      'User-Agent': 'Mozilla/5.0 AgentType=WorkBuddy,IsAgent=true',
      origin: host,
      referer: `${host}/sp/edc/report/designer/${reportId || ''}`,
      langType: 'zh_CN',
    };
    let payload = null;
    if (body) {
      payload = Buffer.from(JSON.stringify(body), 'utf8');
      headers['Content-Type'] = 'application/json;charset=UTF-8';
      headers['Content-Length'] = payload.length;
    }
    const u = new URL(host + urlPath);
    const req = https.request(
      { hostname: u.hostname, port: u.port || 443, path: u.pathname + u.search, method, headers, rejectUnauthorized: false },
      (res) => {
        let data = '';
        res.on('data', (c) => (data += c));
        res.on('end', () => resolve({ json: parseJsonSnowflakeSafe(data), raw: data }));
      }
    );
    req.on('error', reject);
    if (payload) req.write(payload);
    req.end();
  });
}

function extractItems(json) {
  const d = json?.data;
  if (!d) return [];
  if (Array.isArray(d)) return d;
  if (Array.isArray(d.data)) return d.data;
  if (Array.isArray(d.records)) return d.records;
  if (d.data && Array.isArray(d.data.data)) return d.data.data;
  return [];
}

async function hrmSearch(host, appId, reportId, kind, keyword) {
  const paths = {
    role: ['/api/hrm/common/browser/complete/role', { browserMultiple: true, searchValue: keyword, newly: 0 }],
    channel: ['/api/hrm/common/browser/data/channel', { browserMultiple: true, keywords: keyword, current: 1, pageSize: 50 }],
    department: ['/api/workflow/pathdef/common/browser/complete/department', { browserMultiple: true, virtualType: 'All', showSanYuan: true, newly: 0, searchValue: keyword }],
    resource: ['/api/edc/report/common/browser/complete/resource', { browserMultiple: true, searchValue: keyword, authWecahtBook: true }],
  };
  const spec = paths[kind];
  if (!spec) throw new Error(`no browser for kind: ${kind}`);
  const res = await request(host, 'POST', spec[0], { body: spec[1], appId, reportId });
  if (res.json?.code !== 200) return [];
  return extractItems(res.json);
}

function buildEntry(reportId, meta, targetId, label) {
  const tid = meta.targetId != null ? meta.targetId : String(targetId);
  const entry = {
    sourceId: reportId,
    permissionId: 'report_view',
    permissionType: 1,
    targetType: meta.targetType,
    targetId: tid,
    sourceType: 1,
    objType: meta.objType,
    objTypeSpan: meta.span,
    _entityType: meta.entity,
    seclevel: { min: -999, max: 999 },
    shareKey: `tmp_${meta.objType}_${tid}_${randomBytes(3).toString('hex')}`,
    ...(meta.extra || {}),
  };
  if (meta.objType === 'all') {
    Object.assign(entry, {
      obj_id_all: [{ content: '所有人', icon: 'Icon-all02', id: '0' }],
      obj_id_span: '所有人', objIdList: ['所有人'], content: '所有人', name: '所有人', title: '所有人', icon: 'Icon-all02',
    });
  } else if (meta.objType === 'allExternal') {
    Object.assign(entry, {
      obj_id_span: '所有外部人', objIdList: ['所有外部人'], content: '所有外部人', name: '所有外部人', title: '所有外部人',
    });
  } else if (meta.valueKey) {
    const t = { id: tid, name: label, content: label, title: label };
    entry[meta.valueKey] = [t];
    Object.assign(entry, { obj_id_span: label, objIdList: [label], content: label, name: label, title: label });
  }
  return entry;
}

async function resolveScope(host, appId, reportId, scopeStr) {
  const parts = scopeStr.split(',').map((s) => s.trim()).filter(Boolean);
  const viewRight = [];
  for (const part of parts) {
    const [kind, ...rest] = part.split(':');
    const name = rest.join(':').trim();
    const meta = SHARE_META[kind];
    if (!meta) throw new Error(`unknown scope kind: ${kind}`);
    if (meta.objType === 'all' || meta.objType === 'allExternal') {
      viewRight.push(buildEntry(reportId, meta));
      continue;
    }
    if (!name) throw new Error(`scope ${kind} requires name`);
    const browserKind = kind === 'group' ? 'channel' : kind === 'user' ? 'resource' : kind;
    const items = await hrmSearch(host, appId, reportId, browserKind, name);
    const hit = items.find((x) => (x.name || x.content || x.title) === name) || items[0];
    if (!hit) throw new Error(`not found: ${kind}:${name}`);
    viewRight.push(buildEntry(reportId, meta, hit.id, name));
  }
  return viewRight;
}

async function listScope(host, appId, reportId) {
  const res = await request(host, 'POST', '/api/bs/edc/report/permission/table/list/new', {
    body: { permissionId: 'report_view', id: reportId, current: 1, pageSize: 50, permissionType: 1, params: { appId } },
    appId,
    reportId,
  });
  return extractItems(res.json);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (!args.reportId || !args.appId) throw new Error('--report-id and --app-id required');

  if (args.list) {
    const items = await listScope(args.host, args.appId, args.reportId);
    console.log(JSON.stringify(items.map((it) => ({
      objType: it.objType,
      objTypeSpan: it.objTypeSpan,
      targetType: it.targetType,
      targetId: it.targetId,
      label: it.obj_id_span || it.content || it.name,
    })), null, 2));
    return;
  }
  if (!args.scope) throw new Error('--scope required (or --list)');

  const viewRight = await resolveScope(args.host, args.appId, args.reportId, args.scope);
  const body = { [args.reportId]: { viewRight, disableRight: [], viewMatrixRight: [] } };
  const save = await request(args.host, 'POST', '/api/bs/edc/report/permission/table/savePermissions', {
    body, appId: args.appId, reportId: args.reportId,
  });
  console.log('savePermissions:', save.json.code, save.json.msg || '');
  const items = await listScope(args.host, args.appId, args.reportId);
  items.forEach((it) => {
    console.log(` - ${it.objTypeSpan || it.objType} ${it.obj_id_span || it.content || ''} targetType=${it.targetType} targetId=${it.targetId}`);
  });
}

main().catch((e) => {
  console.error('ERROR:', e.message);
  process.exit(1);
});
