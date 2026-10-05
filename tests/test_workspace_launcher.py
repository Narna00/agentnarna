from __future__ import annotations

import json
from pathlib import Path

import pytest

from bughunter import workspace


def test_launch_environment_applies_brand_and_preserves_preferences():
    env = workspace.launch_environment(
        {"OPENCODE_CLI_CONFIG_CONTENT": '{"mouse":false,"scroll":{"speed":5}}'}
    )
    settings = json.loads(env["OPENCODE_CLI_CONFIG_CONTENT"])
    assert settings["theme"] == {"name": "agentnarna", "mode": "dark"}
    assert settings["mouse"] is False
    assert settings["scroll"] == {"speed": 5}
    assert env["AGENTNARNA_PRODUCT"] == "AgentNarna"


def test_agentnarna_launches_complete_workspace(monkeypatch, tmp_path: Path):
    (tmp_path / "AGENTS.md").write_text("# AgentNarna", encoding="utf-8")
    (tmp_path / ".opencode" / "skills").mkdir(parents=True)
    monkeypatch.setenv("AGENTNARNA_WORKSPACE", str(tmp_path))
    monkeypatch.setattr(workspace.shutil, "which", lambda command: "/runtime/opencode")

    captured = {}

    def fake_exec(path, argv, env):
        captured.update(path=path, argv=argv, env=env, cwd=Path.cwd())
        raise RuntimeError("exec intercepted")

    monkeypatch.setattr(workspace.os, "execvpe", fake_exec)
    previous = Path.cwd()
    try:
        with pytest.raises(RuntimeError, match="exec intercepted"):
            workspace.launch(["--continue"])
    finally:
        workspace.os.chdir(previous)

    assert captured["path"] == "/runtime/opencode"
    assert captured["argv"] == ["/runtime/opencode", "--continue"]
    assert captured["cwd"] == tmp_path
    assert json.loads(captured["env"]["OPENCODE_CLI_CONFIG_CONTENT"])["theme"]["name"] == "agentnarna"


def test_theme_is_valid_and_complete():
    path = Path(__file__).resolve().parents[1] / "ui" / "themes" / "agentnarna.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    required = {"primary", "background", "text", "success", "warning", "error"}
    assert required <= payload["theme"].keys()
