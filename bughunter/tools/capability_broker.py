#!/usr/bin/env python3
"""Guarded tool, wordlist, and desktop-proxy lifecycle for AgentNarna.

Online discovery is deliberately separated from execution. Search results are
untrusted candidates; unattended installation is limited to this reviewed
manifest and must be enabled once by the operator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path


HOME = Path(os.environ.get("AGENTNARNA_HOME", Path.home() / ".agentnarna")).expanduser()
POLICY_PATH = HOME / "tool-policy.json"
AUDIT_PATH = HOME / "tool-audit.jsonl"
BIN_DIR = Path.home() / ".local" / "bin"
WORDLIST_DIR = Path(os.environ.get("WORDLIST_BASE", Path.home() / "wordlists")).expanduser()
SECLISTS_COMMIT = "7b0924570dc4cd18d4a34bffcb695bf02bb608e6"


@dataclass(frozen=True)
class Tool:
    name: str
    executables: tuple[str, ...]
    source: str
    capabilities: tuple[str, ...]
    go_module: str = ""
    go_package: str = ""
    pipx_package: str = ""


TOOLS = {
    item.name: item for item in (
        Tool("subfinder", ("subfinder",), "https://github.com/projectdiscovery/subfinder", ("recon", "subdomains"), "github.com/projectdiscovery/subfinder/v2", "github.com/projectdiscovery/subfinder/v2/cmd/subfinder"),
        Tool("httpx", ("httpx",), "https://github.com/projectdiscovery/httpx", ("recon", "probe"), "github.com/projectdiscovery/httpx", "github.com/projectdiscovery/httpx/cmd/httpx"),
        Tool("nuclei", ("nuclei",), "https://github.com/projectdiscovery/nuclei", ("scan", "cve"), "github.com/projectdiscovery/nuclei/v3", "github.com/projectdiscovery/nuclei/v3/cmd/nuclei"),
        Tool("katana", ("katana",), "https://github.com/projectdiscovery/katana", ("recon", "crawl"), "github.com/projectdiscovery/katana", "github.com/projectdiscovery/katana/cmd/katana"),
        Tool("naabu", ("naabu",), "https://github.com/projectdiscovery/naabu", ("ports", "recon"), "github.com/projectdiscovery/naabu/v2", "github.com/projectdiscovery/naabu/v2/cmd/naabu"),
        Tool("ffuf", ("ffuf",), "https://github.com/ffuf/ffuf", ("fuzz", "content"), "github.com/ffuf/ffuf/v2", "github.com/ffuf/ffuf/v2"),
        Tool("dalfox", ("dalfox",), "https://github.com/hahwul/dalfox", ("xss",), "github.com/hahwul/dalfox/v2", "github.com/hahwul/dalfox/v2"),
        Tool("gau", ("gau",), "https://github.com/lc/gau", ("recon", "urls"), "github.com/lc/gau/v2", "github.com/lc/gau/v2/cmd/gau"),
        Tool("interactsh-client", ("interactsh-client",), "https://github.com/projectdiscovery/interactsh", ("oob", "ssrf", "xxe"), "github.com/projectdiscovery/interactsh", "github.com/projectdiscovery/interactsh/cmd/interactsh-client"),
        Tool("arjun", ("arjun",), "https://github.com/s0md3v/Arjun", ("params",), pipx_package="arjun"),
        Tool("sqlmap", ("sqlmap",), "https://github.com/sqlmapproject/sqlmap", ("sqli",), pipx_package="sqlmap"),
        Tool("semgrep", ("semgrep",), "https://github.com/semgrep/semgrep", ("sast", "source"), pipx_package="semgrep"),
        Tool("burp", ("burpsuite", "burp"), "https://portswigger.net/burp", ("proxy", "browser", "manual")),
        Tool("caido", ("caido", "Caido"), "https://caido.io", ("proxy", "browser", "manual")),
    )
}

CAPABILITIES = {
    "recon": ("subfinder", "httpx", "katana", "gau"),
    "web-scan": ("nuclei", "ffuf"),
    "xss": ("dalfox",),
    "sqli": ("sqlmap",),
    "params": ("arjun",),
    "ports": ("naabu",),
    "oob": ("interactsh-client",),
    "sast": ("semgrep",),
}

WORDLISTS = {
    "common.txt": "Discovery/Web-Content/common.txt",
    "raft-medium-dirs.txt": "Discovery/Web-Content/raft-medium-directories.txt",
    "api-endpoints.txt": "Discovery/Web-Content/api/api-endpoints.txt",
    "params.txt": "Discovery/Web-Content/burp-parameter-names.txt",
}


def _secure_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.parent.chmod(0o700)
    except OSError:
        pass
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
    try:
        path.chmod(0o600)
    except OSError:
        pass


def policy() -> dict:
    defaults = {"auto_install": False, "auto_launch": False}
    try:
        loaded = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
        if isinstance(loaded, dict):
            defaults.update({k: bool(loaded[k]) for k in defaults if k in loaded})
    except (OSError, ValueError, TypeError):
        pass
    return defaults


def set_policy(*, auto_install: bool | None = None, auto_launch: bool | None = None) -> dict:
    current = policy()
    if auto_install is not None:
        current["auto_install"] = auto_install
    if auto_launch is not None:
        current["auto_launch"] = auto_launch
    _secure_json(POLICY_PATH, current)
    _audit("policy", current)
    return current


def _audit(event: str, detail: dict) -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {"time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "event": event, **detail}
    with AUDIT_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")
    try:
        AUDIT_PATH.chmod(0o600)
    except OSError:
        pass


def executable(tool: Tool) -> str | None:
    for name in tool.executables:
        found = shutil.which(name)
        if found:
            return found
        local = BIN_DIR / name
        if local.is_file() and os.access(local, os.X_OK):
            return str(local)
        go_bin = Path.home() / "go" / "bin" / name
        if go_bin.is_file() and os.access(go_bin, os.X_OK):
            return str(go_bin)
    return None


def _run(argv: list[str], *, timeout: int = 900, env: dict | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(argv, text=True, capture_output=True, timeout=timeout, env=env, shell=False)


def _resolve_go_version(module: str) -> str:
    result = _run(["go", "list", "-m", "-json", f"{module}@latest"], timeout=90)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"could not resolve {module}")
    value = json.loads(result.stdout).get("Version")
    if not value:
        raise RuntimeError(f"Go did not return a version for {module}")
    return str(value)


def install_tool(name: str, *, approved: bool = False) -> bool:
    tool = TOOLS.get(name.lower())
    if not tool:
        raise ValueError(f"'{name}' is not in AgentNarna's reviewed tool manifest")
    if executable(tool):
        return True
    if not (approved or policy()["auto_install"]):
        raise PermissionError("auto-install is disabled; run: agentnarna tools policy --auto-install on")

    if tool.go_package:
        if not shutil.which("go"):
            raise RuntimeError("Go is required for this tool; install Go, then retry")
        version = _resolve_go_version(tool.go_module)
        argv = ["go", "install", f"{tool.go_package}@{version}"]
        install_id = version
    elif tool.pipx_package:
        if not shutil.which("pipx"):
            raise RuntimeError("pipx is required for this tool; install pipx, then retry")
        argv = ["pipx", "install", tool.pipx_package]
        install_id = "pypi-current"
    else:
        raise RuntimeError(f"{name} requires a licensed/desktop installation from {tool.source}")

    result = _run(argv)
    _audit("install", {"tool": tool.name, "source": tool.source, "version": install_id,
                       "argv": argv, "returncode": result.returncode})
    if result.returncode != 0 and "already" not in (result.stderr + result.stdout).lower():
        raise RuntimeError((result.stderr or result.stdout).strip()[-1000:])
    if not executable(tool):
        raise RuntimeError(f"{tool.name} installation completed but its executable is not on PATH")
    return True


def ensure_capability(name: str, *, approved: bool = False) -> dict[str, bool]:
    names = CAPABILITIES.get(name.lower())
    if not names:
        raise ValueError(f"unknown capability '{name}'")
    return {tool: install_tool(tool, approved=approved) for tool in names}


def sync_wordlists(*, approved: bool = False) -> list[dict]:
    if not (approved or policy()["auto_install"]):
        raise PermissionError("wordlist download is disabled; enable auto-install or pass --approve")
    WORDLIST_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for filename, relative in WORDLISTS.items():
        url = f"https://raw.githubusercontent.com/danielmiessler/SecLists/{SECLISTS_COMMIT}/{relative}"
        destination = WORDLIST_DIR / filename
        with urllib.request.urlopen(url, timeout=60) as response:  # nosec B310 - fixed HTTPS host and commit
            data = response.read(25 * 1024 * 1024 + 1)
        if len(data) > 25 * 1024 * 1024:
            raise RuntimeError(f"refused oversized wordlist: {filename}")
        digest = hashlib.sha256(data).hexdigest()
        destination.write_bytes(data)
        results.append({"name": filename, "path": str(destination), "sha256": digest, "source": url})
    _audit("wordlists", {"commit": SECLISTS_COMMIT, "files": results})
    return results


def _running_pid(pattern: str) -> int | None:
    if os.name == "nt" or not shutil.which("pgrep"):
        return None
    result = _run(["pgrep", "-n", "-f", pattern], timeout=10)
    if result.returncode == 0 and result.stdout.strip().isdigit():
        return int(result.stdout.strip())
    return None


def launch_desktop(name: str, *, approved: bool = False) -> int:
    if name not in {"burp", "caido"}:
        raise ValueError("desktop launch supports burp or caido")
    if not (approved or policy()["auto_launch"]):
        raise PermissionError("auto-launch is disabled; run: agentnarna tools policy --auto-launch on")
    tool = TOOLS[name]
    command_override = os.environ.get(f"AGENTNARNA_{name.upper()}_COMMAND")
    if command_override:
        argv = shlex.split(command_override)
    else:
        resolved = executable(tool)
        if resolved:
            argv = [resolved]
        elif name == "burp" and os.environ.get("BURP_JAR") and shutil.which("java"):
            argv = [shutil.which("java") or "java", "-jar", os.environ["BURP_JAR"]]
        else:
            raise RuntimeError(f"{name} is not installed; use the official source: {tool.source}")
    existing = _running_pid(Path(argv[0]).name)
    if existing:
        _audit("reuse", {"tool": name, "pid": existing})
        return existing
    proc = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL, start_new_session=True, close_fds=True)
    _audit("launch", {"tool": name, "argv": argv, "pid": proc.pid})
    return proc.pid


def discover(query: str) -> list[dict]:
    """Search GitHub metadata for candidates; never install the results."""
    encoded = urllib.parse.urlencode({"q": f"{query} security tool", "sort": "stars", "order": "desc", "per_page": 5})
    request = urllib.request.Request(
        f"https://api.github.com/search/repositories?{encoded}",
        headers={"Accept": "application/vnd.github+json", "User-Agent": "agentnarna-tool-discovery/1"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310 - fixed GitHub API host
        payload = json.load(response)
    return [{"name": item.get("full_name"), "url": item.get("html_url"),
             "description": item.get("description"), "stars": item.get("stargazers_count"),
             "updated": item.get("updated_at"), "archived": item.get("archived")}
            for item in payload.get("items", [])]


def status() -> dict:
    return {name: {"installed": bool(executable(tool)), "path": executable(tool),
                   "capabilities": tool.capabilities, "source": tool.source}
            for name, tool in TOOLS.items()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="AgentNarna capability broker")
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("status")
    p_policy = sub.add_parser("policy")
    p_policy.add_argument("--auto-install", choices=("on", "off"))
    p_policy.add_argument("--auto-launch", choices=("on", "off"))
    p_ensure = sub.add_parser("ensure")
    group = p_ensure.add_mutually_exclusive_group(required=True)
    group.add_argument("--tool")
    group.add_argument("--capability")
    p_ensure.add_argument("--approve", action="store_true")
    p_words = sub.add_parser("wordlists")
    p_words.add_argument("--approve", action="store_true")
    p_launch = sub.add_parser("launch")
    p_launch.add_argument("desktop", choices=("burp", "caido"))
    p_launch.add_argument("--approve", action="store_true")
    p_discover = sub.add_parser("discover")
    p_discover.add_argument("query")
    args = parser.parse_args(argv)
    try:
        if args.action == "status":
            result = {"policy": policy(), "tools": status()}
        elif args.action == "policy":
            result = set_policy(auto_install=None if args.auto_install is None else args.auto_install == "on",
                                auto_launch=None if args.auto_launch is None else args.auto_launch == "on")
        elif args.action == "ensure":
            result = ({args.tool: install_tool(args.tool, approved=args.approve)} if args.tool
                      else ensure_capability(args.capability, approved=args.approve))
        elif args.action == "wordlists":
            result = sync_wordlists(approved=args.approve)
        elif args.action == "launch":
            result = {"tool": args.desktop, "pid": launch_desktop(args.desktop, approved=args.approve)}
        else:
            result = {"candidates": discover(args.query), "installable": False,
                      "note": "Search results require review and manifest admission before installation."}
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (ValueError, PermissionError, RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
