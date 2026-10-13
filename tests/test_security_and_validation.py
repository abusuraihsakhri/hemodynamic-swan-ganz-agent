"""
Focused tests for security hardening and input validation.
"""
import sys
import os
import math
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pytest
from agents.models import SystemTaskPayload, UrgencyLevel
from agents.base import AuditTrail, PHIGuard, SecurityException
from cli import _safe_resolve_path


class TestInputValidation:
    """Tests for NaN/Inf rejection and identifier sanitization."""

    def test_reject_nan_primary(self):
        with pytest.raises(ValueError, match="finite number"):
            SystemTaskPayload(task_id="T1", target_identifier="X", primary_metric=float("nan"))

    def test_reject_inf_secondary(self):
        with pytest.raises(ValueError, match="finite number"):
            SystemTaskPayload(task_id="T1", target_identifier="X", primary_metric=1.0, secondary_metric=float("inf"))

    def test_reject_empty_task_id(self):
        with pytest.raises(ValueError, match="empty or whitespace"):
            SystemTaskPayload(task_id="   ", target_identifier="X", primary_metric=1.0)

    def test_reject_empty_target(self):
        with pytest.raises(ValueError, match="empty or whitespace"):
            SystemTaskPayload(task_id="T1", target_identifier="", primary_metric=1.0)

    def test_valid_payload(self):
        p = SystemTaskPayload(task_id="T1", target_identifier="X", primary_metric=1.0, secondary_metric=2.0)
        assert p.primary_metric == 1.0
        assert p.task_id == "T1"

    def test_whitespace_stripped(self):
        p = SystemTaskPayload(task_id="  T1  ", target_identifier="  X  ", primary_metric=1.0)
        assert p.task_id == "T1"
        assert p.target_identifier == "X"


class TestPathSafety:
    """Tests for path traversal protection in batch CLI."""

    def test_safe_path_within_cwd(self):
        result = _safe_resolve_path("sample.csv", must_exist=False)
        assert os.path.basename(result) == "sample.csv"

    def test_safe_path_nonexistent_input_raises(self):
        with pytest.raises(FileNotFoundError):
            _safe_resolve_path("nonexistent_file.csv", must_exist=True)

    def test_traversal_outside_cwd_rejected(self):
        with pytest.raises(ValueError, match="outside the working directory"):
            _safe_resolve_path("../etc/passwd", must_exist=False)

    def test_deeply_nested_traversal_rejected(self):
        with pytest.raises(ValueError, match="outside the working directory"):
            _safe_resolve_path("subdir/../../etc/shadow", must_exist=False)


class TestAuditTrailSecurity:
    """Tests for HMAC audit trail key handling and integrity."""

    def test_random_key_generated_by_default(self):
        t1 = AuditTrail()
        t2 = AuditTrail()
        assert t1.secret_key != t2.secret_key

    def test_explicit_key_matches(self):
        t = AuditTrail(secret_key="test-key")
        assert t.secret_key == b"test-key"

    def test_audit_integrity_after_multiple_entries(self):
        t = AuditTrail(secret_key="integrity-test-key")
        for i in range(5):
            t.log(actor="test", actor_tier="test", event_type="TEST", details={"i": i})
        assert t.verify_integrity() is True

    def test_audit_logs_are_chained(self):
        t = AuditTrail(secret_key="chain-test-key")
        t.log(actor="a", actor_tier="t", event_type="E1", details={"x": 1})
        t.log(actor="b", actor_tier="t", event_type="E2", details={"y": 2})
        logs = t.get_trail()
        assert len(logs) == 2
        assert logs[1]["prev_hash"] == logs[0]["current_hash"]

    def test_empty_trail_is_valid(self):
        t = AuditTrail()
        assert t.verify_integrity() is True


class TestPHIGuardComprehensive:
    """Extended PHI guard tests."""

    def test_reject_email(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Contact patient at john@example.com")

    def test_reject_phone(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("Call 555-123-4567 for results")

    def test_reject_ssn(self):
        with pytest.raises(SecurityException):
            PHIGuard.assert_no_phi("SSN: 123-45-6789 verified")

    def test_allow_clean_text(self):
        PHIGuard.assert_no_phi("Hemodynamic parameters within normal limits for case KEY-001")

    def test_redact_phi(self):
        result = PHIGuard.redact_phi("Patient MRN-12345 tested")
        assert "REDACTED_IDENTIFIER" in result
        assert "MRN" not in result or "12345" not in result

def test_hmac_detects_signature_tamper():
    trail = AuditTrail(secret_key="test")
    trail.log("actor", "tier", "EVENT", {"x": 1})
    trail.logs[0]["payload_hash"] = "0" * 64
    assert trail.verify_integrity() is False


def test_hmac_detects_recomputed_link_without_secret():
    trail = AuditTrail(secret_key="test")
    trail.log("actor", "tier", "EVENT", {"x": 1})
    trail.log("actor", "tier", "EVENT", {"x": 2})
    trail.logs[0]["current_hash"] = "0" * 64
    trail.logs[1]["prev_hash"] = "0" * 64
    assert trail.verify_integrity() is False


def test_audit_export_is_defensive_copy():
    trail = AuditTrail(secret_key="test")
    trail.log("actor", "tier", "EVENT", {"x": 1})
    trail.get_trail()[0]["current_hash"] = "changed"
    assert trail.verify_integrity() is True


def test_batch_bool_decoding():
    from cli import _parse_csv_bool
    assert _parse_csv_bool("False") is False
    assert _parse_csv_bool("true") is True
    with pytest.raises(ValueError):
        _parse_csv_bool("not-a-bool")


def test_batch_uses_synthetic_aliases_and_real_boolean_values(tmp_path, monkeypatch):
    import csv
    from cli import main
    monkeypatch.chdir(tmp_path)
    (tmp_path / "input.csv").write_text(
        "case_id,patient_synthetic_id,metric_primary,metric_secondary,is_stat,status_flag\\n"
        "CASE-A,SYNTH-01,10,3,False,NORMAL\\n"
        "CASE-B,SYNTH-02,10,3,True,NORMAL\\n"
    )
    assert main(["batch", "-i", "input.csv", "-o", "out.csv"]) == 0
    with (tmp_path / "out.csv").open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 2
    assert rows[0]["overall_urgency"] == "ROUTINE"
    assert rows[1]["overall_urgency"] == "CRITICAL_STAT_PANIC"


def test_batch_skips_sensitive_row_without_echo(tmp_path, monkeypatch, capsys):
    from cli import main
    monkeypatch.chdir(tmp_path)
    (tmp_path / "input.csv").write_text(
        "task_id,target_identifier,primary_metric,secondary_metric\\n"
        "CASE-1,Patient MRN-987654,8,1\\n"
    )
    assert main(["batch", "-i", "input.csv", "-o", "out.csv"]) == 0
    assert "MRN-987654" not in capsys.readouterr().out
