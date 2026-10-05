"""Launch the complete AgentNarna terminal workspace.

AgentNarna owns the user-facing command and product identity.  The interactive
terminal renderer is supplied by a compatible OpenCode runtime, in the same way
an application can embed a browser engine without asking users to launch the
browser themselves.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import NoReturn, Sequence


PACKAGE_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = PACKAGE_DIR.parent


class WorkspaceRuntimeError(RuntimeError):
    """Raised when the interactive runtime cannot be started."""


def workspace_root() -> Path:
    override = os.environ.get("AGENTNARNA_WORKSPACE")
    return Path(override).expanduser().resolve() if override else REPOSITORY_ROOT


def runtime_path() -> str:
    override = os.environ.get("AGENTNARNA_RUNTIME")
    resolved = shutil.which(override or "opencode")
    if not resolved:
        raise WorkspaceRuntimeError(
            "AgentNarna's interactive runtime is not installed. Install the "
            "runtime prerequisite from https://opencode.ai/docs and rerun "
            "./install.sh. You will still launch the product with `agentnarna`."
        )
    return resolved


def launch_environment(base: dict[str, str] | None = None) -> dict[str, str]:
    """Return an environment that applies AgentNarna's visual identity.

    Newer runtime releases accept inline CLI settings. Preserve unrelated user
    preferences while making the checked-in AgentNarna theme authoritative.
    """

    env = dict(base if base is not None else os.environ)
    raw = env.get("OPENCODE_CLI_CONFIG_CONTENT", "")
    try:
        settings = json.loads(raw) if raw else {}
    except (TypeError, json.JSONDecodeError):
        settings = {}
    if not isinstance(settings, dict):
        settings = {}
    settings["theme"] = {"name": "agentnarna", "mode": "dark"}
    settings.setdefault("animations", True)
    settings.setdefault("cursor", {"style": "block", "blinking": True})
    env["OPENCODE_CLI_CONFIG_CONTENT"] = json.dumps(settings, separators=(",", ":"))
    env["AGENTNARNA_PRODUCT"] = "AgentNarna"
    env.setdefault("COLORTERM", "truecolor")
    return env


def launch(arguments: Sequence[str] = ()) -> NoReturn:
    """Replace this process with the complete AgentNarna TUI."""

    root = workspace_root()
    if not (root / "AGENTS.md").is_file():
        raise WorkspaceRuntimeError(
            f"AgentNarna workspace is incomplete at {root}. Clone the full "
            "repository or set AGENTNARNA_WORKSPACE to its path."
        )
    if not (root / ".opencode" / "skills").is_dir():
        raise WorkspaceRuntimeError(
            "AgentNarna workspace assets are not installed. Run ./install.sh "
            "from the repository, then launch `agentnarna` again."
        )

    runtime = runtime_path()
    env = launch_environment()
    os.chdir(root)
    # Keep the runtime's real argv[0] for compatibility with packaged
    # executables. The shell command, theme, and workspace remain product-owned.
    os.execvpe(runtime, [runtime, *arguments], env)
    raise AssertionError("os.execvpe returned unexpectedly")
