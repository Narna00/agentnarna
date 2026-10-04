"""The fork's primary product surface is the OpenCode workspace."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")


def test_readme_leads_with_opencode_before_optional_standalone():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    install = "./install.sh --agent opencode --project"
    assert install in text
    assert "opencode\n" in text
    assert text.index(install) < text.index("## Optional standalone CLI")
    assert "40+ hunting commands" in text
    assert "21 specialized skills" in text


@pytest.mark.skipif(BASH is None, reason="bash not available")
def test_opencode_shortcut_installs_the_complete_global_workspace(tmp_path):
    config = tmp_path / "opencode"
    env = {
        **os.environ,
        "OPENCODE_CONFIG_DIR": str(config),
        "AGENTNARNA_SKIP_DEPS": "1",
    }
    proc = subprocess.run(
        [BASH, str(ROOT / "install.sh"), "--opencode"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr
    assert "Start the full AgentNarna workspace" in proc.stdout
    assert sorted(p.name for p in (config / "skills").iterdir()) == sorted(
        p.name for p in (ROOT / "skills").iterdir()
    )
    assert sorted(p.name for p in (config / "commands").glob("*.md")) == sorted(
        p.name for p in (ROOT / "commands").glob("*.md")
    )
    assert sorted(p.name for p in (config / "agents").glob("*.md")) == sorted(
        p.name for p in (ROOT / "bughunter" / "agents").glob("*.md")
    )
