import json

from brain import Brain
from tools.report_evidence import collect_verified_evidence, report_gate_note


def _validation(*, ready: bool, endpoint: str, links=None):
    return {
        "status": "validated_finding" if ready else "scanner_hit",
        "rejection_reasons": [] if ready else ["verifier rejected"],
        "verifier": {"confirmed": ready, "oracle": "fresh marker", "trace": []},
        "finding": {
            "vulnerability_type": "IDOR" if ready else "XSS",
            "endpoint": endpoint,
            "impact": "controlled identity B data read" if ready else "reflection only",
        },
        "evidence_links": links or [],
    }


def test_verified_finding_cannot_promote_neighboring_scanner_artifact(tmp_path):
    good = tmp_path / "idor"
    noisy = tmp_path / "xss"
    good.mkdir()
    noisy.mkdir()
    (good / "proof.txt").write_text("victim marker NARNA-123", encoding="utf-8")
    (good / "validation.json").write_text(json.dumps(
        _validation(ready=True, endpoint="/api/invoices/2", links=["proof.txt"])
    ), encoding="utf-8")
    (noisy / "reflection.txt").write_text("UNVERIFIED-XSS-SHOULD-NOT-LEAK", encoding="utf-8")
    (noisy / "validation.json").write_text(json.dumps(
        _validation(ready=False, endpoint="/?q=x", links=["reflection.txt"])
    ), encoding="utf-8")

    evidence = collect_verified_evidence(str(tmp_path))
    assert "/api/invoices/2" in evidence
    assert "NARNA-123" in evidence
    assert "UNVERIFIED-XSS-SHOULD-NOT-LEAK" not in evidence
    assert "/?q=x" not in evidence


def test_evidence_link_cannot_escape_finding_root(tmp_path):
    root = tmp_path / "findings"
    finding = root / "idor"
    finding.mkdir(parents=True)
    secret = tmp_path / "outside.txt"
    secret.write_text("OUTSIDE-SECRET", encoding="utf-8")
    (finding / "validation.json").write_text(json.dumps(
        _validation(ready=True, endpoint="/api/2", links=["../../outside.txt"])
    ), encoding="utf-8")
    assert "OUTSIDE-SECRET" not in collect_verified_evidence(str(root))


def test_blocked_report_does_not_save_no_reports_artifact(tmp_path):
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "validation.json").write_text(json.dumps(
        _validation(ready=False, endpoint="/?q=x")
    ), encoding="utf-8")
    brain = Brain.__new__(Brain)
    brain.enabled = True

    result = brain.write_report(str(tmp_path))
    assert result.startswith("NO_REPORTS")
    assert not (tmp_path / "brain" / "04_h1_reports.md").exists()


def test_gate_requires_at_least_one_exact_verified_record(tmp_path):
    ready, note = report_gate_note(str(tmp_path))
    assert ready is False
    assert "no validation.json" in note

