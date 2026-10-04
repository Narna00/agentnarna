"""Console-script entrypoints.

`agentnarna`        -> engine.main   (recon/hunt/verify/report dispatcher)
`agentnarna-agent`  -> agent.main    (autonomous session runner)

The old ``bughunter`` names remain compatibility aliases in pyproject.toml.

Both insert this package dir on sys.path first so the package's flat internal
imports (`from brain import ...`, `from tools.scope_checker import ...`) resolve.
"""
import os
import sys

_PKG = os.path.dirname(os.path.abspath(__file__))
if _PKG not in sys.path:
    sys.path.insert(0, _PKG)


def main():
    import engine
    engine.main()


def agent_main():
    import agent
    agent.main()


if __name__ == "__main__":
    main()
