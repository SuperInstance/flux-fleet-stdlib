"""
Comprehensive tests for flux-fleet-stdlib.

Run with:  python -m pytest tests/test_stdlib.py -v
"""

import json
import math
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
from src.manifest import (
    AgentManifest, ResourceRequirements, OpcodeSupport, VALID_ROLES,
)
from src.envelope import (
    MessageEnvelope, MessageType, Priority,
)
from src.versioning import (
    ISAVersion, OpcodeMapping,
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

    def test_vm_domain_count(self):
        vm = [e for e in ErrorCode if e.value.startswith("VM_")]
        assert len(vm) >= 10

    def test_coop_domain_count(self):
        coop = [e for e in ErrorCode if e.value.startswith("COOP_")]
        assert len(coop) >= 8

    def test_transport_domain_count(self):
        tr = [e for e in ErrorCode if e.value.startswith("TRANSPORT_")]
        assert len(tr) >= 7

    def test_trust_domain_count(self):
        tr = [e for e in ErrorCode if e.value.startswith("TRUST_")]
        assert len(tr) >= 3

    def test_spec_domain_count(self):
        sp = [e for e in ErrorCode if e.value.startswith("SPEC_")]
        assert len(sp) >= 5

    def test_security_domain_count(self):
        se = [e for e in ErrorCode if e.value.startswith("SECURITY_")]
        assert len(se) >= 3

    def test_enum_is_string_based(self):
        assert isinstance(ErrorCode.VM_HALTED.value, str)

    def test_enum_members_are_iterable(self):
        codes = list(ErrorCode)
        assert len(codes) >= 40


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

    def test_repr(self):
        err = FleetError(code="VM_HALTED", message="stopped")
        r = repr(err)
        assert "FleetError" in r
        assert "VM_HALTED" in r

    def test_error_id_is_string(self):
        err = FleetError(code="TEST", message="m")
        assert isinstance(err.error_id, str)
        assert len(err.error_id) == 12

    def test_custom_error_id(self):
        err = FleetError(code="TEST", message="m", error_id="custom123")
        assert err.error_id == "custom123"

    def test_timestamp_is_float(self):
        err = FleetError(code="TEST", message="m")
        assert isinstance(err.timestamp, float)

    def test_custom_timestamp(self):
        err = FleetError(code="TEST", message="m", timestamp=1234.5)
        assert err.timestamp == 1234.5

    def test_is_exception(self):
        err = FleetError(code="TEST", message="m")
        assert isinstance(err, Exception)

    def test_empty_context(self):
        err = FleetError(code="TEST", message="m")
        assert err.context == {}

    def test_nested_context(self):
        err = fleet_error("TEST", "m", details={"key": {"nested": 42}})
        assert err.context["details"]["key"]["nested"] == 42

    def test_str_without_repo(self):
        err = FleetError(code="VM_HALTED", message="stop")
        s = str(err)
        assert "(" not in s  # no repo parenthetical

    def test_dict_keys(self):
        err = FleetError(code="TEST", message="m", error_id="abc123")
        d = err.to_dict()
        expected_keys = {"code", "message", "severity", "source_repo",
                         "source_agent", "timestamp", "error_id", "context"}
        assert set(d.keys()) == expected_keys


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

    def test_factory_info_severity(self):
        err = fleet_error("TEST", "info msg", severity=Severity.INFO.value)
        assert err.severity == Severity.INFO.value

    def test_factory_fatal_severity(self):
        err = fleet_error("TEST", "fatal msg", severity=Severity.FATAL.value)
        assert err.severity == Severity.FATAL.value

    def test_factory_no_context(self):
        err = fleet_error("TEST", "m")
        assert err.context == {}

    def test_factory_multiple_context_keys(self):
        err = fleet_error("TEST", "m", a=1, b=2, c=3)
        assert err.context == {"a": 1, "b": 2, "c": 3}


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

    def test_chain_dict_round_trip(self):
        e1 = fleet_error("TEST", "a", x=1)
        e2 = fleet_error("TEST", "b", y=2)
        chain = ErrorChain().wrap(e1).wrap(e2)
        d = chain.to_dict()
        restored = ErrorChain.from_dict(d)
        assert len(restored) == 2

    def test_chain_bool_truthy(self):
        chain = ErrorChain().wrap(fleet_error("TEST", "m"))
        assert bool(chain) is True

    def test_chain_empty_dict(self):
        d = ErrorChain().to_dict()
        assert d == {"errors": []}

    def test_chain_empty_json_round_trip(self):
        chain = ErrorChain()
        restored = ErrorChain.from_json(chain.to_json())
        assert not restored

    def test_chain_wrap_returns_self(self):
        chain = ErrorChain()
        result = chain.wrap(fleet_error("TEST", "m"))
        assert result is chain


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

    def test_status_is_string_enum(self):
        assert isinstance(Status.SUCCESS.value, str)

    def test_all_statuses_frozenset(self):
        assert ALL_STATUSES == frozenset(s.value for s in Status)


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

    def test_ok_list(self):
        result = StatusOr(value=[1, 2, 3])
        assert result.ok()
        assert result.value == [1, 2, 3]

    def test_ok_zero_value(self):
        result = StatusOr(value=0)
        assert result.ok()
        assert result.value == 0

    def test_ok_empty_string(self):
        result = StatusOr(value="")
        assert result.ok()
        assert result.value == ""

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

    def test_error_message_empty_by_default(self):
        result = StatusOr(status=Status.ERROR)
        assert result.error_message == ""

    def test_error_code_empty_by_default(self):
        result = StatusOr(status=Status.ERROR)
        assert result.error_code == ""

    def test_dict_round_trip_ok(self):
        result = StatusOr(value="test")
        restored = StatusOr.from_dict(result.to_dict())
        assert restored.ok()
        assert restored.value == "test"

    def test_dict_round_trip_err(self):
        result = StatusOr(status=Status.PARTIAL, error_message="partial")
        restored = StatusOr.from_dict(result.to_dict())
        assert not restored.ok()
        assert restored.status == Status.PARTIAL

    def test_value_overrides_status(self):
        """Providing a value should force status to SUCCESS."""
        result = StatusOr(value=99, status=Status.ERROR)
        assert result.ok()
        assert result.value == 99

    def test_none_value_treated_as_error(self):
        result = StatusOr(value=None, status=Status.PENDING)
        assert not result.ok()
        assert result.status == Status.PENDING


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

    def test_dict_keys(self):
        a = AgentId(name="a", repo_url="b", role="c", capabilities=["d"])
        d = a.to_dict()
        assert set(d.keys()) == {"name", "repo_url", "role", "capabilities"}

    def test_json_string_output(self):
        a = AgentId(name="a", repo_url="b")
        j = a.to_json()
        parsed = json.loads(j)
        assert parsed["name"] == "a"


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

    def test_different_agents_different_hashes(self):
        t1 = TaskId(source_agent="agent-a", timestamp=1000.0)
        t2 = TaskId(source_agent="agent-b", timestamp=1000.0)
        assert t1.unique_hash != t2.unique_hash

    def test_dict_keys(self):
        t = TaskId(source_agent="a", timestamp=1.0, unique_hash="hash")
        d = t.to_dict()
        assert set(d.keys()) == {"source_agent", "timestamp", "unique_hash"}


class TestRepoRef:
    def test_full_name(self):
        r = RepoRef(owner="SuperInstance", name="flux-runtime")
        assert r.full_name == "SuperInstance/flux-runtime"

    def test_round_trip(self):
        r = RepoRef(owner="SuperInstance", name="flux-coop", branch="dev",
                     commit_hash="abc123")
        restored = RepoRef.from_json(r.to_json())
        assert restored == r

    def test_defaults(self):
        r = RepoRef(owner="o", name="n")
        assert r.branch == "main"
        assert r.commit_hash == ""

    def test_from_dict_minimal(self):
        r = RepoRef.from_dict({"owner": "o", "name": "n"})
        assert r.full_name == "o/n"
        assert r.branch == "main"


class TestCapability:
    def test_confidence_clamped_high(self):
        c = Capability(name="vm-run", confidence=1.5)
        assert c.confidence == 1.0

    def test_confidence_clamped_low(self):
        c2 = Capability(name="vm-run", confidence=-0.3)
        assert c2.confidence == 0.0

    def test_confidence_boundary_high(self):
        c = Capability(name="x", confidence=1.0)
        assert c.confidence == 1.0

    def test_confidence_boundary_low(self):
        c = Capability(name="x", confidence=0.0)
        assert c.confidence == 0.0

    def test_round_trip(self):
        c = Capability(name="bytecode-verify", confidence=0.95,
                        evidence_url="https://example.com/evidence")
        restored = Capability.from_json(c.to_json())
        assert restored == c

    def test_default_evidence_url(self):
        c = Capability(name="x")
        assert c.evidence_url == ""


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

    def test_defaults(self):
        a = FleetAddress(name="test")
        assert a.role_pattern == "*"
        assert a.capability_pattern == "*"
        assert a.repo_url == ""

    def test_dict_keys(self):
        a = FleetAddress(name="a", role_pattern="b", capability_pattern="c", repo_url="d")
        d = a.to_dict()
        assert set(d.keys()) == {"name", "role_pattern", "capability_pattern", "repo_url"}


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

    def test_severity_count(self):
        assert len(Severity) == 4


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


# ===================================================================
# 9. ResourceRequirements
# ===================================================================

class TestResourceRequirements:
    def test_defaults(self):
        r = ResourceRequirements()
        assert r.max_memory_mb == 256
        assert r.max_cpu_seconds == 60
        assert r.requires_gpu is False
        assert r.requires_network is False
        assert r.supported_formats == ["A", "B", "C", "D", "E"]

    def test_custom(self):
        r = ResourceRequirements(
            max_memory_mb=512,
            max_cpu_seconds=120,
            requires_gpu=True,
            requires_network=True,
            supported_formats=["A", "B"],
        )
        assert r.max_memory_mb == 512
        assert r.requires_gpu is True
        assert r.supported_formats == ["A", "B"]

    def test_json_round_trip(self):
        r = ResourceRequirements(max_memory_mb=1024, supported_formats=["F", "G"])
        restored = ResourceRequirements.from_json(r.to_json())
        assert restored == r

    def test_dict_round_trip(self):
        r = ResourceRequirements(max_cpu_seconds=300, requires_gpu=True)
        restored = ResourceRequirements.from_dict(r.to_dict())
        assert restored.max_cpu_seconds == 300
        assert restored.requires_gpu is True

    def test_dict_keys(self):
        r = ResourceRequirements()
        d = r.to_dict()
        expected = {"max_memory_mb", "max_cpu_seconds", "requires_gpu",
                     "requires_network", "supported_formats"}
        assert set(d.keys()) == expected

    def test_from_dict_defaults(self):
        r = ResourceRequirements.from_dict({})
        assert r.max_memory_mb == 256
        assert r.supported_formats == ["A", "B", "C", "D", "E"]


# ===================================================================
# 10. OpcodeSupport
# ===================================================================

class TestOpcodeSupport:
    def test_defaults(self):
        op = OpcodeSupport(opcode=0, mnemonic="NOP", format="A")
        assert op.implemented is False
        assert op.tested is False

    def test_full(self):
        op = OpcodeSupport(opcode=1, mnemonic="ADD", format="A",
                           implemented=True, tested=True)
        assert op.opcode == 1
        assert op.mnemonic == "ADD"
        assert op.implemented is True
        assert op.tested is True

    def test_json_round_trip(self):
        op = OpcodeSupport(opcode=42, mnemonic="CUSTOM", format="F",
                           implemented=True, tested=False)
        restored = OpcodeSupport.from_json(op.to_json())
        assert restored == op

    def test_dict_round_trip(self):
        op = OpcodeSupport(opcode=5, mnemonic="SUB", format="B")
        restored = OpcodeSupport.from_dict(op.to_dict())
        assert restored.opcode == 5
        assert restored.mnemonic == "SUB"

    def test_from_dict_defaults(self):
        op = OpcodeSupport.from_dict({"opcode": 1, "mnemonic": "ADD"})
        assert op.format == "A"
        assert op.implemented is False
        assert op.tested is False


# ===================================================================
# 11. AgentManifest
# ===================================================================

def _make_manifest(**overrides) -> AgentManifest:
    """Helper to create a test manifest."""
    defaults = dict(
        agent_name="test-agent",
        agent_role="workhorse",
        version="1.0.0",
        capabilities=["bytecode_execution", "a2a_tell"],
        opcode_support=[
            OpcodeSupport(opcode=0, mnemonic="NOP", format="A", implemented=True, tested=True),
            OpcodeSupport(opcode=1, mnemonic="ADD", format="A", implemented=True, tested=True),
            OpcodeSupport(opcode=2, mnemonic="SUB", format="A", implemented=False, tested=False),
        ],
        resource_requirements=ResourceRequirements(supported_formats=["A", "B"]),
        repo_url="https://github.com/test/agent",
        test_count=50,
        trust_baseline=0.8,
    )
    defaults.update(overrides)
    return AgentManifest(**defaults)


class TestAgentManifest:
    def test_basic_creation(self):
        m = _make_manifest()
        assert m.agent_name == "test-agent"
        assert m.agent_role == "workhorse"
        assert m.version == "1.0.0"

    def test_supports_opcode_true(self):
        m = _make_manifest()
        assert m.supports_opcode(0) is True
        assert m.supports_opcode(1) is True

    def test_supports_opcode_false(self):
        m = _make_manifest()
        assert m.supports_opcode(2) is False  # not implemented
        assert m.supports_opcode(999) is False  # unknown

    def test_supports_format_true(self):
        m = _make_manifest()
        assert m.supports_format("A") is True
        assert m.supports_format("B") is True

    def test_supports_format_false(self):
        m = _make_manifest()
        assert m.supports_format("Z") is False

    def test_supports_capability_true(self):
        m = _make_manifest()
        assert m.supports_capability("bytecode_execution") is True
        assert m.supports_capability("a2a_tell") is True

    def test_supports_capability_false(self):
        m = _make_manifest()
        assert m.supports_capability("nonexistent") is False

    def test_json_round_trip(self):
        m = _make_manifest()
        restored = AgentManifest.from_json(m.to_json())
        assert restored.agent_name == m.agent_name
        assert restored.agent_role == m.agent_role
        assert restored.version == m.version
        assert len(restored.opcode_support) == len(m.opcode_support)
        assert restored.test_count == 50

    def test_dict_round_trip(self):
        m = _make_manifest()
        restored = AgentManifest.from_dict(m.to_dict())
        assert restored == m

    def test_compatibility_score_identical(self):
        m = _make_manifest()
        score = m.compatibility_score(m)
        assert score == 1.0

    def test_compatibility_score_disjoint(self):
        m1 = _make_manifest(
            capabilities=["cap_a"],
            opcode_support=[OpcodeSupport(opcode=0, mnemonic="X", format="A", implemented=True)],
            resource_requirements=ResourceRequirements(supported_formats=["A"]),
            trust_baseline=1.0,
        )
        m2 = _make_manifest(
            agent_name="other",
            capabilities=["cap_b"],
            opcode_support=[OpcodeSupport(opcode=99, mnemonic="Y", format="Z", implemented=True)],
            resource_requirements=ResourceRequirements(supported_formats=["Z"]),
            trust_baseline=0.0,
        )
        score = m1.compatibility_score(m2)
        # Should be 0 because everything is disjoint and trust distance is max
        assert score == 0.0

    def test_compatibility_score_partial(self):
        m1 = _make_manifest(
            capabilities=["a", "b", "c"],
            opcode_support=[
                OpcodeSupport(opcode=0, mnemonic="X", format="A", implemented=True),
                OpcodeSupport(opcode=1, mnemonic="Y", format="A", implemented=True),
            ],
            resource_requirements=ResourceRequirements(supported_formats=["A", "B"]),
            trust_baseline=0.5,
        )
        m2 = _make_manifest(
            agent_name="other",
            capabilities=["a", "b", "d"],
            opcode_support=[
                OpcodeSupport(opcode=0, mnemonic="X", format="A", implemented=True),
                OpcodeSupport(opcode=2, mnemonic="Z", format="A", implemented=True),
            ],
            resource_requirements=ResourceRequirements(supported_formats=["A", "C"]),
            trust_baseline=0.5,
        )
        score = m1.compatibility_score(m2)
        assert 0.0 < score < 1.0

    def test_empty_opcodes_supports_opcode(self):
        m = _make_manifest(opcode_support=[])
        assert m.supports_opcode(0) is False

    def test_empty_capabilities_supports_capability(self):
        m = _make_manifest(capabilities=[])
        assert m.supports_capability("anything") is False

    def test_default_values(self):
        m = AgentManifest(agent_name="a", agent_role="vessel", version="0.1.0")
        assert m.capabilities == []
        assert m.opcode_support == []
        assert m.test_count == 0
        assert m.trust_baseline == 0.5
        assert m.repo_url == ""
        assert isinstance(m.last_active, float)

    def test_last_active_is_recent(self):
        m = _make_manifest()
        assert time.time() - m.last_active < 2.0

    def test_from_dict_defaults(self):
        d = {"agent_name": "x", "agent_role": "scout", "version": "0.0.1"}
        m = AgentManifest.from_dict(d)
        assert m.capabilities == []
        assert m.test_count == 0

    def test_valid_roles_constant(self):
        assert "lighthouse" in VALID_ROLES
        assert "vessel" in VALID_ROLES
        assert "scout" in VALID_ROLES
        assert "workhorse" in VALID_ROLES
        assert len(VALID_ROLES) == 4

    def test_compatibility_trust_proximity(self):
        m1 = _make_manifest(
            capabilities=[], opcode_support=[],
            resource_requirements=ResourceRequirements(supported_formats=[]),
            trust_baseline=0.9,
        )
        m2 = _make_manifest(
            agent_name="other",
            capabilities=[], opcode_support=[],
            resource_requirements=ResourceRequirements(supported_formats=[]),
            trust_baseline=0.1,
        )
        score = m1.compatibility_score(m2)
        # All factors are 0 except trust: 1.0 - 0.8 = 0.2, weighted 0.15
        assert abs(score - 0.15 * 0.2) < 1e-9


# ===================================================================
# 12. MessageType
# ===================================================================

class TestMessageType:
    def test_all_types(self):
        expected = {"TELL", "ASK", "DELEGATE", "BCAST", "ACCEPT", "DECLINE",
                     "REPORT", "SIGNAL", "STATUS", "DISCOVER", "HEARTBEAT"}
        actual = set(t.value for t in MessageType)
        assert expected == actual

    def test_count(self):
        assert len(MessageType) == 11

    def test_is_string_enum(self):
        assert isinstance(MessageType.TELL.value, str)

    def test_all_unique(self):
        vals = [t.value for t in MessageType]
        assert len(vals) == len(set(vals))


# ===================================================================
# 13. Priority
# ===================================================================

class TestPriority:
    def test_all_levels(self):
        expected = {"LOW", "NORMAL", "HIGH", "CRITICAL"}
        actual = set(p.value for p in Priority)
        assert expected == actual

    def test_count(self):
        assert len(Priority) == 4

    def test_is_string_enum(self):
        assert isinstance(Priority.LOW.value, str)

    def test_all_unique(self):
        vals = [p.value for p in Priority]
        assert len(vals) == len(set(vals))


# ===================================================================
# 14. MessageEnvelope
# ===================================================================

class TestMessageEnvelope:
    def test_defaults(self):
        env = MessageEnvelope()
        assert env.msg_type == MessageType.TELL
        assert env.priority == Priority.NORMAL
        assert env.payload == {}
        assert env.correlation_id == ""
        assert env.ttl_seconds == 3600
        assert env.reply_to == ""

    def test_custom_creation(self):
        env = MessageEnvelope(
            msg_type=MessageType.ASK,
            priority=Priority.HIGH,
            payload={"question": "what?"},
        )
        assert env.msg_type == MessageType.ASK
        assert env.priority == Priority.HIGH
        assert env.payload["question"] == "what?"

    def test_msg_id_is_string(self):
        env = MessageEnvelope()
        assert isinstance(env.msg_id, str)
        assert len(env.msg_id) == 32  # UUID hex

    def test_is_expired_false(self):
        env = MessageEnvelope(ttl_seconds=3600)
        assert env.is_expired() is False

    def test_is_expired_true(self):
        env = MessageEnvelope(ttl_seconds=0, created_at=time.time() - 1)
        assert env.is_expired() is True

    def test_is_expired_just_created(self):
        env = MessageEnvelope(ttl_seconds=1)
        assert env.is_expired() is False

    def test_create_reply(self):
        sender = FleetAddress(name="agent-a", repo_url="https://a.com/repo")
        recipient = FleetAddress(name="agent-b", repo_url="https://b.com/repo")
        env = MessageEnvelope(
            msg_type=MessageType.ASK,
            sender=sender,
            recipient=recipient,
            priority=Priority.HIGH,
            payload={"q": "hello"},
            correlation_id="corr-123",
            ttl_seconds=600,
        )
        reply = env.create_reply(payload={"answer": "world"})
        assert reply.msg_type == MessageType.REPORT
        assert reply.sender == recipient
        assert reply.recipient == sender
        assert reply.priority == Priority.HIGH
        assert reply.payload == {"answer": "world"}
        assert reply.correlation_id == "corr-123"
        assert reply.ttl_seconds == 600
        assert reply.reply_to == env.msg_id

    def test_create_reply_custom_type(self):
        env = MessageEnvelope(msg_type=MessageType.ASK)
        reply = env.create_reply(payload={}, msg_type=MessageType.DECLINE)
        assert reply.msg_type == MessageType.DECLINE

    def test_create_reply_uses_msg_id_when_no_correlation(self):
        env = MessageEnvelope(correlation_id="")
        reply = env.create_reply(payload={})
        assert reply.correlation_id == env.msg_id

    def test_json_round_trip(self):
        env = MessageEnvelope(
            msg_type=MessageType.DELEGATE,
            sender=FleetAddress(name="a", role_pattern="worker"),
            recipient=FleetAddress(name="b"),
            priority=Priority.CRITICAL,
            payload={"task": "execute_bytecode", "data": [1, 2, 3]},
            correlation_id="corr-1",
            ttl_seconds=300,
            reply_to="original-msg",
        )
        restored = MessageEnvelope.from_json(env.to_json())
        assert restored.msg_type == MessageType.DELEGATE
        assert restored.sender.name == "a"
        assert restored.recipient.name == "b"
        assert restored.priority == Priority.CRITICAL
        assert restored.payload == {"task": "execute_bytecode", "data": [1, 2, 3]}
        assert restored.correlation_id == "corr-1"
        assert restored.ttl_seconds == 300
        assert restored.reply_to == "original-msg"

    def test_dict_round_trip(self):
        env = MessageEnvelope(
            msg_type=MessageType.HEARTBEAT,
            payload={"beat": 1},
        )
        restored = MessageEnvelope.from_dict(env.to_dict())
        assert restored.msg_type == MessageType.HEARTBEAT
        assert restored.payload == {"beat": 1}

    def test_dict_keys(self):
        env = MessageEnvelope(msg_id="id123", created_at=1000.0)
        d = env.to_dict()
        expected = {"msg_id", "msg_type", "sender", "recipient", "priority",
                     "payload", "correlation_id", "ttl_seconds", "created_at",
                     "reply_to"}
        assert set(d.keys()) == expected

    def test_all_message_types(self):
        for mt in MessageType:
            env = MessageEnvelope(msg_type=mt)
            assert env.msg_type == mt

    def test_all_priorities(self):
        for p in Priority:
            env = MessageEnvelope(priority=p)
            assert env.priority == p

    def test_from_json_minimal(self):
        env = MessageEnvelope.from_json("{}")
        assert env.msg_type == MessageType.TELL
        assert env.priority == Priority.NORMAL

    def test_custom_msg_id(self):
        env = MessageEnvelope(msg_id="custom-id")
        assert env.msg_id == "custom-id"


# ===================================================================
# 15. ISAVersion
# ===================================================================

class TestISAVersion:
    def test_str_no_label(self):
        v = ISAVersion(major=2, minor=1, patch=0)
        assert str(v) == "2.1.0"

    def test_str_with_label(self):
        v = ISAVersion(major=2, minor=1, patch=0, label="converged")
        assert str(v) == "2.1.0-converged"

    def test_repr(self):
        v = ISAVersion(major=1, minor=0, patch=0)
        assert "ISAVersion" in repr(v)

    def test_compatible_same_major(self):
        v1 = ISAVersion(2, 0, 0)
        v2 = ISAVersion(2, 5, 3)
        assert v1.compatible_with(v2) is True

    def test_compatible_different_major(self):
        v1 = ISAVersion(1, 0, 0)
        v2 = ISAVersion(2, 0, 0)
        assert v1.compatible_with(v2) is False

    def test_compatible_self(self):
        v = ISAVersion(3, 1, 4)
        assert v.compatible_with(v) is True

    def test_compatible_label_ignored(self):
        v1 = ISAVersion(1, 0, 0, label="v2")
        v2 = ISAVersion(1, 0, 0, label="unified")
        assert v1.compatible_with(v2) is True

    def test_less_than(self):
        v1 = ISAVersion(1, 0, 0)
        v2 = ISAVersion(2, 0, 0)
        assert v1 < v2

    def test_greater_than(self):
        v1 = ISAVersion(2, 0, 0)
        v2 = ISAVersion(1, 9, 9)
        assert v1 > v2

    def test_less_than_minor(self):
        v1 = ISAVersion(1, 0, 0)
        v2 = ISAVersion(1, 1, 0)
        assert v1 < v2

    def test_less_than_patch(self):
        v1 = ISAVersion(1, 0, 0)
        v2 = ISAVersion(1, 0, 1)
        assert v1 < v2

    def test_equality(self):
        v1 = ISAVersion(1, 2, 3, label="x")
        v2 = ISAVersion(1, 2, 3, label="x")
        assert v1 == v2

    def test_inequality_label(self):
        v1 = ISAVersion(1, 2, 3, label="a")
        v2 = ISAVersion(1, 2, 3, label="b")
        assert v1 != v2

    def test_hash_equality(self):
        v1 = ISAVersion(1, 2, 3, label="x")
        v2 = ISAVersion(1, 2, 3, label="x")
        assert hash(v1) == hash(v2)

    def test_json_round_trip(self):
        v = ISAVersion(2, 1, 0, label="converged")
        restored = ISAVersion.from_json(v.to_json())
        assert restored == v

    def test_dict_round_trip(self):
        v = ISAVersion(3, 5, 7)
        restored = ISAVersion.from_dict(v.to_dict())
        assert restored == v

    def test_from_dict_defaults(self):
        v = ISAVersion.from_dict({})
        assert v.major == 0
        assert v.minor == 0
        assert v.patch == 0
        assert v.label == ""

    def test_le_ge(self):
        v1 = ISAVersion(1, 0, 0)
        v2 = ISAVersion(1, 0, 0)
        assert v1 <= v2
        assert v1 >= v2

    def test_comparison_with_non_isa(self):
        v = ISAVersion(1, 0, 0)
        assert v.__lt__(42) is NotImplemented

    def test_dict_keys(self):
        v = ISAVersion(1, 2, 3, label="x")
        d = v.to_dict()
        assert set(d.keys()) == {"major", "minor", "patch", "label"}


# ===================================================================
# 16. OpcodeMapping
# ===================================================================

class TestOpcodeMapping:
    def test_basic(self):
        m = OpcodeMapping(mnemonic="ADD", source_code=1, target_code=5, format="A")
        assert m.mnemonic == "ADD"
        assert m.source_code == 1
        assert m.target_code == 5
        assert m.format == "A"

    def test_default_format(self):
        m = OpcodeMapping(mnemonic="ADD", source_code=1, target_code=5)
        assert m.format == "A"

    def test_json_round_trip(self):
        m = OpcodeMapping(mnemonic="SUB", source_code=2, target_code=10, format="B")
        restored = OpcodeMapping.from_json(m.to_json())
        assert restored == m

    def test_dict_round_trip(self):
        m = OpcodeMapping(mnemonic="MUL", source_code=3, target_code=15, format="C")
        restored = OpcodeMapping.from_dict(m.to_dict())
        assert restored.mnemonic == "MUL"
        assert restored.source_code == 3
        assert restored.target_code == 15

    def test_from_dict_defaults(self):
        m = OpcodeMapping.from_dict({"mnemonic": "X", "source_code": 1, "target_code": 2})
        assert m.format == "A"

    def test_dict_keys(self):
        m = OpcodeMapping(mnemonic="X", source_code=1, target_code=2, format="F")
        d = m.to_dict()
        assert set(d.keys()) == {"mnemonic", "source_code", "target_code", "format"}


# ===================================================================
# 17. Cross-module integration: versioning + manifest
# ===================================================================

class TestVersioningManifestIntegration:
    def test_manifest_with_version_string(self):
        m = _make_manifest(version="2.1.0")
        v = ISAVersion(2, 1, 0)
        assert str(v) == m.version

    def test_opcodes_match_opcode_mapping(self):
        mapping = OpcodeMapping(mnemonic="ADD", source_code=1, target_code=5)
        op = OpcodeSupport(opcode=5, mnemonic="ADD", format="A", implemented=True)
        assert op.opcode == mapping.target_code
        assert op.mnemonic == mapping.mnemonic


# ===================================================================
# 18. Cross-module integration: envelope + types
# ===================================================================

class TestEnvelopeTypesIntegration:
    def test_envelope_with_fleet_address(self):
        addr = FleetAddress(
            name="agent-x",
            role_pattern="*",
            capability_pattern="vm-*",
            repo_url="https://github.com/org/repo",
        )
        env = MessageEnvelope(sender=addr, recipient=addr)
        assert env.sender == addr

    def test_envelope_serialized_addresses_preserve_fields(self):
        sender = FleetAddress(name="s", role_pattern="r", capability_pattern="c", repo_url="u")
        recipient = FleetAddress(name="r2")
        env = MessageEnvelope(sender=sender, recipient=recipient)
        restored = MessageEnvelope.from_json(env.to_json())
        assert restored.sender.role_pattern == "r"
        assert restored.sender.capability_pattern == "c"
        assert restored.sender.repo_url == "u"


# ===================================================================
# 19. Edge cases and robustness
# ===================================================================

class TestEdgeCases:
    def test_empty_payload_serialization(self):
        env = MessageEnvelope(payload={})
        restored = MessageEnvelope.from_json(env.to_json())
        assert restored.payload == {}

    def test_nested_payload_serialization(self):
        env = MessageEnvelope(payload={"a": {"b": {"c": [1, 2, 3]}}})
        restored = MessageEnvelope.from_json(env.to_json())
        assert restored.payload["a"]["b"]["c"] == [1, 2, 3]

    def test_large_opcode_number(self):
        op = OpcodeSupport(opcode=999999, mnemonic="BIG", format="G")
        restored = OpcodeSupport.from_json(op.to_json())
        assert restored.opcode == 999999

    def test_manifest_with_many_opcodes(self):
        opcodes = [
            OpcodeSupport(opcode=i, mnemonic=f"OP_{i}", format="A", implemented=True)
            for i in range(100)
        ]
        m = _make_manifest(opcode_support=opcodes)
        assert m.supports_opcode(50) is True
        assert m.supports_opcode(100) is False

    def test_statusor_value_falsey_types(self):
        """Ensure False, 0, empty list don't get treated as errors."""
        result = StatusOr(value=False)
        assert result.ok()
        assert result.value is False

    def test_isa_version_zero(self):
        v = ISAVersion(0, 0, 0)
        assert str(v) == "0.0.0"
        assert v.compatible_with(ISAVersion(0, 99, 99)) is True

    def test_resource_requirements_empty_formats(self):
        r = ResourceRequirements(supported_formats=[])
        assert r.supported_formats == []
        m = _make_manifest(resource_requirements=r)
        assert m.supports_format("A") is False

    def test_compatibility_both_empty(self):
        m1 = AgentManifest(agent_name="a", agent_role="scout", version="1.0.0")
        m2 = AgentManifest(agent_name="b", agent_role="vessel", version="1.0.0")
        score = m1.compatibility_score(m2)
        # Both default to ResourceRequirements with formats [A-E], so format
        # overlap is 1.0 (0.25). Capabilities/opcodes are empty → 0.0. Trust
        # both 0.5 → 1.0*0.15. Total = 0.25 + 0 + 0 + 0.15 = 0.40
        assert abs(score - 0.40) < 1e-9


# ===================================================================
# 20. Additional coverage tests
# ===================================================================

class TestErrorCodeSpecificMembers:
    """Spot-check individual error codes exist and have expected string values."""

    def test_vm_halted(self):
        assert ErrorCode.VM_HALTED.value == "VM_HALTED"

    def test_coop_timeout(self):
        assert ErrorCode.COOP_TIMEOUT.value == "COOP_TIMEOUT"

    def test_transport_git_error(self):
        assert ErrorCode.TRANSPORT_GIT_ERROR.value == "TRANSPORT_GIT_ERROR"

    def test_trust_score_low(self):
        assert ErrorCode.TRUST_SCORE_LOW.value == "TRUST_SCORE_LOW"

    def test_spec_version_mismatch(self):
        assert ErrorCode.SPEC_VERSION_MISMATCH.value == "SPEC_VERSION_MISMATCH"

    def test_security_cap_required(self):
        assert ErrorCode.SECURITY_CAP_REQUIRED.value == "SECURITY_CAP_REQUIRED"


class TestStatusForAllErrorCodes:
    """Every error code should map to a valid Status."""

    def test_all_codes_map_to_valid_status(self):
        for ec in ErrorCode:
            status = status_for_error_code(ec.value)
            assert status in Status, f"{ec.value} maps to invalid status"

    def test_all_mapped_statuses_are_known(self):
        for ec in ErrorCode:
            status = status_for_error_code(ec.value)
            assert status.value in ALL_STATUSES


class TestFleetErrorWithAllErrorCodes:
    """FleetError can be constructed with every ErrorCode value."""

    def test_create_error_for_each_code(self):
        for ec in ErrorCode:
            err = FleetError(code=ec.value, message="test")
            assert err.code == ec.value


class TestMessageEnvelopeReplyChaining:
    """Test multi-hop reply chains."""

    def test_two_hop_reply(self):
        alice = FleetAddress(name="alice")
        bob = FleetAddress(name="bob")
        carol = FleetAddress(name="carol")

        # Alice asks Bob
        msg1 = MessageEnvelope(
            msg_type=MessageType.ASK,
            sender=alice,
            recipient=bob,
            payload={"q": "decode this"},
        )
        # Bob delegates to Carol
        msg2 = msg1.create_reply(payload={"delegated": True}, msg_type=MessageType.DELEGATE)
        assert msg2.sender == bob
        assert msg2.recipient == alice  # reply goes back to sender

        # Carol replies to Bob
        msg3 = msg2.create_reply(payload={"result": "ok"})
        assert msg3.sender == alice  # msg2's recipient
        assert msg3.recipient == bob   # msg2's sender

    def test_reply_preserves_correlation_across_chain(self):
        original = MessageEnvelope(correlation_id="chain-abc")
        reply = original.create_reply(payload={})
        assert reply.correlation_id == "chain-abc"


class TestISAVersionAdvancedComparison:
    """Additional ISAVersion comparison scenarios."""

    def test_equal_without_labels(self):
        v1 = ISAVersion(1, 2, 3)
        v2 = ISAVersion(1, 2, 3)
        assert v1 == v2
        assert not (v1 != v2)

    def test_not_equal_by_minor(self):
        v1 = ISAVersion(1, 0, 0)
        v2 = ISAVersion(1, 1, 0)
        assert v1 != v2

    def test_not_equal_by_patch(self):
        v1 = ISAVersion(1, 0, 0)
        v2 = ISAVersion(1, 0, 1)
        assert v1 != v2

    def test_greater_than_or_equal(self):
        v1 = ISAVersion(2, 0, 0)
        v2 = ISAVersion(1, 99, 99)
        assert v1 >= v2

    def test_less_than_or_equal(self):
        v1 = ISAVersion(1, 0, 0)
        v2 = ISAVersion(2, 0, 0)
        assert v1 <= v2

    def test_sort_versions(self):
        versions = [
            ISAVersion(2, 0, 0),
            ISAVersion(1, 5, 0),
            ISAVersion(1, 0, 9),
            ISAVersion(3, 0, 0),
            ISAVersion(1, 0, 1),
        ]
        sorted_versions = sorted(versions)
        assert sorted_versions[0] == ISAVersion(1, 0, 1)
        assert sorted_versions[-1] == ISAVersion(3, 0, 0)

    def test_version_in_set(self):
        v = ISAVersion(1, 2, 3, "label")
        s = {v}
        assert v in s
        assert ISAVersion(1, 2, 3, "label") in s
        assert ISAVersion(1, 2, 3) not in s  # different label

    def test_version_as_dict_key(self):
        v = ISAVersion(1, 0, 0)
        d = {v: "hello"}
        assert d[ISAVersion(1, 0, 0)] == "hello"


class TestManifestAdvanced:
    """Additional manifest edge cases."""

    def test_supports_opcode_only_implemented_not_tested(self):
        op = OpcodeSupport(opcode=10, mnemonic="DIV", format="A",
                           implemented=True, tested=False)
        m = _make_manifest(opcode_support=[op])
        assert m.supports_opcode(10) is True

    def test_manifest_with_all_roles(self):
        for role in VALID_ROLES:
            m = AgentManifest(agent_name=f"agent-{role}", agent_role=role, version="1.0.0")
            assert m.agent_role == role

    def test_manifest_trust_baseline_boundaries(self):
        m_low = AgentManifest(agent_name="a", agent_role="scout", version="1.0.0",
                              trust_baseline=0.0)
        m_high = AgentManifest(agent_name="b", agent_role="scout", version="1.0.0",
                               trust_baseline=1.0)
        assert m_low.trust_baseline == 0.0
        assert m_high.trust_baseline == 1.0

    def test_manifest_resource_requirements_embedded(self):
        rr = ResourceRequirements(max_memory_mb=4096, requires_gpu=True,
                                  supported_formats=["F"])
        m = _make_manifest(resource_requirements=rr)
        assert m.resource_requirements.max_memory_mb == 4096
        assert m.resource_requirements.requires_gpu is True
        assert m.supports_format("F") is True
        assert m.supports_format("A") is False

    def test_manifest_serialization_preserves_all_opcodes(self):
        opcodes = [
            OpcodeSupport(opcode=i, mnemonic=f"OP{i}", format="A",
                          implemented=(i % 2 == 0), tested=(i % 3 == 0))
            for i in range(20)
        ]
        m = _make_manifest(opcode_support=opcodes)
        restored = AgentManifest.from_json(m.to_json())
        assert len(restored.opcode_support) == 20
        for orig, res in zip(m.opcode_support, restored.opcode_support):
            assert orig.opcode == res.opcode
            assert orig.implemented == res.implemented
            assert orig.tested == res.tested


class TestEnvelopeTTLBoundary:
    """Test TTL expiry boundary conditions."""

    def test_not_expired_at_exact_boundary(self):
        """Message created at time T with TTL=N should not be expired at T+N."""
        now = time.time()
        env = MessageEnvelope(ttl_seconds=100, created_at=now)
        assert env.is_expired() is False

    def test_expired_one_second_past_ttl(self):
        now = time.time()
        env = MessageEnvelope(ttl_seconds=10, created_at=now - 11)
        assert env.is_expired() is True

    def test_negative_ttl(self):
        env = MessageEnvelope(ttl_seconds=-1, created_at=time.time())
        assert env.is_expired() is True


class TestStatusForErrorCodeSpecific:
    """Detailed status_for_error_code mappings."""

    def test_security_errors_map_correctly(self):
        assert status_for_error_code("SECURITY_CAP_REQUIRED") == Status.REFUSED
        assert status_for_error_code("SECURITY_CAP_DENIED") == Status.REFUSED
        assert status_for_error_code("SECURITY_SANDBOX_VIOLATION") == Status.ERROR
        assert status_for_error_code("SECURITY_UNVERIFIED_BYTECODE") == Status.REFUSED

    def test_trust_errors_map_correctly(self):
        assert status_for_error_code("TRUST_SCORE_LOW") == Status.REFUSED
        assert status_for_error_code("TRUST_POISONING") == Status.ERROR
        assert status_for_error_code("TRUST_UNKNOWN_AGENT") == Status.REFUSED
        assert status_for_error_code("TRUST_ATTESTATION_FAILED") == Status.ERROR


class TestOpcodeMappingAdvanced:
    """Additional OpcodeMapping tests."""

    def test_identity_mapping(self):
        m = OpcodeMapping(mnemonic="NOP", source_code=0, target_code=0)
        assert m.source_code == m.target_code

    def test_many_mappings(self):
        mappings = [
            OpcodeMapping(mnemonic=f"OP{i}", source_code=i, target_code=i + 100)
            for i in range(50)
        ]
        for m in mappings:
            restored = OpcodeMapping.from_json(m.to_json())
            assert restored == m

    def test_mapping_different_formats(self):
        for fmt in ["A", "B", "C", "D", "E", "F", "G"]:
            m = OpcodeMapping(mnemonic="X", source_code=1, target_code=2, format=fmt)
            assert m.format == fmt


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
