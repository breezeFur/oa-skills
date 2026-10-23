# -*- coding: utf-8 -*-
"""
weaver_auth_headers.py
E10 统一凭证解析 + 浏览器对齐请求头构造（Python 版，与 scripts/eb_auth.js 语义一致）。

设计目标（针对「登录自动获取不了、又一直等待/反复调用」）：
  1. 命中即返回，**每个进程最多 spawn 一次 `e10-login`**（结果缓存）
  2. 凭证文件不存在 → **立刻**报错并给出「需要获取什么、去哪拿」的指引，不 spawn、不等待
  3. spawn 有**硬超时**（默认 8s，可用 EB_AUTH_TIMEOUT_MS 覆盖），超时即失败，不重试
  4. baseUrl 从本地 config.json 直读（明文），不消耗 CLI

解析顺序：
  ① 环境变量 EB_ETEAMSID / EB_HOST（推荐：source ./e10env.sh）
  ② ~/.e10-cli/profiles/<profile>/auth 不存在 → 立即抛 EbAuthError(LOGIN_HELP)
  ③ 读取 config.json 拿 baseUrl
  ④ 调一次 `e10-login status` 取 ETEAMSID（硬超时，仅一次）
  ⑤ 仍失败 → 抛 EbAuthError(LOGIN_HELP)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

E10_DIR = Path.home() / ".e10-cli"
PROFILES_DIR = E10_DIR / "profiles"
ACTIVE_PROFILE_FILE = E10_DIR / "profile"
CLI_TIMEOUT_S = int(os.environ.get("EB_AUTH_TIMEOUT_MS", "8000")) / 1000.0
NO_CLI = str(os.environ.get("EB_AUTH_NO_CLI", "")).lower() in ("1", "true", "yes")

LOGIN_HELP = """
════════════════════════════════════════════════════════════════
未获取到 E10 登录凭证（ETEAMSID）—— 请手动提供，本工具不会自动登录
════════════════════════════════════════════════════════════════

【需要获取的东西】浏览器里该平台的 ETEAMSID cookie 值

  1. 用浏览器打开平台地址并完成登录（能正常看到首页即可）
  2. 按 F12 → Application / 应用程序 → Storage → Cookies → 选中该站点
  3. 复制名为 ETEAMSID 的那一行 Value
     形如：PCACCOUNT_EXAMPLE_SESSION_VALUE
     （也可在 DevTools → Network 里任一请求的 Cookie 头中找 ETEAMSID=... ）

【拿到后二选一】

  A) 只对当前终端生效 —— 最快，零等待（推荐）
       export EB_ETEAMSID="<粘贴 cookie>"
       export EB_HOST="<平台地址，如 https://itsm.hongjing-wh.com:5001>"

  B) 持久写入 —— 之后所有脚本免配置
       e10-login set --eteamsid "<粘贴 cookie>" --base-url "<平台地址>"

【为什么不能自动登录】
  本环境 SSO 的 authorize 端点不发放授权码（302 → logintip?code=80015），
  `e10-login oidc` 的本地回调永远等不到 → 会一直卡住。所以禁止用 oidc 兜底。

