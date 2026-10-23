'use strict';
/**
 * eb_auth.js —— E10 统一凭证解析（快速失败 / 明确提示 / 绝不反复调用）
 *
 * 设计目标（针对「登录自动获取不了、又一直等待/反复调用」）：
 *   1. 命中即返回，**每个进程最多 spawn 一次 `e10-login`**
 *   2. 凭证文件不存在 → **立刻**报错并给出「需要获取什么、去哪拿」的指引，不 spawn、不等待
 *   3. spawn 有**硬超时**（默认 8s，可用 EB_AUTH_TIMEOUT_MS 覆盖），超时即失败，不重试
 *   4. baseUrl 从本地 config.json 直读（明文），不消耗 CLI
 *
 * 解析顺序：
 *   ① 环境变量 EB_ETEAMSID / EB_HOST（推荐：source ./e10env.sh，零 spawn、零等待）
 *   ② 若 ~/.e10-cli/profiles/<profile>/auth 不存在 → 立即抛出 LOGIN_HELP
 *   ③ 读取本地 config.json 拿 baseUrl
 *   ④ 调一次 `e10-login status` 取 ETEAMSID（硬超时，仅一次）
 *   ⑤ 仍失败 → 抛出 LOGIN_HELP
 *
 * 用法：
 *   const A = require('./eb_auth.js');
 *   const sid = A.eteamsId();        // 缺凭证时抛 EbAuthError（带 .help）
 *   const host = A.baseUrl();
 *   const st = A.authStatus();       // {ok, source, eteamsId?, host?, help?} 不抛异常
 *
 * 环境变量：
 *   EB_ETEAMSID / EB_HOST     凭证（首选）
 *   E10_BASE_URL / E10_HOST   兼容旧名
 *   EB_AUTH_TIMEOUT_MS        CLI 硬超时，默认 8000
 *   EB_AUTH_NO_CLI=1          禁止 spawn CLI（纯 env 模式，用于测试）
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const E10_DIR = path.join(os.homedir(), '.e10-cli');
const PROFILES_DIR = path.join(E10_DIR, 'profiles');
const ACTIVE_PROFILE_FILE = path.join(E10_DIR, 'profile');
const CLI_TIMEOUT = Number(process.env.EB_AUTH_TIMEOUT_MS || 8000);
const NO_CLI = /^(1|true|yes)$/i.test(String(process.env.EB_AUTH_NO_CLI || ''));

class EbAuthError extends Error {
  constructor(message, extra) {
    super(message);
    this.name = 'EbAuthError';
    this.help = (extra && extra.help) || LOGIN_HELP;
    if (extra && extra.reason) this.reason = extra.reason;
  }
}

const LOGIN_HELP = [
  '',
  '════════════════════════════════════════════════════════════════',
  '未获取到 E10 登录凭证（ETEAMSID）—— 请手动提供，本工具不会自动登录',
  '════════════════════════════════════════════════════════════════',
  '',
  '【需要获取的东西】浏览器里该平台的 ETEAMSID cookie 值',
  '',
  '  1. 用浏览器打开平台地址并完成登录（能正常看到首页即可）',
  '  2. 按 F12 → Application / 应用程序 → Storage → Cookies → 选中该站点',
  '  3. 复制名为 ETEAMSID 的那一行 Value',
  '     形如：PCACCOUNT_EXAMPLE_SESSION_VALUE',
  '     （也可在 DevTools → Network 里任一请求的 Cookie 头中找 ETEAMSID=... ）',
  '',
  '【拿到后二选一】',
  '',
  '  A) 只对当前终端生效 —— 最快，零等待（推荐）',
  '       export EB_ETEAMSID="<粘贴 cookie>"',
  '       export EB_HOST="<平台地址，如 https://itsm.hongjing-wh.com:5001>"',
  '     已在 D:/Workspace/WorkBuddy/.workbuddy 下准备好 e10env.sh，可直接：',
  '       source ./e10env.sh            # 有 env 直接用；没有则读一次 e10-login',
  '',
  '  B) 持久写入 —— 之后所有脚本免配置',
  '       e10-login set --eteamsid "<粘贴 cookie>" --base-url "<平台地址>"',
  '',
  '【为什么不能自动登录】',
  '  本环境 SSO 的 authorize 端点不发放授权码（302 → logintip?code=80015），',
  '  `e10-login oidc` 的本地回调永远等不到 → 会一直卡住。所以禁止用 oidc 兜底。',
  '',
  '【安全】cookie 等同账号会话，不要写进代码、不要提交仓库。',
  '════════════════════════════════════════════════════════════════',
  '',
].join('\n');

// ── 本地 profile / config（明文，零 spawn） ──────────────────

function activeProfile() {
  const fromEnv = String(process.env.E10_PROFILE || '').trim();
  if (fromEnv) return fromEnv;
  try {
    const n = fs.readFileSync(ACTIVE_PROFILE_FILE, 'utf8').trim();
    if (n) return n;
  } catch (e) { /* ignore */ }
  return 'default';
}

function profileDir(profile) {
  return path.join(PROFILES_DIR, profile || activeProfile());
}

/** 本地 config.json 是明文，可直读 baseUrl / tenantKey（不消耗 CLI） */
function readLocalConfig(profile) {
  try {
    const raw = fs.readFileSync(path.join(profileDir(profile), 'config.json'), 'utf8');
    const j = JSON.parse(raw);
    return {
      baseUrl: String(j.baseUrl || j.passportUrl || '').replace(/\/+$/, ''),
      tenantKey: String(j.tenantKey || ''),
    };
  } catch (e) {
    return { baseUrl: '', tenantKey: '' };
  }
}

function authFileExists(profile) {
  if (fs.existsSync(path.join(profileDir(profile), 'auth'))) return true;
  // 旧版单文件布局
  return fs.existsSync(path.join(E10_DIR, 'auth'));
}

