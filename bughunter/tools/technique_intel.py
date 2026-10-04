#!/usr/bin/env python3
"""Ingest public security research into a compact, source-linked intel ledger.

Connections:
* Medium: public RSS/Atom feeds (no account or token required).
* X: official recent-search API using ``X_BEARER_TOKEN``.
* Other sites: explicit article URLs supplied by the operator.

Fetched text is untrusted research material. It is never executed, never copied
directly into a command, and never promoted to a finding. The hunt agent uses it
only to generate hypotheses that still require in-scope deterministic proof.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from tools.safe_http import _is_blocked_redirect_target, safe_urlopen

_CTX = ssl.create_default_context()
_MAX_BODY = 1_000_000
_STOP_TERMS = {
    "about", "after", "against", "before", "finding", "from", "have",
    "https", "into", "scanner", "target", "that", "their", "this", "with",
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clean_markup(value: str, limit: int = 1200) -> str:
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", value or "", flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()[:limit]


def _fetch(url: str, *, headers: dict[str, str] | None = None, timeout: int = 15) -> bytes:
    host = urllib.parse.urlparse(url).hostname
    if _is_blocked_redirect_target(host):
        raise ValueError(f"refusing private/loopback research source: {host!r}")
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "agentnarna-intel/1.0", **(headers or {})},
    )
    with safe_urlopen(request, timeout=timeout, context=_CTX) as response:
        return response.read(_MAX_BODY + 1)[:_MAX_BODY]


def _hash(source: str, url: str, title: str) -> str:
    return hashlib.sha256(f"{source}\0{url}\0{title}".encode("utf-8", "replace")).hexdigest()[:20]


def default_ledger_path() -> Path:
    """Return a stable ledger path for source checkouts and installed wheels."""
    explicit = os.environ.get("AGENTNARNA_INTEL_PATH")
    if explicit:
        return Path(explicit).expanduser()
    data_home = os.environ.get("AGENTNARNA_HOME") or os.environ.get("BUGHUNTER_HOME")
    if data_home:
        return Path(data_home).expanduser() / "hunt-memory" / "technique-intel.jsonl"
    checkout = Path(__file__).resolve().parents[2]
    if (checkout / "pyproject.toml").is_file():
        return checkout / "hunt-memory" / "technique-intel.jsonl"
    return Path.home() / ".agentnarna" / "hunt-memory" / "technique-intel.jsonl"


def _item(source: str, url: str, title: str, summary: str, *,
          published: str = "", tags: list[str] | None = None) -> dict:
    return {
        "schema": "agentnarna-intel/1",
        "id": _hash(source, url, title),
        "ingested_at": _now(),
        "source": source,
        "url": url,
        "title": _clean_markup(title, 240),
        "summary": _clean_markup(summary),
        "published": published,
        "tags": sorted(set(tags or [])),
        "trust": "untrusted_external_research",
        "use": "hypothesis_only_requires_live_verification",
    }


def fetch_feed(url: str, *, source: str = "medium") -> list[dict]:
    root = ET.fromstring(_fetch(url))
    out: list[dict] = []

    # RSS items and Atom entries use different namespaces; local-name matching
    # keeps this dependency-free and works for Medium feeds.
    entries = [node for node in root.iter() if node.tag.split("}")[-1] in {"item", "entry"}]
    for entry in entries[:30]:
        values: dict[str, list[str]] = {}
        link = ""
        for child in list(entry):
            name = child.tag.split("}")[-1]
            text = "".join(child.itertext()).strip()
            values.setdefault(name, []).append(text)
            if name == "link":
                link = child.attrib.get("href") or text or link
        title = (values.get("title") or [""])[0]
        summary = (values.get("description") or values.get("summary") or values.get("content") or [""])[0]
        published = (values.get("pubDate") or values.get("published") or values.get("updated") or [""])[0]
        tags = [value for value in values.get("category", []) if value]
        if title and link:
            out.append(_item(source, link, title, summary, published=published, tags=tags))
    return out


def medium_tag(tag: str) -> list[dict]:
    safe_tag = urllib.parse.quote(tag.strip().lower())
    return fetch_feed(f"https://medium.com/feed/tag/{safe_tag}", source="medium")


def fetch_article(url: str) -> list[dict]:
    raw = _fetch(url).decode("utf-8", "replace")
    title_match = re.search(r"<title[^>]*>(.*?)</title>", raw, flags=re.I | re.S)
    title = _clean_markup(title_match.group(1) if title_match else url, 240)
    return [_item("web", url, title, raw)]


def x_recent(query: str, *, limit: int = 25, bearer: str | None = None) -> list[dict]:
    token = bearer or os.environ.get("X_BEARER_TOKEN")
    if not token:
        raise RuntimeError("X recent search requires X_BEARER_TOKEN from an X developer project")
    params = urllib.parse.urlencode({
        "query": query,
        "max_results": max(10, min(limit, 100)),
        "tweet.fields": "created_at,author_id,lang",
    })
    data = json.loads(_fetch(
        f"https://api.x.com/2/tweets/search/recent?{params}",
        headers={"Authorization": f"Bearer {token}"},
    ).decode("utf-8", "replace"))
    out = []
    for post in data.get("data") or []:
        post_id = str(post.get("id") or "")
        text = str(post.get("text") or "")
        if not post_id or not text:
            continue
        url = f"https://x.com/i/web/status/{post_id}"
        out.append(_item(
            "x", url, text[:120], text,
            published=str(post.get("created_at") or ""),
            tags=["x-search", query],
        ))
    return out


def append_ledger(path: str | Path, items: list[dict]) -> tuple[int, int]:
    dest = Path(path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    known: set[str] = set()
    if dest.exists():
        for line in dest.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                known.add(json.loads(line).get("id"))
            except (ValueError, TypeError):
                continue
    added = 0
    with dest.open("a", encoding="utf-8", newline="\n") as handle:
        for item in items:
            if item["id"] in known:
                continue
            handle.write(json.dumps(item, ensure_ascii=False) + "\n")
            known.add(item["id"])
            added += 1
    return added, len(items) - added


def relevant_items(path: str | Path, query: str, *, limit: int = 3) -> list[dict]:
    """Return a tiny relevance-ranked set of hypothesis-only technique cards."""
    source = Path(path)
    if not source.is_file() or limit <= 0:
        return []
    query_terms = {
        term for term in re.findall(r"[a-z0-9_-]{3,}", query.lower())
        if term not in _STOP_TERMS
    }
    if not query_terms:
        return []
    ranked: list[tuple[int, dict]] = []
    for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            item = json.loads(line)
        except (TypeError, ValueError):
            continue
        if not isinstance(item, dict):
            continue
        if item.get("use") != "hypothesis_only_requires_live_verification":
            continue
        title = str(item.get("title") or "")
        summary = str(item.get("summary") or "")
        tags = " ".join(str(tag) for tag in (item.get("tags") or []))
        title_terms = set(re.findall(r"[a-z0-9_-]{3,}", title.lower()))
        body_terms = set(re.findall(r"[a-z0-9_-]{3,}", f"{summary} {tags}".lower()))
        score = 3 * len(query_terms & title_terms) + len(query_terms & body_terms)
        if score:
            ranked.append((score, item))
    ranked.sort(key=lambda row: (row[0], str(row[1].get("published") or "")), reverse=True)
    return [item for _, item in ranked[:limit]]


def render_relevant_intel(path: str | Path, query: str, *, limit: int = 3,
                          max_chars: int = 1800) -> str:
    """Render bounded cards for an LLM prompt without copying whole articles."""
    lines: list[str] = []
    for item in relevant_items(path, query, limit=limit):
        lines.append(
            f"- {str(item.get('title') or 'Untitled')[:180]} "
            f"[{str(item.get('source') or 'web')}]\n"
            f"  hypothesis: {str(item.get('summary') or '')[:360]}\n"
            f"  source: {str(item.get('url') or '')[:300]}"
        )
    return "\n".join(lines)[:max_chars]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Source-linked security technique intelligence")
    parser.add_argument("--medium-tag", action="append", default=[])
    parser.add_argument("--feed", action="append", default=[])
    parser.add_argument("--x-query", action="append", default=[])
    parser.add_argument("--url", action="append", default=[])
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--output", default=str(default_ledger_path()))
    args = parser.parse_args(argv)

    items: list[dict] = []
    for tag in args.medium_tag:
        items.extend(medium_tag(tag))
    for feed in args.feed:
        items.extend(fetch_feed(feed, source="feed"))
    for query in args.x_query:
        items.extend(x_recent(query, limit=args.limit))
    for url in args.url:
        items.extend(fetch_article(url))

    added, duplicate = append_ledger(args.output, items)
    print(f"[+] intel: {added} added, {duplicate} duplicate, {len(items)} fetched -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
