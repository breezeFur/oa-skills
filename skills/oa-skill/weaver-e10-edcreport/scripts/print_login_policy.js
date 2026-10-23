'use strict';
/**
 * edc-report policy login — 登录 / 低版本兼容政策
 */
const text = `
════════════════════════════════════════════════════════════
 edc-report 政策 · 登录与低版本兼容（强制）
════════════════════════════════════════════════════════════

门禁：edc-report auth ready（已登录 → 直接搭表，与 CLI 大版本无关）

1) 推荐升级（有条件）
   npm i -g e10-login@1.5.0 --registry https://registry.npmjs.org
   e10-login oidc --base-url <平台> --agent_type WorkBuddy

2) 低版本未登录（1.1.x 等 · 必须兼容，禁止因版本阻断）
   auth ready → action=login_required_legacy_set
   Agent 必须 AskUserQuestion，二选一：
     A. 升级到 1.5.0+ 再 oidc
     B. 用户提供必要信息后 set

3) 走 set 时用户须提供（必要信息）
   • eteamsid（必填）
       = 浏览器 Cookie 中 Name=ETEAMSID 的 Value（单值）
       形如 PCACCOUNT_xxxx-yyyy
       获取：F12 → Application → Cookies → ETEAMSID → 复制 Value
       禁止：整段 Cookie 头；禁止其它 cookie 名
   • baseUrl（必填）
       = 平台根地址，如 https://<your-e10-host>
       禁止：带 /sp/edc/... 路径
   • agentType（可选，默认 WorkBuddy）

4) 写入命令
   e10-login set --eteamsid "<用户提供的ETEAMSID>" --base-url "<用户提供的baseUrl>"
   e10-login status
   edc-report auth ready

5) 禁令
   • 禁止「必须先升到 1.5 才能搭表」话术
   • 禁止未向用户索要 eteamsid/baseUrl 就编造 token
   • 禁止为登录 Glob/Grep 乱扫仓库

细则：weaver-e10-login · references/e10-login-integration.md
CLI：edc-report auth ready（JSON 含 askUser / needFromUser）
════════════════════════════════════════════════════════════
`;

console.log(text.trim());
process.exit(0);
