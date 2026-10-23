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
 *   4. 失败即输出 need / how_to / askUser，且**禁止 oidc 兜底**与循环重试
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

  const askUser = {
    tool: 'AskUserQuestion',
    title: '需要 E10 登录凭证（ETEAMSID）',
    intro:
      `本环境 SSO 无法回调 localhost，\`e10-login oidc\` 会一直等待到超时 —— 请改用「提供 ETEAMSID」方式。` +
      `（当前 e10-login=${cliVersion}）`,
    requiredFields: [
      {
        key: 'eteamsid',
        label: 'ETEAMSID',
        required: true,
        what: '浏览器 Cookie 中名称为 ETEAMSID 的那一项的 Value（单值）',
        how: '已登录目标环境网页 → F12 → Application / 应用程序 → Storage → Cookies → 选中站点 → 找到 Name=ETEAMSID → 复制 Value',
        example: 'PCACCOUNT_EXAMPLE_SESSION_VALUE',
        not: [
          '不要整段 Cookie 请求头（不要 langType=...; ETEAMSID=...; ...）',
          '不要其它 cookie 名（langType / LOGIN_TYPE / JSESSIONID 等）',
        ],
      },
      {
        key: 'baseUrl',
        label: '平台 base-url',
        required: true,
        what: '环境根地址（与浏览器地址栏主机一致）',
        example: 'https://<your-e10-host>',
        not: ['不要带 /sp/edc/... 路径'],
      },
    ],
    agentRules: [
      '禁止因凭证缺失就拒绝报表搭建 —— 先向用户索要 ETEAMSID',
      '未拿到 eteamsid + baseUrl 前不要瞎猜 token',
      '禁止用 e10-login oidc 兜底（本环境不返回授权码，会一直卡住）',
      '禁止循环重试 auth ready / status',
    ],
  };

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
        need: '浏览器登录后，从 DevTools 复制名为 ETEAMSID 的 cookie 值（另需平台 baseUrl）',
        how_to: [
          '方式 A（最快，零等待）：export EB_ETEAMSID="<粘贴 cookie>"  且  export EB_HOST="<平台地址>"',
          '方式 B（持久）：e10-login set --eteamsid "<粘贴 cookie>" --base-url "<平台地址>"',
          '写入后重新执行：edc-report auth ready（一次即结论，不要循环）',
        ],
        forbid: '禁止 e10-login oidc 兜底：本环境 SSO 不返回授权码，命令会一直等待',
        askUser,
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
