/**
 * 报表列表页生命周期：复制 / 权限(所有人) / 添加到菜单 / 删除
 *
 * Usage:
 *   node report_lifecycle.js copy-and-menu --host https://<your-e10-host> --app-id <appId> --source-name "报表名"
 *   node report_lifecycle.js add-menu --host ... --app-id ... --report-id ... --menu-name "菜单名"
 *   node report_lifecycle.js delete --host ... --app-id ... --report-id ...
 */

const https = require('https');
const { randomBytes } = require('crypto');
const { parseJsonSnowflakeSafe, extractIdFromRaw, stringifyId } = require('./json_snowflake');
const { resolveE10Host } = require('./resolve_e10_host');

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

function request(host, appId, method, path, { body, form, referer } = {}) {
  return new Promise((resolve, reject) => {
    const headers = {
      accept: 'application/json, text/plain, */*',
      eteamsid: eteamsId(),
      ebBusinessId: appId,
      Cookie: `ETEAMSID=${eteamsId()}`,
      'User-Agent': 'Mozilla/5.0 AgentType=WorkBuddy,IsAgent=true',
      origin: host,
      referer: referer || `${host}/sp/ebdapp/detail/${appId}/report`,
    };
    let payload = null;
    if (body) {
      payload = Buffer.from(JSON.stringify(body), 'utf8');
      headers['Content-Type'] = 'application/json;charset=UTF-8';
      headers['Content-Length'] = payload.length;
    }
    if (form) {
      const boundary = '----LifeCycle' + randomBytes(6).toString('hex');
      const parts = Object.entries(form).map(
        ([k, v]) => `--${boundary}\r\nContent-Disposition: form-data; name="${k}"\r\n\r\n${v}\r\n`
      );
      parts.push(`--${boundary}--\r\n`);
      payload = Buffer.from(parts.join(''), 'utf8');
      headers['Content-Type'] = `multipart/form-data; boundary=${boundary}`;
      headers['Content-Length'] = payload.length;
    }
    const u = new URL(host + path);
    const req = https.request(
      { hostname: u.hostname, port: u.port || 443, path: u.pathname + u.search, method, headers, rejectUnauthorized: false },
      (res) => {
        let data = '';
        res.on('data', (c) => (data += c));
        res.on('end', () => {
          try {
            resolve({ raw: data, json: parseJsonSnowflakeSafe(data) });
          } catch (e) {
            reject(new Error(`parse fail: ${data.slice(0, 400)}`));
          }
        });
      }
    );
    req.on('error', reject);
    if (payload) req.write(payload);
    req.end();
  });
}

function flattenReports(data) {
  if (Array.isArray(data)) return data;
  return data.reportList || data.list || data.records || [];
}

async function findReport(host, appId, name) {
  const r = await request(host, appId, 'GET', `/api/bs/edc/report/list?appid=${appId}&groupid=-1&objId=-1`);
  const rows = flattenReports(r.json.data || []);
  const exact = rows.filter((x) => (x.name || x.reportName) === name);
  const hit = exact.length ? exact[0] : rows.find((x) => String(x.name || '').includes(name));
  if (!hit) throw new Error(`Report not found: ${name}`);
  return { id: stringifyId(hit.id || hit.reportId), name: hit.name || hit.reportName };
}

function everyoneViewRight(reportId) {
  return {
    sourceId: reportId,
    permissionId: 'report_view',
    permissionType: 1,
    targetType: 11,
    targetId: 0,
    sourceType: 1,
    objType: 'all',
    objTypeSpan: '所有人',
    _entityType: 'all',
    obj_id_all: [{ content: '所有人', icon: 'Icon-all02', id: '0' }],
    obj_id_span: '所有人',
    objIdList: ['所有人'],
    content: '所有人',
    seclevel: { min: -999, max: 999 },
    shareKey: 'tmp_all_0_' + randomBytes(3).toString('hex'),
  };
}

function menuShareMap() {
  return [{
    id: '0', content: '所有人', permissionId: 'sys_view', targetId: 0, targetType: 11,
    sourceType: 1, objIdList: ['所有人'], objType: 'all', objTypeSpan: '所有人',
    seclevel: { min: -999, max: 999 }, icon: 'Icon-all02',
    shareKey: 'temp_all_0_' + randomBytes(3).toString('hex'),
    obj_id_all: [{ content: '所有人', icon: 'Icon-all02', id: '0' }],
  }];
}

