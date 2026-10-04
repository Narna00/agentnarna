# Security Policy

## Supported Versions

| Version | Supported |
|:---|:---|
| Latest `0.x` release | Yes |

## Reporting a Vulnerability

For a vulnerability in AgentNarna itself, do not open a public issue. Use
GitHub's **Report a vulnerability** flow on the repository Security tab to open
a private security advisory. If private reporting has not been enabled, contact
the repository owner privately without publishing exploit details.

Include the affected version, reproduction steps, impact, and a suggested fix
when available.

## Scope

This policy covers:

- `bughunter/tools/` — Python and shell research tools
- `bughunter/memory/` — hunt memory and evidence handling
- `install.sh` and `install_tools.sh` — installer scripts
- `demo/` — local demonstration services

Third-party programs tested with AgentNarna are out of scope for this policy;
report those only through their authorized disclosure or bug-bounty channel.

## Responsible Disclosure

The project follows coordinated disclosure and keeps reporters informed while a
fix is developed. Credit is provided in release notes unless anonymity is
requested.
