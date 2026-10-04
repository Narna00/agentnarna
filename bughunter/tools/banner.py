"""Shared, quiet-by-default CLI banner for agentnarna."""
from __future__ import annotations

import os
import sys
from typing import Optional, Sequence, Tuple, Union

_LOGO = [
    "▄▀█ █▀▀ █▀▀ █▄░█ ▀█▀ █▄░█ ▄▀█ █▀█ █▄░█ ▄▀█",
    "█▀█ █▄█ ██▄ █░▀█ ░█░ █░▀█ █▀█ █▀▄ █░▀█ █▀█",
]
_WIDTH = max(len(line) for line in _LOGO)
_PINK, _CYAN, _WHITE, _DIM, _NC = (
    "\033[38;5;213m", "\033[38;5;51m", "\033[1;37m", "\033[2m", "\033[0m"
)

Step = Union[str, Tuple[str, str]]


def _center(text: str) -> str:
    return " " * max(0, (_WIDTH - len(text)) // 2) + text


def _enabled(stream) -> bool:
    return bool(
        getattr(stream, "isatty", lambda: False)()
        and not os.environ.get("NO_COLOR")
        and not os.environ.get("AGENTNARNA_NO_BANNER")
        and not os.environ.get("BBHUNT_NO_BANNER")
        and not os.environ.get("AGENTNARNA_BANNER_SHOWN")
        and not os.environ.get("BBHUNT_BANNER_SHOWN")
    )


def print_banner(subtitle: Optional[str] = None, target: Optional[str] = None,
                 steps: Optional[Sequence[Step]] = None, stream=None) -> None:
    stream = stream or sys.stdout
    if not _enabled(stream):
        return
    print(file=stream)
    print(f"  {_PINK}{_LOGO[0]}{_NC}", file=stream)
    print(f"  {_CYAN}{_LOGO[1]}{_NC}", file=stream)
    print(f"  {_DIM}{_center('lead → adapt → verify → report')}{_NC}", file=stream)
    if subtitle:
        print(f"  {_WHITE}{_center(subtitle)}{_NC}", file=stream)
    if target:
        print(f"  {_CYAN}{_center('target: ' + target)}{_NC}", file=stream)
    if steps:
        print(file=stream)
        for idx, value in enumerate(steps, 1):
            label, detail = value if isinstance(value, tuple) else (str(value), "")
            suffix = f"  {_DIM}{detail}{_NC}" if detail else ""
            print(f"  {_CYAN}{idx:02d}{_NC}  {_WHITE}{label}{_NC}{suffix}", file=stream)
    print(file=stream)
    os.environ["AGENTNARNA_BANNER_SHOWN"] = "1"
    os.environ["BBHUNT_BANNER_SHOWN"] = "1"


if __name__ == "__main__":
    print_banner(
        sys.argv[1] if len(sys.argv) > 1 else "evidence-first security research",
        target=sys.argv[2] if len(sys.argv) > 2 else None,
        steps=[
            ("Recon", "map the authorized surface"),
            ("Adapt", "learn from controls"),
            ("Verify", "fresh deterministic proof"),
            ("Report", "verified evidence only"),
        ],
    )
