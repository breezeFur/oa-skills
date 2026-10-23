'use strict';
/**
 * 新建报表默认表头样式（仅用户未指定样式、未给效果图时）
 * 见 references/default-header-style-guide.md
 */

/** 正文 / 数据格默认（克制） */
const DEFAULT_BODY_STYLE = {
  font: '微软雅黑',
  fontSize: 12,
  bold: false,
  italic: false,
  underline: false,
  foreColor: '#333333',
  backColor: '#FFFFFF',
  hAlign: 'left',
  vAlign: 'center',
  borderColor: '#CCCCCC',
};

/** 报表标题行（有 layout.title 时） */
const DEFAULT_TITLE_STYLE = {
  font: '微软雅黑',
  fontSize: 14,
  bold: true,
  italic: false,
  underline: false,
  foreColor: '#000000',
  backColor: '#B6D6FF',
  hAlign: 'center',
  vAlign: 'center',
  borderColor: '#99B8D9',
};

/** 列表字段表头行（列名 Const） */
const DEFAULT_HEADER_STYLE = {
  font: '微软雅黑',
  fontSize: 12,
  bold: true,
  italic: false,
  underline: false,
  foreColor: '#000000',
  backColor: '#E6E6E6',
  hAlign: 'center',
  vAlign: 'center',
  borderColor: '#CCCCCC',
};

/**
 * @param {object} spec build spec
 * @param {{ fromMockup?: boolean, userSpecifiedStyle?: boolean }} [hints]
 * @returns {{ title: object, header: object, body: object, source: 'default-header'|'user'|'plain' }}
 */
function resolveLayerStyles(spec, hints = {}) {
  const s = spec || {};
  const fromMockup =
    hints.fromMockup === true ||
    s.styleFromMockup === true ||
    s.fromMockup === true ||
    s.hasEffectImage === true;
  const applyDefault =
    s.applyDefaultHeader !== false && s.defaultHeader !== false && !fromMockup;

  const hasUserStyle = !!(
    hints.userSpecifiedStyle ||
    s.style ||
    s.titleStyle ||
    s.headerStyle ||
    s.bodyStyle ||
    s.columnHeaderStyle
  );

  // 用户明确关默认，或只要素色
  if (s.applyDefaultHeader === false || s.stylePreset === 'none' || s.stylePreset === 'plain') {
    const base = Object.assign({}, DEFAULT_BODY_STYLE, s.style || {});
    return {
      title: Object.assign({}, base, s.titleStyle || {}),
      header: Object.assign({}, base, s.headerStyle || s.columnHeaderStyle || {}),
      body: Object.assign({}, base, s.bodyStyle || {}),
      source: 'plain',
    };
  }

  // 用户指定了任意样式 / 效果图 → 用户优先；全局 style 下沉到各层，分层可覆盖
  if (hasUserStyle || fromMockup) {
    const base = Object.assign({}, DEFAULT_BODY_STYLE, s.style || {});
    return {
      title: Object.assign({}, base, s.titleStyle || {}),
      header: Object.assign({}, base, s.headerStyle || s.columnHeaderStyle || {}),
      body: Object.assign({}, base, s.bodyStyle || {}),
      source: 'user',
    };
  }

  // 未指定样式、无效果图 → 默认表头（标题蓝底 + 列表头灰底）+ 素色正文
  if (applyDefault) {
    return {
      title: Object.assign({}, DEFAULT_BODY_STYLE, DEFAULT_TITLE_STYLE, s.titleStyle || {}),
      header: Object.assign({}, DEFAULT_BODY_STYLE, DEFAULT_HEADER_STYLE, s.headerStyle || {}),
      body: Object.assign({}, DEFAULT_BODY_STYLE, s.bodyStyle || {}),
      source: 'default-header',
    };
  }

  const base = Object.assign({}, DEFAULT_BODY_STYLE);
  return {
    title: base,
    header: base,
    body: base,
    source: 'plain',
  };
}

module.exports = {
  DEFAULT_BODY_STYLE,
  DEFAULT_TITLE_STYLE,
  DEFAULT_HEADER_STYLE,
  resolveLayerStyles,
};

if (require.main === module) {
  const args = process.argv.slice(2);
  let inline = null;
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--inline') inline = JSON.parse(args[++i] || '{}');
    if (args[i] === '--list') {
      console.log(
        JSON.stringify(
          {
            DEFAULT_TITLE_STYLE,
            DEFAULT_HEADER_STYLE,
            DEFAULT_BODY_STYLE,
            guide: 'references/default-header-style-guide.md',
          },
          null,
          2
        )
      );
      process.exit(0);
    }
  }
  const r = resolveLayerStyles(inline || {});
  console.log(JSON.stringify(r, null, 2));
}
