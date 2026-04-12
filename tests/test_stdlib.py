"""
Comprehensive tests for flux-fleet-stdlib.

Run with:  python -m pytest tests/test_stdlib.py -v
"""

import json
import sys
import os
import time

# Ensure the src package is importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.errors import (
    ErrorCode, Severity, FleetError, ErrorChain, fleet_error,
    ALL_ERROR_CODES,
)
from src.status import (
    Status, StatusOr, status_for_error_code,
    ALL_STATUSES,
)
from src.types import (
    AgentId, TaskId, RepoRef, Capability, FleetAddress,
)


# ===================================================================
# 1. Error-code uniqueness & completeness
# ===================================================================

class TestErrorCodeUniqueness:
    def test_all_values_unique(self):
        vals = [e.value for e in ErrorCode]
        assert len(vals) == len(set(vals)), "Duplicate error code values detected"

    def test_at_least_40_codes(self):
        assert len(ErrorCode) >= 40, f"Expected >= 40 codes, got {len(ErrorCode)}"

    def test_constants_match_enum(self):
        """The ERR_* module-level constants should match the enum values."""
        import src.errors as e
        for ec in ErrorCode:
            const_name = f"ERR_{ec.value}"
            assert hasattr(e, const_name), f"Missing constant {const_name}"
            assert getattr(e, const_name) == ec.value

    def test_frozenset_agreement(self):
        assert ALL_ERROR_CODES == frozenset(ec.value for ec in ErrorCode)

    def test_domain_coverage(self):
        domains = set()
        for ec in ErrorCode:
            domains.add(ec.value.split("_")[0])
        expected = {"VM", "COOP", "TRANSPORT", "TRUST", "SPEC", "SECURITY"}
        assert expected <= domains, f"Missing domains: {expected - domains}"


# ===================================================================
# 2. FleetError creation & serialization
# ===================================================================

class TestFleetError:
    def test_basic_creation(self):
        err = FleetError(code="VM_DIV_ZERO", message="division by zero at pc=42")
        assert err.code == "VM_DIV_ZERO"
        assert err.message == "division by zero at pc=42"
        assert err.severity == Severity.ERROR.value
        assert err.error_id  # should be auto-generated

    def test_full_creation(self):
        err = FleetError(
            code="COOP_TIMEOUT",
            message="no response in 30s",
            severity=Severity.FATAL.value,
            source_repo="flux-coop-runtime",
            source_agent="orchestrator-01",
            context={"timeout_s": 30, "retries": 3},
        )
        assert err.source_repo == "flux-coop-runtime"
        assert err.context["timeout_s"] == 30

    def test_str_representation(self):
        err = FleetError(
            code="TRANSPORT_PUSH_FAILED",
            message="git push rejected",
            source_repo="flux-runtime",
            source_agent="pusher",
        )
        s = str(err)
        assert "TRANSPORT_PUSH_FAILED" in s
        assert "flux-runtime" in s
        assert "pusher" in s

    def test_json_round_trip(self):
        err = fleet_error(
            "VM_CYCLE_LIMIT",
            "hit ceiling",
            source_repo="test-repo",
            cycles=5000,
        )
        json_str = err.to_json()
        restored = FleetError.from_json(json_str)
        assert restored.code == err.code
        assert restored.message == err.message
        assert restored.source_repo == err.source_repo
        assert restored.context["cycles"] == 5000

    def test_dict_round_trip(self):
        err = fleet_error("SPEC_FORMAT_VIOLATION", "bad header", line=10)
        d = err.to_dict()
        restored = FleetError.from_dict(d)
        assert restored.code == err.code
        assert restored.context["line"] == 10


# ===================================================================
# 3. fleet_error factory
# ===================================================================

class TestFleetErrorFactory:
    def test_factory_basic(self):
        err = fleet_error("VM_HALTED", "machine stopped")
        assert isinstance(err, FleetError)
        assert err.code == "VM_HALTED"

    def test_factory_with_kwargs(self):
        err = fleet_error(
            "SECURITY_SANDBOX_VIOLATION",
            "attempted file write",
            source_repo="vm-guard",
            source_agent="sandbox-monitor",
            path="/etc/passwd",
        )
        assert err.context["path"] == "/etc/passwd"
        assert err.source_agent == "sandbox-monitor"

    def test_factory_default_severity(self):
        err = fleet_error("COOP_AGENT_REFUSED", "nope")
        assert err.severity == Severity.ERROR.value

    def test_factory_custom_severity(self):
        err = fleet_error("TRUST_SCORE_LOW", "score 0.1", severity=Severity.WARNING.value)
        assert err.severity == Severity.WARNING.value


