/**
 * Enable scheduled snapshot — uses safe_report_save to preserve layout.
 *
 * Usage:
 *   node set_snapshot_schedule.js --report-id <id>
 *   node set_snapshot_schedule.js --report-id <id> --cron "0 0/1 * * * ?"
 *   node set_snapshot_schedule.js --report-id <id> --snapshot-name "自定义-{date}"
 *   node set_snapshot_schedule.js --report-id <id> --list-only
 *
 * 默认快照名：{报表名}-{date}-{time}（未传 --snapshot-name 时）
 * 雪花 ID 禁止 Number()——见 references/designer-blank-prevention-guide.md
 */
const https = require('https');
const {
  DEFAULT_HOST,
  getReportDevInfo,
  safeSaveReportDevInfo,
  assertLayoutNotEmptyBeforeSave,
} = require('./safe_report_save');
const {
  defaultSnapshotName,
  validateSnapshotPatch,
  validateShowLocation,
} = require('./validate_designer_blank_guard');

const DEFAULT_CRON = '0 0 0 * * ?';

function parseArgs() {
  const out = { reportId: '', cron: DEFAULT_CRON, snapshotName: '', listOnly: false, host: '' };
  const argv = process.argv.slice(2);
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--report-id') out.reportId = argv[++i];
    else if (argv[i] === '--cron') out.cron = argv[++i];
    else if (argv[i] === '--snapshot-name') out.snapshotName = argv[++i];
    else if (argv[i] === '--host') out.host = argv[++i];
    else if (argv[i] === '--list-only') out.listOnly = true;
  }
  if (!out.reportId) throw new Error('--report-id is required');
  if (!out.host) out.host = DEFAULT_HOST();
  return out;
}

function requestGet(url, headers) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    https
      .get({ hostname: u.hostname, port: u.port || 443, path: u.pathname + u.search, headers, rejectUnauthorized: false }, (res) => {
        let b = '';
        res.on('data', (c) => (b += c));
        res.on('end', () => resolve(JSON.parse(b)));
      })
      .on('error', reject);
  });
}

async function getBaseInfo(host, reportId, et, appId) {
  const headers = {
    eteamsid: et,
    ebBusinessId: appId || '',
    Cookie: `ETEAMSID=${et}`,
    Accept: 'application/json',
    Referer: `${host}/sp/edc/report/designer/${reportId}`,
    'User-Agent': 'Mozilla/5.0 AgentType=WorkBuddy,IsAgent=true',
  };
  const json = await requestGet(`${host}/api/bs/edc/report/baseInfo?id=${reportId}&useTag=backend`, headers);
  return json.data || {};
}

function buildSnapshotConfig(existing, reportId, reportName, cron, snapshotName) {
  const params = existing?.params || JSON.stringify({ searchCondition: {} });
  // 未指定名称 → 报表名-{date}-{time}；雪花 ID 必须字符串
  const name =
    snapshotName && String(snapshotName).trim()
      ? String(snapshotName).trim()
      : defaultSnapshotName(reportName);
  const cfg = {
    enableSnapshot: true,
    cron,
    snapshotName: name,
    params,
    sheetId: String(reportId),
  };
  if (existing?.enableSnapshot && existing?.deleteType === 0) {
    if (existing.id != null) cfg.id = String(existing.id);
    if (existing.jobId != null) cfg.jobId = String(existing.jobId);
  }
  return cfg;
}

async function main() {
  const args = parseArgs();
  const { reportId, cron, listOnly, host } = args;

  const { et, data } = await getReportDevInfo(host, reportId, '');
  const base = await getBaseInfo(host, reportId, et, '');
  const reportName = String(base.name || '报表').replace(/[\r\n]/g, '');
  const appId = String(base.appId || '0');
  const groupId = base.groupId != null ? String(base.groupId) : '0';
  const nameLabelId = base.nameLabelId != null ? String(base.nameLabelId) : '-1';
  const existing = data.snapshot || null;

  console.log('Report:', reportName, reportId);
  console.log('Layout:', assertLayoutNotEmptyBeforeSave(data));
  console.log('Current snapshot:', existing ? JSON.stringify(existing, null, 2) : '(none)');
  console.log('Default snapshotName:', defaultSnapshotName(reportName));

  if (listOnly) return;

  // showLocation 门禁：禁止带着 0 去合并保存
  const sp0 = (data.sheetProps && data.sheetProps[0]) || {};
  const locCheck = validateShowLocation(sp0.showLocation);
  if (!locCheck.ok) {
    console.warn('WARN showLocation:', locCheck.errors.join('; '), '→ will force', locCheck.normalized, 'on sheet tag');
  }

  const snapshot = buildSnapshotConfig(existing, reportId, reportName, cron, args.snapshotName);
  const gate = validateSnapshotPatch(snapshot, { reportId, reportName });
  if (!gate.ok) {
    console.error('BLANK_GUARD_FAIL', gate.errors);
    process.exit(1);
  }
  if (gate.warnings.length) console.warn('BLANK_GUARD_WARN', gate.warnings);

  console.log('\nTarget snapshot:', JSON.stringify(snapshot, null, 2));

  const result = await safeSaveReportDevInfo(host, {
    reportId,
    appId,
    name: reportName,
    designKey: data.designKey,
    devData: data,
    et,
    groupId,
    nameLabelId,
    patchFn: (wb) => {
      wb.snapshot = snapshot;
      // 防空白：合并时纠正 showLocation=0
      const sheets = wb.sheets || {};
      for (const sh of Object.values(sheets)) {
        if (!sh.tag) sh.tag = {};
        const cur = sh.tag.showLocation;
        if (cur == null || cur === 0 || cur === '0') {
          sh.tag.showLocation = locCheck.normalized || 2;
        }
      }
    },
  });

  const saved = result.after.snapshot;
  console.log('\nVerified fields:', result.after.fields?.length);
  console.log('Verified snapshot:', saved ? JSON.stringify(saved, null, 2) : '(none)');
  if (!saved?.enableSnapshot) {
    console.warn('Warning: snapshot may need manual enable in designer (scheduler conflict after rollback).');
  } else {
    console.log('\nDone. cron:', saved.cron, 'snapshotName:', saved.snapshotName);
    if (typeof saved.sheetId === 'number') {
      console.error(
        'BLANK_GUARD: 回读 sheetId 为 number（可能被 JSON 数字截断）。写入已用 String；若设计区异常请 verify blank'
      );
      process.exitCode = 1;
    }
  }
}

main().catch((e) => {
  console.error(e.message || e);
  process.exit(1);
});
