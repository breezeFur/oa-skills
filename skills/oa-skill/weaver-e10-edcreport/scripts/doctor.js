'use strict';
/**
 * doctor.js —— 环境体检（把历史踩过的工具链坑变成可执行检查）
 *
 * 覆盖的坑（对应 pitfalls.js 的 id）：
 *   ENV-1 脚本漏 port（非 443 环境 ETIMEDOUT）        → scripts.port + env.probe
 *   ENV-2/ENV-4 脚本模块或打包依赖缺失（MODULE_NOT_FOUND）  → scripts.require
 *   ENV-3 全局 shim 悬空（指向已改名/已删入口）        → install.shim
 *   ENV-5 python helper 缺失（ImportError）          → scripts.py-dep
 *   ENV-6 安装树与开发树分叉                          → trees.diff
 *   ENV-7 入口 shebang 行 CRLF（npm link 每次重新分叉）→ install.eol
 *   AUTH-4 EB_HOST / E10_HOST 变量名不匹配            → env.host-var
 *   PERF-1/2 渲染守卫与 5 万格上限                     → perf.policy
 *
 * 用法：
 *   node doctor.js [env|scripts|install|trees|perf|all] [--json] [--fix] [--full]
 *     --fix    自动修可安全自愈项（入口行尾 CRLF→LF、shim 路径改指）
 *     --full   额外做全量 JS 语法检查（慢，默认跳过）
 *     --json   结构化输出
 *
 * 退出码：有 FAIL → 1；只有 WARN → 0（但会提示）。
 */
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');
const https = require('https');

const ROOT = path.join(__dirname, '..');          // 技能树根
const SCRIPTS = path.join(ROOT, 'scripts');
const PKG_DIR = path.join(ROOT, 'edc-report');
const ENTRY_REL = 'edc-report/edc-report.js';
const PEER_NAMES = ['weaver-e10-edcreport', 'weaver-e10-edcreport__skillhub'];

const results = [];
let fixCount = 0;

function add(scope, id, level, msg, hint) {
  results.push({ scope, id, level, msg, hint: hint || '' });
}
const ok = (s, i, m) => add(s, i, 'ok', m);
const warn = (s, i, m, h) => add(s, i, 'warn', m, h);
const fail = (s, i, m, h) => add(s, i, 'fail', m, h);
const info = (s, i, m) => add(s, i, 'info', m);

function parseArgs(v) {
  const a = { scope: 'all', json: false, fix: false, full: false };
  for (const x of v) {
    if (x === '--json') a.json = true;
    else if (x === '--fix') a.fix = true;
    else if (x === '--full') a.full = true;
    else if (!x.startsWith('--')) a.scope = x;
  }
  return a;
}

// ───────────────────────── env ─────────────────────────
function checkEnv() {
  let auth = null;
  try {
    auth = require('./eb_auth.js').authStatus();
  } catch (e) {
    fail('env', 'auth', `无法加载 eb_auth.js：${e.message}`, '检查 scripts/eb_auth.js 是否存在');
    return;
  }
  if (!auth.ok) {
    fail('env', 'auth', `凭证不可用：${auth.reason}（${auth.message}）`,
      'edc-report auth ready 会给出需要获取什么（浏览器 ETEAMSID cookie + baseUrl）');
    return;
  }
  ok('env', 'auth', `凭证可用 source=${auth.source} profile=${auth.profile}`);

  // AUTH-4 变量名匹配
  const hasEbHost = !!String(process.env.EB_HOST || '').trim();
  const hasE10Host = !!String(process.env.E10_HOST || '').trim();
  const hasBase = !!String(process.env.E10_BASE_URL || '').trim();
  if (hasEbHost && !hasE10Host && !hasBase) {
    warn('env', 'host-var', '只设置了 EB_HOST，未导出 E10_HOST/E10_BASE_URL',
      '老脚本读 E10_HOST → 让 e10env.sh 同时导出三个别名（本版 eb_auth 已兼容三者）');
  } else {
    ok('env', 'host-var', `host 变量齐备 (EB_HOST=${hasEbHost} E10_HOST=${hasE10Host} E10_BASE_URL=${hasBase})`);
  }

  // 端口是否解析到（ENV-1 的配置侧防线）
  let u = null;
  try { u = new URL(auth.host); } catch (e) { /* ignore */ }
  if (u && !u.port && u.protocol === 'https:') {
    info('env', 'host-port', `host=${auth.host} 未显式带端口 → 走 443`);
  } else if (u) {
    ok('env', 'host-port', `host=${auth.host} (port ${u.port || 443})`);
  }

  // CLI 版本
  const vr = spawnSync('e10-login', ['--version'], { encoding: 'utf8', shell: false, timeout: 8000 });
  const vm = String(`${vr.stdout || ''}${vr.stderr || ''}`).match(/(\d+)\.(\d+)\.(\d+)/);
  const cliVer = vm ? `${vm[1]}.${vm[2]}.${vm[3]}` : 'unknown';
  let pkgVer = 'unknown';
  try { pkgVer = require(path.join(PKG_DIR, 'package.json')).version; } catch (e) { /* ignore */ }
  ok('env', 'version', `e10-login=${cliVer}  edc-report=${pkgVer}`);
  if (vm && (+vm[1] < 1 || (+vm[1] === 1 && (+vm[2] < 5)))) {
    info('env', 'cli-legacy',
      `e10-login ${cliVer}（<1.5）不支持 oidc 自动登录 —— 本工具已不依赖 oidc，用 env 凭证即可`);
  }
}

