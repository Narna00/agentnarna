"""Compact feedback model for iterative, proof-oriented validation.

This does not claim vulnerabilities and does not execute requests.  It turns a
response into a control fingerprint and suggests a *different* strategy family
for the next low-impact canary, preventing an agent from repeating payload
spelling changes while learning nothing.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Fingerprint:
    status: int | None
    control: str
    signature: str


def classify_output(text: str) -> Fingerprint:
    raw = text or ""
    lower = raw.lower()
    statuses = re.findall(r"(?:http/\d(?:\.\d)?\s+|status(?:code)?[\s:=]+)(\d{3})", lower)
    status = int(statuses[-1]) if statuses else None

    if status == 429 or "too many requests" in lower or "rate limit" in lower:
        control = "rate_limit"
    elif status == 403 or any(x in lower for x in ("access denied", "request blocked", "waf", "cloudflare ray")):
        control = "waf_or_acl"
    elif status in (301, 302, 303, 307, 308) and any(x in lower for x in ("login", "signin", "auth")):
        control = "auth_redirect"
    elif any(x in lower for x in ("html encoded", "escaped", "sanitiz", "csp", "content-security-policy")):
        control = "output_encoding"
    elif status and 500 <= status <= 599:
        control = "server_error"
    elif status and 200 <= status <= 299:
        control = "accepted"
    else:
        control = "unknown"

    normalized = re.sub(r"\b[0-9a-f]{12,}\b", "<id>", lower)
    normalized = re.sub(r"\d+", "<n>", normalized)
    signature = hashlib.sha256(normalized[:4000].encode("utf-8", "replace")).hexdigest()[:12]
    return Fingerprint(status=status, control=control, signature=signature)


def infer_strategy_family(command: str) -> str:
    lower = (command or "").lower()
    checks = (
        ("method-semantics", (" -x ", "--request", " options ", " head ")),
        ("path-normalization", ("%2f", "%2e", "/./", "/../")),
        ("header-routing", ("x-original", "x-rewrite", "x-forwarded", "x-http-method")),
        ("encoding-normalization", ("%25", "unicode", "urlencode", "base64")),
        ("browser-oracle", ("playwright", "selenium", "chrom", "dom_xss")),
        ("identity-differential", ("cookie:", "authorization:", "bearer ")),
        ("oob-callback", ("interactsh", "callback", "webhook")),
    )
    for family, needles in checks:
        if any(item in lower for item in needles):
            return family
    return "direct-replay"


def next_guidance(vuln_type: str, fp: Fingerprint, tried: set[str]) -> str:
    kind = (vuln_type or "").lower()
    if fp.control == "waf_or_acl":
        options = [
            "path-normalization: test whether proxy and origin normalize the same route",
            "method-semantics: compare safe verb handling and method-override behavior",
            "header-routing: test documented reverse-proxy routing headers with a harmless canary",
            "alternate-surface: find the same operation in API/mobile/GraphQL versions",
        ]
    elif "xss" in kind or fp.control == "output_encoding":
        options = [
            "context-map: identify HTML/attribute/JS/URL/DOM context before changing syntax",
            "browser-oracle: verify execution in a real browser with a harmless unique canary",
            "encoding-normalization: compare decoding stages without escalating impact",
            "alternate-sink: trace the same input into DOM, template, preview, export, or notification sinks",
            "policy-boundary: measure CSP/Trusted Types behavior and look for an allowed gadget",
        ]
    elif fp.control == "auth_redirect":
        options = [
            "identity-differential: compare anonymous, low-privilege A, and low-privilege B",
            "alternate-surface: test sibling API/mobile/GraphQL operations for inconsistent authorization",
            "workflow-order: replay the operation at a different authorized workflow step",
        ]
    elif fp.control == "rate_limit":
        options = [
            "limit-scope: determine whether the limit keys on account, session, endpoint, or operation",
            "alternate-surface: compare equivalent documented endpoints without increasing request volume",
        ]
    else:
        options = [
            "identity-differential: compare two controlled identities and an anonymous baseline",
            "alternate-surface: locate a sibling implementation of the same business operation",
            "workflow-order: vary valid state transitions and preconditions",
            "browser-oracle: use an execution oracle instead of reflection or status alone",
        ]

    for option in options:
        family = option.split(":", 1)[0]
        if family not in tried:
            return option
    return "exhausted: no untried low-impact strategy family remains; suppress the candidate"