【安全】cookie 等同账号会话，不要写进代码、不要提交仓库。
════════════════════════════════════════════════════════════════
"""


class EbAuthError(RuntimeError):
    """凭证缺失/失效。message 已含完整获取指引（.help）。"""

    def __init__(self, message: str, reason: str = "unknown", help_text: str = LOGIN_HELP):
        super().__init__(message)
        self.reason = reason
        self.help = help_text


# ── 本地 profile / config（明文，零 spawn） ──────────────────

def active_profile() -> str:
    env = (os.environ.get("E10_PROFILE") or "").strip()
    if env:
        return env
    try:
        name = ACTIVE_PROFILE_FILE.read_text(encoding="utf-8").strip()
        if name:
            return name
    except OSError:
        pass
    return "default"


def profile_dir(profile: str | None = None) -> Path:
    return PROFILES_DIR / (profile or active_profile())


def read_local_config(profile: str | None = None) -> dict:
    """本地 config.json 是明文，可直读 baseUrl / tenantKey（不消耗 CLI）。"""
    try:
        j = json.loads((profile_dir(profile) / "config.json").read_text(encoding="utf-8"))
        return {
            "baseUrl": str(j.get("baseUrl") or j.get("passportUrl") or "").rstrip("/"),
            "tenantKey": str(j.get("tenantKey") or ""),
        }
    except (OSError, ValueError):
        return {"baseUrl": "", "tenantKey": ""}


def auth_file_exists(profile: str | None = None) -> bool:
    if (profile_dir(profile) / "auth").exists():
        return True
    return (E10_DIR / "auth").exists()


# ── 解析 ────────────────────────────────────────────────────

_CACHE: dict | None = None


def _from_env() -> dict | None:
    sid = (os.environ.get("EB_ETEAMSID") or os.environ.get("ETEAMSID") or "").strip()
    host = (
        os.environ.get("EB_HOST")
        or os.environ.get("E10_BASE_URL")
        or os.environ.get("E10_HOST")
        or ""
    ).rstrip("/")
    if not sid:
        return None
    return {"eteams_id": sid, "host": host, "source": "env"}


def _from_cli() -> dict:
    """只调一次 `e10-login status`，带硬超时；失败即返回 error，绝不重试。"""
    if NO_CLI:
        return {"error": "已通过 EB_AUTH_NO_CLI 禁用 CLI"}
    try:
        proc = subprocess.run(
            "e10-login status",
            shell=True,
            capture_output=True,
            text=True,
            timeout=CLI_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return {"error": f"e10-login 超时（>{int(CLI_TIMEOUT_S * 1000)}ms）"}
    except OSError as exc:
        return {"error": f"调用 e10-login 失败：{exc}"}

    out = (proc.stdout or "") + (proc.stderr or "")
    marker = "ETEAMSID:"
    if marker not in out:
        return {"error": "e10-login status 未返回 ETEAMSID（未登录或凭证已过期）"}
    sid = out.split(marker, 1)[1].strip().split()[0]
    host = ""
    if "baseUrl:" in out:
        host = out.split("baseUrl:", 1)[1].strip().split()[0].rstrip("/")
    return {"eteams_id": sid, "host": host, "source": "e10-login"}


def resolve_auth(profile: str | None = None) -> dict:
    """
    解析凭证（进程内缓存）。
    返回 {"eteams_id": str, "host": str, "source": str}
    缺凭证时抛 EbAuthError（其 .help 含完整获取指引）。
    """
    global _CACHE
    if _CACHE is not None:
        return _CACHE

    env = _from_env()
    if env:
        if not env["host"]:
            env["host"] = read_local_config(profile)["baseUrl"]
        if not env["host"]:
            raise EbAuthError("EB_ETEAMSID 已设置，但缺少平台地址 EB_HOST。", reason="no_host")
        _CACHE = env
        return _CACHE

    if not auth_file_exists(profile):
        raise EbAuthError(
            f"未找到登录凭证文件（{profile_dir(profile) / 'auth'} 不存在）。",
            reason="no_auth_file",
        )

    local = read_local_config(profile)
    cli = _from_cli()
    if cli.get("eteams_id"):
        host = cli.get("host") or local["baseUrl"]
        if not host:
            raise EbAuthError("已取到 ETEAMSID，但无法确定平台地址（config.json 缺 baseUrl）。", reason="no_host")
        _CACHE = {"eteams_id": cli["eteams_id"], "host": host, "source": cli["source"]}
        return _CACHE

    raise EbAuthError(
        f"读取登录凭证失败：{cli.get('error') or '未知原因'}",
        reason=cli.get("error") or "cli_failed",
    )


def auth_status(profile: str | None = None) -> dict:
    """不抛异常的状态查询，供门禁脚本直接打印。"""
    try:
        r = resolve_auth(profile)
        sid = r["eteams_id"]
        return {
            "ok": True,
            "source": r["source"],
            "eteamsIdMasked": (sid[:10] + f"…(len={len(sid)})") if len(sid) > 16 else "***",
            "host": r["host"],
            "profile": profile or active_profile(),
        }
    except EbAuthError as exc:
        return {
            "ok": False,
            "reason": exc.reason,
            "profile": profile or active_profile(),
            "authFile": str(profile_dir(profile) / "auth"),
            "authFileExists": auth_file_exists(profile),
            "message": str(exc),
            "help": exc.help,
        }


def require_auth_or_exit(profile: str | None = None) -> dict:
    """缺凭证时打印指引并 exit(2)；有凭证则返回状态。"""
    st = auth_status(profile)
    if st["ok"]:
        return st
    print(st["message"], file=sys.stderr)
    print(st["help"], file=sys.stderr)
    sys.exit(2)


# ── 浏览器对齐请求头 ────────────────────────────────────────

def build_auth_headers(
    host: str,
    eteamsid: str,
    cookie: str = "",
    agent_type: str = "WorkBuddy",
    ebbusinessid: str = "",
    referer_suffix: str = "",
) -> dict:
    """
    构造与浏览器一致的表单提交请求头。
    cookie 为空时回退为 `langType=zh_CN; LOGIN_TYPE=pc_account; ETEAMSID=<id>`。
    """
    base = (host or "").rstrip("/")
    sid = str(eteamsid or "").strip()
    if not sid:
        raise EbAuthError("build_auth_headers 需要 eteamsid。", reason="no_eteamsid")

    cookie_str = str(cookie or "").strip()
    if not cookie_str or "ETEAMSID=" not in cookie_str:
        cookie_str = f"langType=zh_CN; LOGIN_TYPE=pc_account; ETEAMSID={sid}"

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "eteamsid": sid,
        "Cookie": cookie_str,
        "Origin": base,
        "User-Agent": f"Mozilla/5.0 AgentType={agent_type},IsAgent=true",
        "timezoneoffset": "28800000",
    }
    if base:
        headers["Referer"] = f"{base}{referer_suffix}" if referer_suffix else base
    if ebbusinessid:
        headers["ebBusinessId"] = str(ebbusinessid)
        headers["ebbusinessid"] = str(ebbusinessid)
    return headers


if __name__ == "__main__":
    st = auth_status()
    print(json.dumps(st, ensure_ascii=False, indent=2))
    sys.exit(0 if st["ok"] else 2)