/** 连通性探针：只做 TLS+TLS 层 HEAD，不依赖鉴权。能返回任何状态码即"可达"。 */
function probeHost() {
  return new Promise((resolve) => {
    let auth;
    try { auth = require('./eb_auth.js').authStatus(); } catch (e) { return resolve({ skipped: true }); }
    if (!auth.ok) return resolve({ skipped: true });
    let u;
    try { u = new URL(auth.host); } catch (e) { return resolve({ error: `host 不是合法 URL: ${auth.host}` }); }
    const t0 = Date.now();
    const req = https.request({
      method: 'HEAD', hostname: u.hostname, port: u.port || 443, path: '/',
      rejectUnauthorized: false, timeout: 8000,
    }, (res) => {
      res.resume();
      resolve({ reachable: true, status: res.statusCode, port: u.port || 443, ms: Date.now() - t0 });
    });
    req.setTimeout(8000, () => { req.destroy(new Error(`连接超时 >8000ms（port=${u.port || 443}）`)); });
    req.on('error', (e) => resolve({ error: `${e.message}（port=${u.port || 443}）`, timedOut: /超时/.test(e.message) }));
    req.end();
  });
}

// ───────────────────────── scripts ─────────────────────────
function walkJs(dir, out = []) {
  let ents = [];
  try { ents = fs.readdirSync(dir, { withFileTypes: true }); } catch (e) { return out; }
  for (const e of ents) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) {
      if (e.name !== 'node_modules' && e.name !== '__pycache__') walkJs(p, out);
    } else if (e.name.endsWith('.js')) out.push(p);
  }
  return out;
}