// ── 解析 ────────────────────────────────────────────────────

let _cache = null;

function fromEnv() {
  const sid = String(process.env.EB_ETEAMSID || process.env.ETEAMSID || '').trim();
  const host = String(
    process.env.EB_HOST || process.env.E10_BASE_URL || process.env.E10_HOST || ''
  ).replace(/\/+$/, '');
  if (!sid) return null;
  return { eteamsId: sid, host, source: 'env' };
}

/** 只调一次 `e10-login status`，带硬超时；失败即返回 null，绝不重试 */
function fromCli() {
  if (NO_CLI) return null;
  let r;
  try {
    r = spawnSync('e10-login', ['status'], {
      encoding: 'utf8',
      shell: false,
      timeout: CLI_TIMEOUT,
      killSignal: 'SIGKILL',
      env: process.env,
    });
  } catch (e) {
    return { error: `调用 e10-login 失败：${e.message}` };
  }
  if (r.error && r.error.code === 'ETIMEDOUT') return { error: `e10-login 超时（>${CLI_TIMEOUT}ms）` };
  if (r.error) return { error: `调用 e10-login 失败：${r.error.message}` };
  const out = `${r.stdout || ''}${r.stderr || ''}`;
  const m = out.match(/ETEAMSID:\s*(\S+)/);
  if (!m) return { error: 'e10-login status 未返回 ETEAMSID（未登录或凭证已过期）' };
  const bm = out.match(/baseUrl:\s*(\S+)/);
  return {
    eteamsId: m[1].trim(),
    host: bm ? bm[1].replace(/\/+$/, '') : '',
    source: 'e10-login',
  };
}

/**
 * 解析凭证（带进程内缓存）。
 * @returns {{eteamsId:string, host:string, source:string}}
 * @throws {EbAuthError} 缺凭证时 —— 错误信息已含完整获取指引
 */
function resolve(profile) {
  if (_cache) return _cache;

  const env = fromEnv();
  if (env) {
    if (!env.host) {
      const local = readLocalConfig(profile);
      env.host = local.baseUrl;
    }
    if (!env.host) {
      throw new EbAuthError(
        'EB_ETEAMSID 已设置，但缺少平台地址 EB_HOST。',
        { reason: 'no_host' }
      );
    }
    _cache = env;
    return _cache;
  }

  // 凭证文件不存在 → 立即失败，不 spawn、不等待
  if (!authFileExists(profile)) {
    throw new EbAuthError(
      `未找到登录凭证文件（${path.join(profileDir(profile), 'auth')} 不存在）。`,
      { reason: 'no_auth_file' }
    );
  }

  const local = readLocalConfig(profile);
  const cli = fromCli();
  if (cli && cli.eteamsId) {
    _cache = {
      eteamsId: cli.eteamsId,
      host: cli.host || local.baseUrl,
      source: cli.source,
    };
    if (!_cache.host) {
      throw new EbAuthError('已取到 ETEAMSID，但无法确定平台地址（config.json 缺 baseUrl）。', {
        reason: 'no_host',
      });
    }
    return _cache;
  }

  throw new EbAuthError(
    `读取登录凭证失败：${(cli && cli.error) || '未知原因'}`,
    { reason: (cli && cli.error) || 'cli_failed' }
  );
}

function eteamsId(profile) {
  return resolve(profile).eteamsId;
}

function baseUrl(profile) {
  return resolve(profile).host.replace(/\/+$/, '');
}

function cookieHeader(profile) {
  const sid = eteamsId(profile);
  return `langType=zh_CN; LOGIN_TYPE=pc_account; ETEAMSID=${sid}`;
}

/** 不抛异常的状态查询，供门禁脚本直接打印 */
function authStatus(profile) {
  try {
    const r = resolve(profile);
    return {
      ok: true,
      source: r.source,
      eteamsId: r.eteamsId,
      eteamsIdMasked: r.eteamsId.length > 16
        ? `${r.eteamsId.slice(0, 10)}…(len=${r.eteamsId.length})`
        : '***',
      host: r.host,
      profile: profile || activeProfile(),
    };
  } catch (e) {
    return {
      ok: false,
      reason: e.reason || 'unknown',
      profile: profile || activeProfile(),
      authFile: path.join(profileDir(profile), 'auth'),
      authFileExists: authFileExists(profile),
      message: e.message,
      help: e.help || LOGIN_HELP,
    };
  }
}

/** 缺凭证时直接打印指引并 exit(2)；有凭证则静默返回 */
function requireAuthOrExit(profile) {
  const st = authStatus(profile);
  if (st.ok) return st;
  console.error(st.message);
  console.error(st.help);
  process.exit(2);
}

function shellQuote(s) {
  return "'" + String(s).replace(/'/g, "'\\''") + "'";
}

if (require.main === module) {
  const mode = process.argv[2] || '--status';
  const st = authStatus();
  if (!st.ok) {
    console.error(st.message);
    console.error(st.help);
    process.exit(1);
  }
  if (mode === '--export') {
    // 供 `source e10env.sh` 直接 eval，省掉重复 node 进程
    const r = resolve();
    console.log(`export EB_ETEAMSID=${shellQuote(r.eteamsId)}`);
    console.log(`export EB_HOST=${shellQuote(r.host)}`);
  } else if (mode === '--host') {
    console.log(resolve().host);
  } else {
    console.log(JSON.stringify(st, null, 2));
  }
}

module.exports = {
  EbAuthError,
  LOGIN_HELP,
  activeProfile,
  authFileExists,
  authStatus,
  baseUrl,
  cookieHeader,
  eteamsId,
  readLocalConfig,
  requireAuthOrExit,
  resolve,
};
