import json

import pytest

from tools import technique_intel as intel


def test_feed_is_compact_source_linked_and_untrusted(monkeypatch):
    feed = b"""<?xml version='1.0'?><rss><channel><item>
      <title>WAF normalization writeup</title>
      <link>https://example.org/post</link>
      <description><![CDATA[<p>Compare proxy and origin parsing.</p>]]></description>
      <category>bug bounty</category>
    </item></channel></rss>"""
    monkeypatch.setattr(intel, "_fetch", lambda *_a, **_k: feed)
    items = intel.fetch_feed("https://example.org/feed")
    assert len(items) == 1
    assert items[0]["url"] == "https://example.org/post"
    assert items[0]["trust"] == "untrusted_external_research"
    assert items[0]["use"] == "hypothesis_only_requires_live_verification"
    assert "<p>" not in items[0]["summary"]


def test_ledger_deduplicates_by_source_url_title(tmp_path):
    item = intel._item("web", "https://example.org/p", "Title", "Summary")
    path = tmp_path / "intel.jsonl"
    assert intel.append_ledger(path, [item]) == (1, 0)
    assert intel.append_ledger(path, [item]) == (0, 1)
    assert len(path.read_text(encoding="utf-8").splitlines()) == 1
    assert json.loads(path.read_text(encoding="utf-8"))["id"] == item["id"]


def test_x_requires_operator_developer_token(monkeypatch):
    monkeypatch.delenv("X_BEARER_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="X_BEARER_TOKEN"):
        intel.x_recent("bug bounty")


def test_rejects_private_initial_research_url():
    with pytest.raises(ValueError, match="private/loopback"):
        intel._fetch("http://127.0.0.1/internal")


def test_relevant_items_are_ranked_bounded_and_hypothesis_only(tmp_path):
    path = tmp_path / "intel.jsonl"
    items = [
        intel._item(
            "medium", "https://example.org/waf", "WAF path normalization bypass",
            "Compare proxy and origin path parsing for authorization differences.",
            tags=["waf", "403"],
        ),
        intel._item(
            "web", "https://example.org/xss", "DOM XSS sink mapping",
            "Trace browser sinks and confirm script execution.",
            tags=["xss"],
        ),
    ]
    intel.append_ledger(path, items)
    matches = intel.relevant_items(path, "403 WAF normalization", limit=1)
    assert [item["url"] for item in matches] == ["https://example.org/waf"]
    rendered = intel.render_relevant_intel(path, "403 WAF normalization", limit=1, max_chars=240)
    assert "hypothesis:" in rendered
    assert "https://example.org/waf" in rendered
    assert len(rendered) <= 240


def test_relevant_items_ignore_unverified_schema_rows(tmp_path):
    path = tmp_path / "intel.jsonl"
    path.write_text(json.dumps({"title": "WAF bypass", "summary": "normalization"}) + "\n")
    assert intel.relevant_items(path, "waf normalization") == []


def test_default_ledger_honors_agentnarna_home(tmp_path, monkeypatch):
    monkeypatch.setenv("AGENTNARNA_HOME", str(tmp_path))
    monkeypatch.delenv("AGENTNARNA_INTEL_PATH", raising=False)
    assert intel.default_ledger_path() == tmp_path / "hunt-memory" / "technique-intel.jsonl"