# ===================================================================
# 4. ErrorChain wrapping
# ===================================================================

class TestErrorChain:
    def test_empty_chain(self):
        chain = ErrorChain()
        assert not chain
        assert len(chain) == 0
        assert chain.root() is None
        assert chain.outermost() is None

    def test_wrap_single(self):
        e1 = fleet_error("TRANSPORT_GIT_ERROR", "clone failed")
        chain = ErrorChain().wrap(e1)
        assert len(chain) == 1
        assert chain.root().code == "TRANSPORT_GIT_ERROR"  # type: ignore

    def test_wrap_multiple(self):
        e1 = fleet_error("TRANSPORT_GIT_ERROR", "clone failed")
        e2 = fleet_error("COOP_TRANSPORT_FAILURE", "could not contact agent",
                         source_repo="coop", source_agent="sender")
        e3 = fleet_error("COOP_TIMEOUT", "overall timeout", severity=Severity.FATAL.value)
        chain = ErrorChain().wrap(e1).wrap(e2).wrap(e3)
        assert len(chain) == 3
        assert chain.root().code == "TRANSPORT_GIT_ERROR"  # type: ignore
        assert chain.outermost().code == "COOP_TIMEOUT"  # type: ignore

    def test_chain_serialization(self):
        e1 = fleet_error("VM_INVALID_OPCODE", "bad byte 0xFF", pc=99)
        e2 = fleet_error("VM_TYPE_ERROR", "type mismatch during decode")
        chain = ErrorChain().wrap(e1).wrap(e2)
        json_str = chain.to_json()
        restored = ErrorChain.from_json(json_str)
        assert len(restored) == 2
        assert restored.root().code == "VM_INVALID_OPCODE"  # type: ignore
        assert restored.outermost().context == {}  # type: ignore


# ===================================================================
# 5. Status & StatusOr
# ===================================================================

class TestStatus:
    def test_all_statuses_unique(self):
        vals = [s.value for s in Status]
        assert len(vals) == len(set(vals))

    def test_expected_statuses(self):
        expected = {"SUCCESS", "PENDING", "TIMEOUT", "REFUSED",
                     "ERROR", "CANCELLED", "PARTIAL", "RATE_LIMITED"}
        actual = set(s.value for s in Status)
        assert expected == actual

    def test_status_for_error_code(self):
        assert status_for_error_code("COOP_TIMEOUT") == Status.TIMEOUT
        assert status_for_error_code("COOP_AGENT_REFUSED") == Status.REFUSED
        assert status_for_error_code("VM_DIV_ZERO") == Status.ERROR
        assert status_for_error_code("TRANSPORT_MERGE_CONFLICT") == Status.PARTIAL
        assert status_for_error_code("UNKNOWN_THING") == Status.ERROR  # fallback


class TestStatusOr:
    def test_ok_value(self):
        result = StatusOr(value=42)
        assert result.ok()
        assert result.value == 42
        assert bool(result) is True

    def test_ok_string(self):
        result = StatusOr(value="hello")
        assert result.ok()
        assert result.value == "hello"

    def test_ok_dict(self):
        result = StatusOr(value={"key": "val"})
        assert result.ok()
        assert result.value["key"] == "val"

    def test_error_status(self):
        result = StatusOr(status=Status.REFUSED, error_message="nope")
        assert not result.ok()
        assert result.status == Status.REFUSED
        assert result.error_message == "nope"
        assert bool(result) is False

    def test_access_value_on_error_raises(self):
        result = StatusOr(status=Status.ERROR, error_message="boom")
        try:
            _ = result.value
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "boom" in str(e)

    def test_error_code_propagation(self):
        result = StatusOr(
            status=Status.TIMEOUT,
            error_message="timed out",
            error_code="COOP_TIMEOUT",
        )
        assert result.error_code == "COOP_TIMEOUT"

    def test_json_round_trip_ok(self):
        result = StatusOr(value={"answer": 42})
        restored = StatusOr.from_dict(json.loads(result.to_json()))
        assert restored.ok()
        assert restored.value == {"answer": 42}

    def test_json_round_trip_err(self):
        result = StatusOr(
            status=Status.RATE_LIMITED,
            error_message="slow down",
            error_code="RATE_LIMITED",
        )
        restored = StatusOr.from_dict(json.loads(result.to_json()))
        assert not restored.ok()
        assert restored.status == Status.RATE_LIMITED
        assert restored.error_code == "RATE_LIMITED"

    def test_str_repr(self):
        ok = StatusOr(value=1)
        err = StatusOr(status=Status.CANCELLED, error_message="bye")
        assert "OK" in str(ok)
        assert "CANCELLED" in str(err)


