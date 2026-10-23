/**
 * E10 雪花 ID（64 位）超过 JS Number.MAX_SAFE_INTEGER (9007199254740991)。
 * 禁止对含 id 字段的 API 响应直接使用 JSON.parse，否则末位会漂移。
 *
 * 安全策略：仅对已知 ID 字段名的数值加引号，不碰嵌套 JSON 字符串内的数字。
 */
const ID_FIELD_NAMES = [
  'id', 'reportId', 'sheetId', 'pageId', 'sourceId', 'targetId', 'navId',
  'appId', 'appid', 'groupId', 'groupid', 'objId', 'designKey', 'datasetId',
  'dataSetId', 'permissionId', 'sysMenuId', 'navId', 'remoteAppId',
  'creator', 'formId', 'objid', 'reportid',
];

function quoteSnowflakeLiterals(jsonText) {
  if (typeof jsonText !== 'string') return jsonText;
  let out = jsonText;
  for (const key of ID_FIELD_NAMES) {
    const re = new RegExp(
      `("${key}"\\s*:\\s*)(-?\\d{${16},})(?=\\s*[,}\\]])`,
      'gi'
    );
    out = out.replace(re, '$1"$2"');
  }
  return out;
}

function parseJsonSnowflakeSafe(jsonText) {
  return JSON.parse(quoteSnowflakeLiterals(String(jsonText)));
}

/** 从 raw 响应文本提取 ID（双保险，不依赖 parse） */
function extractIdFromRaw(raw, keys = ['id', 'reportId']) {
  for (const key of keys) {
    const re = new RegExp(`"${key}"\\s*:\\s*(\\d{16,})`);
    const m = String(raw).match(re);
    if (m) return m[1];
  }
  return '';
}

function stringifyId(value) {
  if (value == null || value === '') return '';
  return String(value);
}

module.exports = {
  ID_FIELD_NAMES,
  quoteSnowflakeLiterals,
  parseJsonSnowflakeSafe,
  extractIdFromRaw,
  stringifyId,
};