async function saveEveryonePermission(host, appId, reportId) {
  const body = { [reportId]: { viewRight: [everyoneViewRight(reportId)], viewMatrixRight: [], disableRight: [] } };
  return request(host, appId, 'POST', '/api/bs/edc/report/permission/table/savePermissions', {
    body,
    referer: `${host}/sp/edc/report/designer/${reportId}`,
  });
}

async function addReportToMenu(host, appId, reportId, menuName, menuSysId = '') {
  const nav = {
    content: menuName,
    id: menuSysId || '',
    openMode: '1',
    pid: '0',
    type: '0',
    params: [],
    showType: '1',
    showOrder: 1,
    firstTabChange: false,
    nameLabelId: '-1',
    nameAlias: menuName,
    tabs: '{}',
    combinationId: '',
    shareMap: menuShareMap(),
    excludeShareMap: [],
    showRightBtn: '1',
    urlLinkType: '0',
    page: { pageId: reportId, pageName: menuName, pageType: 'REPORT', terminalScopes: '', appid: appId },
    unitFill: '0',
  };
  return request(host, appId, 'POST', '/api/cusapp/app/savePublishMenu', {
    form: {
      appId,
      navigation: JSON.stringify(nav),
      isThirdParty: 'true',
      terminalType: 'PC',
    },
    referer: `${host}/sp/ebdapp/build/${appId}`,
  });
}

async function copyReport(host, appId, sourceId) {
  const r = await request(host, appId, 'GET', `/api/bs/edc/report/copySheet?sheetId=${sourceId}`, {
    referer: `${host}/sp/edc/report/designer/${sourceId}`,
  });
  const newId = extractIdFromRaw(r.raw) || stringifyId(r.json.data?.id);
  if (!newId) throw new Error('copySheet failed: ' + r.raw.slice(0, 300));
  return { newId, raw: r.raw, json: r.json };
}

async function deleteReport(host, appId, reportId) {
  return request(host, appId, 'GET', `/api/bs/edc/report/deleteReport?id=${reportId}`);
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const cmd = args._[0];
  const host = resolveE10Host({ host: args.host });
  const appId = args.app_id;
  if (!appId) throw new Error('--app-id required');
  if (!cmd) throw new Error('Usage: copy-and-menu | add-menu | delete');

  if (cmd === 'copy-and-menu') {
    const src = await findReport(host, appId, args.source_name || args.sourceName);
    console.log('Source:', src.name, src.id);
    const copy = await copyReport(host, appId, src.id);
    console.log('Copied ID:', copy.newId);
    await saveEveryonePermission(host, appId, copy.newId);
    const menu = await addReportToMenu(host, appId, copy.newId, args.menu_name || `${src.name}(复制)`);
    const pageId = extractIdFromRaw(menu.raw, ['pageId']) || menu.json.data?.pageId;
    console.log(JSON.stringify({
      appId,
      sourceReportId: src.id,
      newReportId: copy.newId,
      designerUrl: `${host}/sp/edc/report/designer/${copy.newId}`,
      menuPageId: pageId,
    }, null, 2));
    return;
  }

  if (cmd === 'add-menu') {
    const reportId = stringifyId(args.report_id);
    const menuName = args.menu_name || args.menuName;
    if (!reportId || !menuName) throw new Error('--report-id and --menu-name required');
    const menu = await addReportToMenu(host, appId, reportId, menuName, args.menu_sys_id || '');
    console.log('savePublishMenu:', menu.json.code, menu.json.msg);
    console.log('pageId:', extractIdFromRaw(menu.raw, ['pageId']));
    return;
  }

  if (cmd === 'delete') {
    const reportId = stringifyId(args.report_id);
    if (!reportId) throw new Error('--report-id required');
    const del = await deleteReport(host, appId, reportId);
    console.log('deleteReport:', del.json.code, del.json.msg);
    return;
  }

  throw new Error(`Unknown command: ${cmd}`);
}

main().catch((e) => {
  console.error('ERROR:', e.message || e);
  process.exit(1);
});
