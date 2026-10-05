from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from bughunter.tools import capability_broker as broker


@pytest.fixture
def isolated_broker(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(broker, "HOME", tmp_path / "home")
    monkeypatch.setattr(broker, "POLICY_PATH", tmp_path / "home" / "tool-policy.json")
    monkeypatch.setattr(broker, "AUDIT_PATH", tmp_path / "home" / "tool-audit.jsonl")
    monkeypatch.setattr(broker, "WORDLIST_DIR", tmp_path / "wordlists")
    return tmp_path


def test_policy_is_opt_in_and_written_private(isolated_broker):
    assert broker.policy() == {"auto_install": False, "auto_launch": False}
    updated = broker.set_policy(auto_install=True, auto_launch=True)
    assert updated == {"auto_install": True, "auto_launch": True}
    assert broker.policy() == updated
    if os.name != "nt":
        assert broker.POLICY_PATH.stat().st_mode & 0o077 == 0


def test_unknown_online_result_cannot_be_installed(isolated_broker):
    with pytest.raises(ValueError, match="reviewed tool manifest"):
        broker.install_tool("random-search-result", approved=True)


def test_missing_tool_requires_saved_or_one_shot_approval(monkeypatch, isolated_broker):
    monkeypatch.setattr(broker, "executable", lambda tool: None)
    with pytest.raises(PermissionError, match="auto-install is disabled"):
        broker.install_tool("nuclei")


def test_go_install_resolves_exact_version_before_execution(monkeypatch, isolated_broker):
    installed = {"value": False}
    monkeypatch.setattr(broker, "executable", lambda tool: "/home/user/go/bin/nuclei" if installed["value"] else None)
    monkeypatch.setattr(broker.shutil, "which", lambda name: "/usr/bin/go" if name == "go" else None)
    monkeypatch.setattr(broker, "_resolve_go_version", lambda module: "v3.7.1")
    seen = []

    class Result:
        returncode = 0
        stdout = ""
        stderr = ""

    def fake_run(argv, **kwargs):
        seen.append(argv)
        installed["value"] = True
        return Result()

    monkeypatch.setattr(broker, "_run", fake_run)
    assert broker.install_tool("nuclei", approved=True)
    assert seen == [["go", "install", "github.com/projectdiscovery/nuclei/v3/cmd/nuclei@v3.7.1"]]
    assert "@latest" not in " ".join(seen[0])


def test_wordlists_are_commit_pinned_size_bounded_and_audited(monkeypatch, isolated_broker):
    payload = b"admin\napi\ninternal\n"

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self, limit):
            assert limit == 25 * 1024 * 1024 + 1
            return payload

    seen = []

    def fake_urlopen(url, timeout):
        seen.append(url)
        assert timeout == 60
        return Response()

    monkeypatch.setattr(broker.urllib.request, "urlopen", fake_urlopen)
    results = broker.sync_wordlists(approved=True)
    assert len(results) == len(broker.WORDLISTS)
    assert all(broker.SECLISTS_COMMIT in url for url in seen)
    assert all(item["sha256"] == hashlib.sha256(payload).hexdigest() for item in results)
    audit = [json.loads(line) for line in broker.AUDIT_PATH.read_text().splitlines()]
    assert audit[-1]["event"] == "wordlists"


def test_desktop_launch_requires_policy(monkeypatch, isolated_broker):
    monkeypatch.setattr(broker, "executable", lambda tool: "/opt/BurpSuite/burpsuite")
    with pytest.raises(PermissionError, match="auto-launch is disabled"):
        broker.launch_desktop("burp")


def test_desktop_launch_is_audited(monkeypatch, isolated_broker):
    class Process:
        pid = 4242

    monkeypatch.setattr(broker, "executable", lambda tool: "/opt/BurpSuite/burpsuite")
    monkeypatch.setattr(broker, "_running_pid", lambda pattern: None)
    monkeypatch.setattr(broker.subprocess, "Popen", lambda *args, **kwargs: Process())
    assert broker.launch_desktop("burp", approved=True) == 4242
    record = json.loads(broker.AUDIT_PATH.read_text().splitlines()[-1])
    assert record["event"] == "launch"
    assert record["tool"] == "burp"