function checkScripts(full) {
  if (!fs.existsSync(path.join(SCRIPTS, 'verify_field_bind.js'))) {
    return fail('scripts', 'dir', `scripts 目录不可用：${SCRIPTS}`, 'CLI 必须与 scripts/ 同仓');
  }
  ok('scripts', 'dir', `scripts=${SCRIPTS}`);

  const files = walkJs(SCRIPTS);
  ok('scripts', 'count', `JS 脚本 ${files.length} 个`);

  // ENV-2/ENV-4 require 可解析
  const missing = [];
  let reqTotal = 0;
  for (const f of files) {
    let txt = '';
    try { txt = fs.readFileSync(f, 'utf8'); } catch (e) { continue; }
    for (const m of txt.matchAll(/require\(\s*['"](\.\/[^'"]+)['"]\s*\)/g)) {
      reqTotal++;
      const rel = m[1];
      const cand = path.resolve(path.dirname(f), rel);
      const tries = [cand, cand + '.js', cand + '.json', path.join(cand, 'index.js')];
      if (!tries.some((p) => fs.existsSync(p))) missing.push(`${path.basename(f)} → ${rel}`);
    }
  }
  if (missing.length) {
    fail('scripts', 'require', `${missing.length} 处本地 require 无法解析（会 MODULE_NOT_FOUND）`,
      missing.slice(0, 5).join('; ') + (missing.length > 5 ? ` …共${missing.length}` : ''));
  } else {
    ok('scripts', 'require', `${reqTotal} 处本地 require 全部可解析`);
  }

  // ENV-1 漏 port / 把 host:port 当 hostname（两种形态都会 ETIMEDOUT）
  const noPort = [];
  for (const f of files) {
    let txt = '';
    try { txt = fs.readFileSync(f, 'utf8'); } catch (e) { continue; }
    if (!/\.request\(|https?\.get\(/.test(txt)) continue;
    const uses = [...txt.matchAll(/hostname\s*:\s*([A-Za-z_$][\w$.]*(?:\(\))?)/g)].map((m) => m[1]);
    if (!uses.length) continue;
    if (/[^A-Za-z_]port\s*:/.test(txt)) continue;   // 已显式带 port → 安全
    const odd = [...new Set(uses.filter((v) => !/\.hostname$/.test(v)))];
    noPort.push(odd.length
      ? `${path.basename(f)} (hostname: ${odd.join('/')} —— 疑似 host:port 整串传入)`
      : path.basename(f));
  }
  if (noPort.length) {
    fail('scripts', 'port', `${noPort.length} 个脚本用 hostname 构造请求但全文无 port → 非 443 环境必超时`,
      noPort.join('; ') + '  → 必须拆成 { hostname, port: u.port || 443 }（见 pitfalls ENV-1）');
  } else {
    ok('scripts', 'port', '所有发起请求的脚本都带 port 且未把 host:port 当 hostname（非 443 环境安全）');
  }

  // ENV-5 python helper 依赖（先排除本地 .py，其余用 python 实测可导入性 → 不误报 stdlib）
  const pyFiles = [];
  try {
    for (const e of fs.readdirSync(SCRIPTS)) if (e.endsWith('.py')) pyFiles.push(e);
  } catch (e) { /* ignore */ }
  const candidates = new Map(); // mod → 引用它的文件列表
  for (const name of pyFiles) {
    let txt = '';
    try { txt = fs.readFileSync(path.join(SCRIPTS, name), 'utf8'); } catch (e) { continue; }
    for (const m of txt.matchAll(/^\s*(?:from|import)\s+([A-Za-z_][A-Za-z0-9_]*)/gm)) {
      const mod = m[1];
      if (fs.existsSync(path.join(SCRIPTS, `${mod}.py`))) continue; // 同目录本地模块
      if (!candidates.has(mod)) candidates.set(mod, []);
      const arr = candidates.get(mod);
      if (!arr.includes(name)) arr.push(name);
    }
  }
  if (!candidates.size) {
    ok('scripts', 'py-dep', `python 本地依赖齐备（${pyFiles.length} 个 .py，无需外部模块）`);
  } else {
    const mods = [...candidates.keys()];
    const py = process.env.PYTHON || 'python';
    const probe = [
      'import importlib.util, json, sys',
      'res = {}',
      'for m in sys.argv[1:]:',
      '    try:',
      '        res[m] = importlib.util.find_spec(m) is not None',
      '    except Exception:',
      '        res[m] = False',
      'print(json.dumps(res))',
    ].join('\n');
    const r = spawnSync(py, ['-c', probe, ...mods], { encoding: 'utf8', timeout: 20000 });
    let verdict = null;
    try { verdict = JSON.parse((r.stdout || '').trim()); } catch (e) { /* ignore */ }
    if (!verdict) {
      info('scripts', 'py-dep', `无法用 ${py} 实测 python 依赖（${mods.length} 个待验证）`,
        '设置 PYTHON 环境变量指向可用解释器可开启该项');
    } else {
      const bad = Object.entries(verdict).filter(([, okv]) => !okv).map(([k]) => k);
      if (bad.length) {
        fail('scripts', 'py-dep', `${bad.length} 个 python 模块既非本地文件也不可导入（会 ImportError）`,
          bad.map((m) => `${m}（被 ${candidates.get(m).join(', ')} 引用）`).join('; '));
      } else {
        ok('scripts', 'py-dep', `${mods.length} 个外部 python 模块全部可导入（${mods.join(', ')}）`);
      }
    }
  }

  // QUERY-2/5/7 守卫在位：防止「静默改查询条件展示格式」的回退
  const sqi = path.join(SCRIPTS, 'save_query_item.js');
  if (!fs.existsSync(sqi)) {
    warn('scripts', 'query-guard', 'save_query_item.js 缺失，无法校验查询条件守卫');
  } else {
    const t = fs.readFileSync(sqi, 'utf8');
    // 只扫代码行（剥离 //、*、/* 注释，避免命中「历史 bug 说明」里的旧实现文本）
    const code = t
      .split(/\r?\n/)
      .filter((l) => !/^\s*(\/\/|\*|\/\*)/.test(l))
      .join('\n');
    const regressed = [];
    // G1 静默注入 advancedSearchType（QUERY-5：会把报表页查询区改成「展开条件」）
    if (/advancedSearchType\s*=\s*['"]openCondition['"]/.test(code)) {
      regressed.push("G1 存在 advancedSearchType='openCondition' 硬编码注入（应为显式 --advanced-search-type 才写）");
    }
    // G2 硬编码 advancedSearch 调批量覆盖接口（QUERY-2：会把整表显示方式打回高级搜索）
    if (/updateQueryType\([^)]*['"]advancedSearch['"]/.test(code)) {
      regressed.push("G2 存在 updateQueryType(..., 'advancedSearch') 硬编码（批量覆盖整表显示方式）");
    }
    // G3 未点名就调批量覆盖（QUERY-2 的另一个放大器：query type 不带 --show-where 时静默改整表）
    if (/const sw\s*=\s*resolveShowWhere\([^)]*\)\s*\|\|\s*['"]advancedSearch['"]/.test(code)) {
      regressed.push('G3 query type 未传 --show-where 时仍默认 advancedSearch 批量覆盖（应只读回读）');
    }
    if (regressed.length) {
      fail('scripts', 'query-guard', `${regressed.length} 处查询条件守卫被回退`,
        regressed.join('; ') + '  → 见 pitfalls QUERY-2/QUERY-5');
    } else {
      const guards = [];
      if (/item\.defaultValueType\s*=\s*['"]default['"]/.test(t)) guards.push('三件套补缺');
      if (/!args\['skip-query-type'\]|args\['show-where'\]/.test(t)) guards.push('批量覆盖需点名');
      ok('scripts', 'query-guard', `查询条件守卫在位（${guards.join('/') || '无静默注入/无硬编码覆盖'}）`);
    }
    // G3 体检脚本存在（QUERY 全族判据的可执行入口）
    if (!fs.existsSync(path.join(SCRIPTS, 'verify_query_items.js'))) {
      warn('scripts', 'query-verify', 'verify_query_items.js 缺失 → edc-report verify query 不可用',
        '它是 QUERY-1~7 全部判据的可执行入口');
    } else {
      ok('scripts', 'query-verify', 'verify_query_items.js 在位（edc-report verify query）');
    }
  }

  // 语法检查（--full）
  if (full) {
    let bad = [];
    for (const f of files) {
      const r = spawnSync(process.execPath, ['--check', f], { encoding: 'utf8' });
      if (r.status !== 0) bad.push(path.basename(f));
    }
    if (bad.length) fail('scripts', 'syntax', `${bad.length} 个脚本语法错误`, bad.join(', '));
    else ok('scripts', 'syntax', `全部 ${files.length} 个 JS 语法检查通过`);
  } else {
    info('scripts', 'syntax', '语法检查已跳过（加 --full 开启）');
  }
}

// ───────────────────────── install ─────────────────────────
function shimDirs() {
  const out = [];
  // managed node：node.exe 所在目录常放 npm 全局 shim
  const execDir = path.dirname(process.execPath);
  if (fs.existsSync(execDir)) out.push(execDir);
  // AppData npm（Windows）
  if (process.env.APPDATA) {
    const p = path.join(process.env.APPDATA, 'npm');
    if (fs.existsSync(p)) out.push(p);
  }
  // Unix 常见全局前缀
  for (const p of ['/usr/local/bin', path.join(os.homedir(), '.npm-global', 'bin')]) {
    if (fs.existsSync(p)) out.push(p);
  }
  return [...new Set(out)];
}

function checkInstall(fix) {
  const dirs = shimDirs();
  const found = [];
  for (const d of dirs) {
    for (const name of ['edc-report', 'edc-report.cmd', 'edc-report.ps1']) {
      const p = path.join(d, name);
      if (fs.existsSync(p)) found.push(p);
    }
  }
  if (!found.length) {
    return warn('install', 'shim', '未找到全局 edc-report shim', '用 `npm link`（在 edc-report/ 目录）安装，或用绝对路径调用');
  }

  const broken = [];
  for (const p of found) {
    let txt = '';
    try { txt = fs.readFileSync(p, 'utf8'); } catch (e) { continue; }
    // 只判断含 edc-report 路径引用的 shim（.ps1/.cmd/.sh）
    const refs = [...txt.matchAll(/edc-report[\\/]([A-Za-z0-9_\-./\\]+\.js)/g)].map((m) => m[0].replace(/\\/g, '/'));
    for (const ref of refs) {
      const base = path.join(path.dirname(p), 'node_modules');
      const target = path.join(base, ref);
      if (!fs.existsSync(target)) broken.push({ shim: p, ref });
    }
  }

  if (broken.length) {
    if (fix) {
      for (const b of broken) {
        let txt = fs.readFileSync(b.shim, 'utf8');
        const before = txt;
        txt = txt.split('edc-report/bin/edc-report.js').join(ENTRY_REL)
                 .split('edc-report\\bin\\edc-report.js').join(ENTRY_REL.replace('/', '\\'));
        if (txt !== before) {
          fs.writeFileSync(b.shim, txt);
          fixCount++;
        }
      }
      ok('install', 'shim', `已改写 ${broken.length} 处悬空 shim 路径 → ${ENTRY_REL}（--fix）`);
    } else {
      fail('install', 'shim', `${broken.length} 处 shim 指向不存在的入口（全局 edc-report 会崩）`,
        broken.map((b) => `${path.basename(b.shim)} → ${b.ref}`).join('; ') + '  → 加 --fix 自动改写');
    }
  } else {
    ok('install', 'shim', `${found.length} 个 shim 入口指向均存在`);
  }

  // ENV-7 入口行尾
  const entry = path.join(PKG_DIR, 'edc-report.js');
  if (fs.existsSync(entry)) {
    const raw = fs.readFileSync(entry);
    if (raw.includes(Buffer.from('\r\n'))) {
      if (fix) {
        fs.writeFileSync(entry, raw.toString('utf8').replace(/\r\n/g, '\n'));
        fixCount++;
        ok('install', 'eol', '入口 CRLF → LF 已规范（--fix）');
      } else {
        fail('install', 'eol', `入口 ${ENTRY_REL} 含 CRLF（shebang 带 \\r 会找不到解释器；npm link 每次都会重新分叉）`,
          '加 --fix 统一为 LF');
      }
    } else {
      ok('install', 'eol', `入口 ${ENTRY_REL} 行尾为 LF`);
    }
  }

  ok('install', 'dirs', `shim 搜索目录：${dirs.map((d) => path.basename(d)).join(', ')}`);
}

// ───────────────────────── trees ─────────────────────────
// 与 _tree_tools.py 的镜像白名单一致：平台元数据不进一致性比对
const TREE_WHITELIST = new Set(['_user_meta.json', '_meta.json', '_skillhub_meta.json', '_icon.png']);

function snapshot(root) {
  const map = new Map();
  (function rec(dir, rel) {
    let ents = [];
    try { ents = fs.readdirSync(dir, { withFileTypes: true }); } catch (e) { return; }
    for (const e of ents) {
      if (e.name === '__pycache__' || e.name === 'node_modules' || e.name === '.git' || e.name === '.workbuddy') continue;
      if (TREE_WHITELIST.has(e.name)) continue;   // 平台元数据（含嵌套）：各副本本就不同
      const abs = path.join(dir, e.name);
      const r = rel ? `${rel}/${e.name}` : e.name;
      if (e.isDirectory()) rec(abs, r);
      else {
        try { map.set(r, fs.statSync(abs).size); } catch (err) { map.set(r, -1); }
      }
    }
  })(root, '');
  return map;
}

function checkTrees() {
  const peersRoot = path.join(os.homedir(), '.workbuddy', 'skills');
  const peers = PEER_NAMES
    .map((n) => path.join(peersRoot, n))
    .filter((p) => fs.existsSync(p) && path.resolve(p) !== path.resolve(ROOT));

  ok('trees', 'self', `当前树=${ROOT}`);

  if (!peers.length) {
    return info('trees', 'diff', '未发现同级安装副本（PEER 不存在，跳过一致性比对）');
  }

  const base = snapshot(ROOT);
  for (const p of peers) {
    const other = snapshot(p);
    const onlySelf = [...base.keys()].filter((k) => !other.has(k));
    const onlyPeer = [...other.keys()].filter((k) => !base.has(k));
    const sizeDiff = [...base.keys()].filter((k) => other.has(k) && other.get(k) !== base.get(k));
    const name = path.basename(p);
    if (!onlySelf.length && !onlyPeer.length && !sizeDiff.length) {
      ok('trees', 'diff', `${name} 与当前树一致（${base.size} 文件）`);
    } else {
      fail('trees', 'diff',
        `${name} 与当前树不一致：多出${onlySelf.length} / 缺少${onlyPeer.length} / 内容不同${sizeDiff.length}`,
        `修复：python _tree_tools.py mirror --dst "${p}"    （权威 = 当前树 ${ROOT}）`);
    }
  }
}

// ───────────────────────── perf ─────────────────────────
function checkPerf() {
  let R = null;
  try { R = require('./eb_render.js'); } catch (e) {
    return fail('perf', 'render-guard', `无法加载 eb_render.js：${e.message}`);
  }
  if (R.ENABLED) {
    warn('perf', 'render-guard', '渲染守卫当前为「放行」状态（EB_ALLOW_RENDER=1）',
      '全量交叉表渲染必然撞 5 万格上限且白烧 15~80s；不探测请 unset EB_ALLOW_RENDER');
  } else {
    ok('perf', 'render-guard', `渲染守卫生效：默认拒绝渲染，上限 ${R.CELL_LIMIT} 格，pageRowCount 封顶 ${R.capPageRowCount().safeMax}`);
  }
  info('perf', 'verify-policy', '验收用结构回读（verify bind / verify all），不要用渲染结果判定成败');
}

// ───────────────────────── main ─────────────────────────
function main() {
  const a = parseArgs(process.argv.slice(2));
  if (a.scope === 'help' || a.scope === '-h') {
    console.log(`Usage: node doctor.js [env|scripts|install|trees|perf|all] [--json] [--fix] [--full]

  env      凭证 / host 与 port / host 变量名 / CLI 版本 + 连通性探针
  scripts  scripts 目录 / require 解析 / 漏 port 扫描 / python 依赖 [/ 语法 --full]
  install  全局 shim 是否悬空 / 入口行尾（--fix 可修）
  trees    当前树 vs 同级安装副本 一致性
  perf     渲染守卫与 5 万格上限策略
  all      全部（默认）
`);
    return;
  }

  const scope = a.scope === 'all' || !['env', 'scripts', 'install', 'trees', 'perf'].includes(a.scope)
    ? 'all' : a.scope;

  if (scope === 'all' || scope === 'env') checkEnv();
  if (scope === 'all' || scope === 'scripts') checkScripts(a.full);
  if (scope === 'all' || scope === 'install') checkInstall(a.fix);
  if (scope === 'all' || scope === 'trees') checkTrees();
  if (scope === 'all' || scope === 'perf') checkPerf();

  // 连通性探针（env / all）
  (async () => {
    if (scope === 'all' || scope === 'env') {
      const r = await probeHost();
      if (r.skipped) info('env', 'probe', '凭证不可用，跳过连通性探针');
      else if (r.error) fail('env', 'probe', `连通性探针失败：${r.error}`,
        r.timedOut ? '典型症状 = 脚本漏 port 或网络不通（见 pitfalls ENV-1）' : '');
      else ok('env', 'probe', `连通性正常（${r.ms}ms, HTTP ${r.status}, port ${r.port}）`);
    }

    const ICON = { ok: '✅', warn: '⚠️ ', fail: '❌', info: 'ℹ️ ' };
    const fails = results.filter((r) => r.level === 'fail');
    const warns = results.filter((r) => r.level === 'warn');

    if (a.json) {
      console.log(JSON.stringify({
        ok: fails.length === 0,
        scope,
        fixed: fixCount,
        counts: { ok: results.filter((r) => r.level === 'ok').length, warn: warns.length, fail: fails.length },
        items: results,
      }, null, 2));
    } else {
      console.log(`\nedc-report doctor —— 环境体检（scope=${scope}${a.fix ? ', --fix' : ''}）\n`);
      let last = '';
      for (const r of results) {
        if (r.scope !== last) { console.log(`── ${r.scope} `.padEnd(60, '─')); last = r.scope; }
        console.log(`  ${ICON[r.level]} ${r.msg}`);
        if (r.hint) console.log(`      → ${r.hint}`);
      }
      console.log('');
      if (fixCount) console.log(`  已自动修复 ${fixCount} 处（--fix）\n`);
      if (!fails.length && !warns.length) console.log('  判定：全部通过 ✅\n');
      else if (!fails.length) console.log(`  判定：通过（${warns.length} 项告警）\n`);
      else console.log(`  判定：${fails.length} 项失败 / ${warns.length} 项告警 ❌\n`);
    }
    process.exitCode = fails.length ? 1 : 0;
  })();
}

if (require.main === module) main();

module.exports = { snapshot };
