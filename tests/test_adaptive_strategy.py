from tools.adaptive_strategy import classify_output, infer_strategy_family, next_guidance


def test_classifies_waf_and_produces_stable_fingerprint():
    a = classify_output("HTTP/2 403\nserver: cloudflare\nAccess denied ray=abc123456789")
    b = classify_output("HTTP/2 403\nserver: cloudflare\nAccess denied ray=def987654321")
    assert a.control == "waf_or_acl"
    assert a.status == 403
    assert a.signature == b.signature


def test_xss_guidance_changes_family_instead_of_repeating():
    fp = classify_output("status: 200 output sanitized and html encoded")
    first = next_guidance("xss", fp, set())
    family = first.split(":", 1)[0]
    second = next_guidance("xss", fp, {family})
    assert second.split(":", 1)[0] != family


def test_infers_common_strategy_families():
    assert infer_strategy_family("curl -X OPTIONS https://t.example/admin") == "method-semantics"
    assert infer_strategy_family("python dom_xss_harness.py https://t.example") == "browser-oracle"

