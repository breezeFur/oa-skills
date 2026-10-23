'use strict';
/**
 * resolve_e10_host.js — 统一平台地址解析（`eb_auth.js` 的薄封装）
 *
 * ⚠️ 本文件曾长期缺失，导致以下依赖它的脚本一运行就 `MODULE_NOT_FOUND`：
 *    create_report.js / find_form_in_app.js / dataset_ops.js / report_lifecycle.js /
 *    report_list_ops.js / save_as_version.js / save_query_item.js / set_report_view_scope.js /
 *    suggest_join_fields.js / validate_*.js / verify_*.js / cleanup_empty_shells.js
 *
 * 契约（调用方约定，勿改签名）：
 *   const { resolveE10Host } = require('./resolve_e10_host');
 *   const host = resolveE10Host();                 // → 'https://xxx'（无尾斜杠）
 *   const host = resolveE10Host({ host: argvHost }); // 显式地址优先
 *
 * 解析优先级（越靠前越省事，也越优先）：
 *   ① `opts.host`（命令行 `--host` 显式指定）
 *   ② 环境变量 `EB_HOST` → `E10_BASE_URL` → `E10_HOST`（推荐：source e10env.sh，零 spawn）
 *   ③ 本地 `~/.e10-cli/profiles/<profile>/config.json` 的 `baseUrl`（明文直读，零 spawn）
 *   ④ 兜底走 `eb_auth.baseUrl()`：最多一次 `e10-login status`（硬超时）
 *   ⑤ 全失败 → 抛 `EbAuthError`，错误信息已含「需要获取什么」的完整指引
 *
 * 设计约束：**不等待、不循环重试**。缺凭证时立即失败并给出获取步骤，
 * 便于上层把指引原样转达给用户（见 references/login-and-render-policy.md）。
 */

const A = require('./eb_auth.js');

function stripTrailingSlash(u) {
  return String(u || '').trim().replace(/\/+$/, '');
}

/**
 * @param {{host?: string}} [opts]
 * @returns {string} 形如 `https://itsm.hongjing-wh.com:5001`
 * @throws {Error} 缺地址且无法解析时（错误信息含获取指引）
 */
function resolveE10Host(opts) {
  const explicit = stripTrailingSlash(opts && opts.host);
  if (explicit) return explicit;

  const envHost = stripTrailingSlash(
    process.env.EB_HOST || process.env.E10_BASE_URL || process.env.E10_HOST || ''
  );
  if (envHost) return envHost;

  try {
    const local = A.readLocalConfig();
    if (local && local.baseUrl) return stripTrailingSlash(local.baseUrl);
  } catch (_) {
    /* 读不到本地 config 就继续往下走 */
  }

  // 兜底：eb_auth 会尝试一次 CLI；失败时抛出带指引的错误
  return stripTrailingSlash(A.baseUrl());
}

module.exports = { resolveE10Host };
