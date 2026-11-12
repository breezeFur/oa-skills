'use strict';
/**
 * auth_ready.js —— 秒级登录门禁（一次即结论 · 快速失败 · 明确指引）
 *
 * 契约：已就绪 → exit 0；不可用 → exit 1（JSON 里 action 说明下一步）。
 * 禁止用本命令触发浏览器登录。
 *
 * 慢点修复（本版重写要点）：
 *   1. 凭证解析统一走 scripts/eb_auth.js：
 *        env(EB_ETEAMSID/EB_HOST) 优先 → auth 文件不存在则**立即失败**（不 spawn、不等待）
 *        → 最多一次 `e10-login status`（硬超时 EB_AUTH_TIMEOUT_MS，默认 8s）
 *   2. 已就绪时**不再额外跑 `e10-login --version`**（旧版固定 2 次 spawn → 现在 0 次）
 *   3. 版本探测改为**惰性**：只在凭证不可用时才做，仅用于提示文案
 *   4. 失败只输出认证状态和实际支持的登录指引，不在门禁内登录、不循环重试
 */
const A = require('./eb_auth.js');
const { spawnSync } = require('child_process');

const status = A.authStatus();

if (!status.ok) {
  // 惰性版本探测：只用于文案，不阻断
  const vr = spawnSync('e10-login', ['--version'], { encoding: 'utf8', shell: false, env: process.env, timeout: 8000 });
  const vm = String(`${vr.stdout || ''}${vr.stderr || ''}`).match(/(\d+)\.(\d+)\.(\d+)/);
  const cliVersion = vm ? `${vm[1]}.${vm[2]}.${vm[3]}` : 'unknown';
  const legacy = !!vm && (+vm[1] < 1 || (+vm[1] === 1 && (+vm[2] < 5)));

  console.log(
    JSON.stringify(
      {
        ok: false,
        action: 'credential_required',
        reason: status.reason,
        profile: status.profile,
        authFile: status.authFile,
        authFileExists: status.authFileExists,
        cliVersion,
        legacyCli: legacy,
        message: status.message,
        need: '目标环境的有效会话；复用用户已提供的地址与登录授权',
        how_to: [
          'Agent 按 weaver-e10-login 准备匹配 CLI，再发起官方 OAuth，在官方页面使用已提供账号密码',
          '仅目标未知时询问地址；验证码、MFA、平台授权或工具障碍才交接用户',
          '完成登录后重新执行一次 edc-report auth ready，不循环重试',
        ],
        authentication: {
          preferredMethod: 'official_oauth',
          reuseProvidedCredentials: true,
          manualSession: '仅用户主动提供 ETEAMSID 并指定此方式时使用 set',
        },
      },
      null,
      2
    )
  );
  console.error(status.help);
  process.exit(1);
}

console.log(
  JSON.stringify(
    {
      ok: true,
      action: 'proceed',
      source: status.source,
      profile: status.profile,
      host: status.host,
      eteamsId: status.eteamsIdMasked,
      message: '凭证可用：直接进入报表搭建；不要调用 oidc，不要重复校验',
      renderPolicy:
        '搭建只要求落库成功，不要全量渲染（analysis 全量交叉表必然 code:555 且白烧 15~80s）；' +
        '验证用 getReportDevInfo.fields / verify_field_bind.js；确需渲染时 EB_ALLOW_RENDER=1 + EB_RENDER_TIMEOUT_MS。',
    },
    null,
    2
  )
);
process.exit(0);