# ===================================================================
# 6. Shared type JSON round-trips
# ===================================================================

class TestAgentId:
    def test_round_trip(self):
        a = AgentId(
            name="executor-01",
            repo_url="https://github.com/SuperInstance/flux-runtime",
            role="vm-executor",
            capabilities=["vm-run", "bytecode-verify"],
        )
        restored = AgentId.from_json(a.to_json())
        assert restored == a

    def test_from_dict_missing_optional(self):
        a = AgentId.from_dict({"name": "x", "repo_url": "y"})
        assert a.role == ""
        assert a.capabilities == []


class TestTaskId:
    def test_auto_hash(self):
        t = TaskId(source_agent="agent-a")
        assert len(t.unique_hash) == 16
        assert t.timestamp > 0

    def test_deterministic_hash(self):
        ts = 1700000000.0
        t1 = TaskId(source_agent="agent-a", timestamp=ts)
        t2 = TaskId(source_agent="agent-a", timestamp=ts)
        assert t1.unique_hash == t2.unique_hash

    def test_round_trip(self):
        t = TaskId(source_agent="orchestrator", timestamp=1234.5, unique_hash="abcd")
        restored = TaskId.from_json(t.to_json())
        assert restored.source_agent == t.source_agent
        assert restored.unique_hash == t.unique_hash


class TestRepoRef:
    def test_full_name(self):
        r = RepoRef(owner="SuperInstance", name="flux-runtime")
        assert r.full_name == "SuperInstance/flux-runtime"

    def test_round_trip(self):
        r = RepoRef(owner="SuperInstance", name="flux-coop", branch="dev",
                     commit_hash="abc123")
        restored = RepoRef.from_json(r.to_json())
        assert restored == r


class TestCapability:
    def test_confidence_clamped(self):
        c = Capability(name="vm-run", confidence=1.5)
        assert c.confidence == 1.0
        c2 = Capability(name="vm-run", confidence=-0.3)
        assert c2.confidence == 0.0

    def test_round_trip(self):
        c = Capability(name="bytecode-verify", confidence=0.95,
                        evidence_url="https://example.com/evidence")
        restored = Capability.from_json(c.to_json())
        assert restored == c


class TestFleetAddress:
    def test_round_trip(self):
        a = FleetAddress(
            name="any-vm-executor",
            role_pattern="vm-*",
            capability_pattern="vm-*",
            repo_url="https://github.com/SuperInstance/flux-runtime",
        )
        restored = FleetAddress.from_json(a.to_json())
        assert restored == a


# ===================================================================
# 7. Severity levels
# ===================================================================

class TestSeverity:
    def test_all_severities(self):
        expected = {"FATAL", "ERROR", "WARNING", "INFO"}
        actual = set(s.value for s in Severity)
        assert expected == actual

    def test_fleet_error_accepts_all_severities(self):
        for sev in Severity:
            err = FleetError(code="TEST", message="m", severity=sev.value)
            assert err.severity == sev.value


# ===================================================================
# 8. Cross-module integration
# ===================================================================

class TestIntegration:
    def test_error_chain_with_status(self):
        """An ErrorChain's outermost error can derive a Status."""
        e1 = fleet_error("TRANSPORT_GIT_ERROR", "clone failed")
        e2 = fleet_error("COOP_TRANSPORT_FAILURE", "upstream failure")
        chain = ErrorChain().wrap(e1).wrap(e2)
        outermost = chain.outermost()
        status = status_for_error_code(outermost.code)  # type: ignore
        assert status == Status.ERROR

    def test_statusor_from_fleet_error(self):
        err = fleet_error("COOP_NO_CAPABLE_AGENT", "nobody available",
                          source_repo="coop-runtime")
        result = StatusOr(
            status=status_for_error_code(err.code),
            error_message=err.message,
            error_code=err.code,
        )
        assert not result.ok()
        assert result.status == Status.REFUSED
        assert result.error_code == "COOP_NO_CAPABLE_AGENT"

    def test_agentid_with_capability_list(self):
        agent = AgentId(
            name="guard-01",
            repo_url="https://github.com/SuperInstance/flux-guard",
            role="security",
            capabilities=["sandbox-enforce", "bytecode-verify"],
        )
        caps = [Capability(name=c, confidence=0.9) for c in agent.capabilities]
        assert len(caps) == 2
        assert all(c.confidence == 0.9 for c in caps)


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
