"""
Comprehensive tests for flux-fleet-stdlib.

Extends the base test suite with exhaustive coverage of every error code,
every status type, edge cases, cross-language consistency (Python ↔ Go),
serialization round-trips, and all public APIs.

Run with:  python -m pytest tests/test_stdlib_comprehensive.py -v
"""

import json
import math
import os
import re
import sys
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
    STATUS_SUCCESS, STATUS_PENDING, STATUS_TIMEOUT, STATUS_REFUSED,
    STATUS_ERROR, STATUS_CANCELLED, STATUS_PARTIAL, STATUS_RATE_LIMITED,
    _ERROR_TO_STATUS,
)
from src.types import (
    AgentId, TaskId, RepoRef, Capability, FleetAddress,
    _stable_hash,
)
import src.errors as errors_mod
import src.status as status_mod


# ===================================================================
# 1. Every ErrorCode enum member value matches its name
# ===================================================================

class TestEveryErrorCodeValue:
    """Each ErrorCode member's value should equal its name (e.g. VM_HALTED == "VM_HALTED")."""

    def test_vm_domain(self):
        codes = [
            ErrorCode.VM_HALTED, ErrorCode.VM_CYCLE_LIMIT, ErrorCode.VM_DIV_ZERO,
            ErrorCode.VM_STACK_OVERFLOW, ErrorCode.VM_STACK_UNDERFLOW,
            ErrorCode.VM_INVALID_OPCODE, ErrorCode.VM_TYPE_ERROR,
            ErrorCode.VM_RESOURCE_ERROR, ErrorCode.VM_OUT_OF_MEMORY,
            ErrorCode.VM_UNKNOWN_INSTRUCTION,
        ]
        for code in codes:
            assert code.value == code.name, f"{code.name} != {code.value}"

    def test_coop_domain(self):
        codes = [
            ErrorCode.COOP_TIMEOUT, ErrorCode.COOP_NO_CAPABLE_AGENT,
            ErrorCode.COOP_TRANSPORT_FAILURE, ErrorCode.COOP_TASK_EXPIRED,
            ErrorCode.COOP_AGENT_REFUSED, ErrorCode.COOP_UNKNOWN_REQUEST,
            ErrorCode.COOP_DUPLICATE_TASK, ErrorCode.COOP_INVALID_PARAMS,
            ErrorCode.COOP_DESERIALIZATION_ERROR,
        ]
        for code in codes:
            assert code.value == code.name

    def test_transport_domain(self):
        codes = [
            ErrorCode.TRANSPORT_GIT_ERROR, ErrorCode.TRANSPORT_PUSH_FAILED,
            ErrorCode.TRANSPORT_PULL_FAILED, ErrorCode.TRANSPORT_MERGE_CONFLICT,
            ErrorCode.TRANSPORT_AUTH_FAILURE, ErrorCode.TRANSPORT_REPO_NOT_FOUND,
            ErrorCode.TRANSPORT_RATE_LIMITED, ErrorCode.TRANSPORT_NETWORK_ERROR,
        ]
        for code in codes:
            assert code.value == code.name

    def test_trust_domain(self):
        codes = [
            ErrorCode.TRUST_SCORE_LOW, ErrorCode.TRUST_POISONING,
            ErrorCode.TRUST_UNKNOWN_AGENT, ErrorCode.TRUST_ATTESTATION_FAILED,
        ]
        for code in codes:
            assert code.value == code.name

    def test_spec_domain(self):
        codes = [
            ErrorCode.SPEC_OPCODE_CONFLICT, ErrorCode.SPEC_FORMAT_VIOLATION,
            ErrorCode.SPEC_ENCODING_ERROR, ErrorCode.SPEC_MISSING_HANDLER,
            ErrorCode.SPEC_VERSION_MISMATCH, ErrorCode.SPEC_UNKNOWN_OPCODE,
        ]
        for code in codes:
            assert code.value == code.name

    def test_security_domain(self):
        codes = [
            ErrorCode.SECURITY_CAP_REQUIRED, ErrorCode.SECURITY_CAP_DENIED,
            ErrorCode.SECURITY_SANDBOX_VIOLATION,
            ErrorCode.SECURITY_UNVERIFIED_BYTECODE,
        ]
        for code in codes:
            assert code.value == code.name

    def test_exact_count(self):
        """Total error codes should be exactly 41."""
        assert len(ErrorCode) == 41

    def test_domain_counts(self):
        """Verify exact count per domain."""
        counts = {}
        for ec in ErrorCode:
            domain = ec.value.split("_")[0]
            counts[domain] = counts.get(domain, 0) + 1
        assert counts["VM"] == 10
        assert counts["COOP"] == 9
        assert counts["TRANSPORT"] == 8
        assert counts["TRUST"] == 4
        assert counts["SPEC"] == 6
        assert counts["SECURITY"] == 4
        assert sum(counts.values()) == 41

    def test_enum_is_str_subclass(self):
        """ErrorCode values should be directly comparable to strings."""
        assert ErrorCode.VM_HALTED == "VM_HALTED"
        assert ErrorCode.VM_HALTED in ("VM_HALTED", "OTHER")

    def test_enum_iteration_order(self):
        """Enum members should be iterable."""
        members = list(ErrorCode)
        assert len(members) == 41
        assert members[0] == ErrorCode.VM_HALTED
        assert members[-1] == ErrorCode.SECURITY_UNVERIFIED_BYTECODE


# ===================================================================
# 2. ErrorCode standalone string constants
# ===================================================================

class TestErrorCodeConstants:
    """Every ERR_* constant should match its corresponding ErrorCode enum value."""

    def test_all_vm_constants(self):
        assert errors_mod.ERR_VM_HALTED == ErrorCode.VM_HALTED.value
        assert errors_mod.ERR_VM_CYCLE_LIMIT == ErrorCode.VM_CYCLE_LIMIT.value
        assert errors_mod.ERR_VM_DIV_ZERO == ErrorCode.VM_DIV_ZERO.value
        assert errors_mod.ERR_VM_STACK_OVERFLOW == ErrorCode.VM_STACK_OVERFLOW.value
        assert errors_mod.ERR_VM_STACK_UNDERFLOW == ErrorCode.VM_STACK_UNDERFLOW.value
        assert errors_mod.ERR_VM_INVALID_OPCODE == ErrorCode.VM_INVALID_OPCODE.value
        assert errors_mod.ERR_VM_TYPE_ERROR == ErrorCode.VM_TYPE_ERROR.value
        assert errors_mod.ERR_VM_RESOURCE_ERROR == ErrorCode.VM_RESOURCE_ERROR.value
        assert errors_mod.ERR_VM_OUT_OF_MEMORY == ErrorCode.VM_OUT_OF_MEMORY.value
        assert errors_mod.ERR_VM_UNKNOWN_INSTRUCTION == ErrorCode.VM_UNKNOWN_INSTRUCTION.value

    def test_all_coop_constants(self):
        assert errors_mod.ERR_COOP_TIMEOUT == ErrorCode.COOP_TIMEOUT.value
        assert errors_mod.ERR_COOP_NO_CAPABLE_AGENT == ErrorCode.COOP_NO_CAPABLE_AGENT.value
        assert errors_mod.ERR_COOP_TRANSPORT_FAILURE == ErrorCode.COOP_TRANSPORT_FAILURE.value
        assert errors_mod.ERR_COOP_TASK_EXPIRED == ErrorCode.COOP_TASK_EXPIRED.value
        assert errors_mod.ERR_COOP_AGENT_REFUSED == ErrorCode.COOP_AGENT_REFUSED.value
        assert errors_mod.ERR_COOP_UNKNOWN_REQUEST == ErrorCode.COOP_UNKNOWN_REQUEST.value
        assert errors_mod.ERR_COOP_DUPLICATE_TASK == ErrorCode.COOP_DUPLICATE_TASK.value
        assert errors_mod.ERR_COOP_INVALID_PARAMS == ErrorCode.COOP_INVALID_PARAMS.value
        assert errors_mod.ERR_COOP_DESERIALIZATION_ERROR == ErrorCode.COOP_DESERIALIZATION_ERROR.value

    def test_all_transport_constants(self):
        assert errors_mod.ERR_TRANSPORT_GIT_ERROR == ErrorCode.TRANSPORT_GIT_ERROR.value
        assert errors_mod.ERR_TRANSPORT_PUSH_FAILED == ErrorCode.TRANSPORT_PUSH_FAILED.value
        assert errors_mod.ERR_TRANSPORT_PULL_FAILED == ErrorCode.TRANSPORT_PULL_FAILED.value
        assert errors_mod.ERR_TRANSPORT_MERGE_CONFLICT == ErrorCode.TRANSPORT_MERGE_CONFLICT.value
        assert errors_mod.ERR_TRANSPORT_AUTH_FAILURE == ErrorCode.TRANSPORT_AUTH_FAILURE.value
        assert errors_mod.ERR_TRANSPORT_REPO_NOT_FOUND == ErrorCode.TRANSPORT_REPO_NOT_FOUND.value
        assert errors_mod.ERR_TRANSPORT_RATE_LIMITED == ErrorCode.TRANSPORT_RATE_LIMITED.value
        assert errors_mod.ERR_TRANSPORT_NETWORK_ERROR == ErrorCode.TRANSPORT_NETWORK_ERROR.value

    def test_all_trust_constants(self):
        assert errors_mod.ERR_TRUST_SCORE_LOW == ErrorCode.TRUST_SCORE_LOW.value
        assert errors_mod.ERR_TRUST_POISONING == ErrorCode.TRUST_POISONING.value
        assert errors_mod.ERR_TRUST_UNKNOWN_AGENT == ErrorCode.TRUST_UNKNOWN_AGENT.value
        assert errors_mod.ERR_TRUST_ATTESTATION_FAILED == ErrorCode.TRUST_ATTESTATION_FAILED.value

    def test_all_spec_constants(self):
        assert errors_mod.ERR_SPEC_OPCODE_CONFLICT == ErrorCode.SPEC_OPCODE_CONFLICT.value
        assert errors_mod.ERR_SPEC_FORMAT_VIOLATION == ErrorCode.SPEC_FORMAT_VIOLATION.value
        assert errors_mod.ERR_SPEC_ENCODING_ERROR == ErrorCode.SPEC_ENCODING_ERROR.value
        assert errors_mod.ERR_SPEC_MISSING_HANDLER == ErrorCode.SPEC_MISSING_HANDLER.value
        assert errors_mod.ERR_SPEC_VERSION_MISMATCH == ErrorCode.SPEC_VERSION_MISMATCH.value
        assert errors_mod.ERR_SPEC_UNKNOWN_OPCODE == ErrorCode.SPEC_UNKNOWN_OPCODE.value

    def test_all_security_constants(self):
        assert errors_mod.ERR_SECURITY_CAP_REQUIRED == ErrorCode.SECURITY_CAP_REQUIRED.value
        assert errors_mod.ERR_SECURITY_CAP_DENIED == ErrorCode.SECURITY_CAP_DENIED.value
        assert errors_mod.ERR_SECURITY_SANDBOX_VIOLATION == ErrorCode.SECURITY_SANDBOX_VIOLATION.value
        assert errors_mod.ERR_SECURITY_UNVERIFIED_BYTECODE == ErrorCode.SECURITY_UNVERIFIED_BYTECODE.value

    def test_constant_count_matches_enum(self):
        """There should be exactly 41 ERR_* constants matching the 41 enum members."""
        err_consts = [name for name in dir(errors_mod) if name.startswith("ERR_")]
        assert len(err_consts) == 41
        for const_name in err_consts:
            const_val = getattr(errors_mod, const_name)
            assert const_val in ALL_ERROR_CODES


# ===================================================================
# 3. Severity enum
# ===================================================================

class TestSeverityDetailed:
    def test_severity_count(self):
        assert len(Severity) == 4

    def test_severity_values_are_strings(self):
        for sev in Severity:
            assert isinstance(sev.value, str)
            assert sev == sev.value

    def test_severity_ordering(self):
        """Severity members should be iterable in definition order."""
        members = list(Severity)
        assert members[0] == Severity.FATAL
        assert members[1] == Severity.ERROR
        assert members[2] == Severity.WARNING
        assert members[3] == Severity.INFO

    def test_severity_uniqueness(self):
        vals = [s.value for s in Severity]
        assert len(vals) == len(set(vals))


# ===================================================================
# 4. Status enum and string constants
# ===================================================================

class TestStatusDetailed:
    def test_status_count(self):
        assert len(Status) == 8

    def test_status_values_are_strings(self):
        for s in Status:
            assert isinstance(s.value, str)
            assert s == s.value

    def test_status_string_constants_match_enum(self):
        assert STATUS_SUCCESS == Status.SUCCESS.value
        assert STATUS_PENDING == Status.PENDING.value
        assert STATUS_TIMEOUT == Status.TIMEOUT.value
        assert STATUS_REFUSED == Status.REFUSED.value
        assert STATUS_ERROR == Status.ERROR.value
        assert STATUS_CANCELLED == Status.CANCELLED.value
        assert STATUS_PARTIAL == Status.PARTIAL.value
        assert STATUS_RATE_LIMITED == Status.RATE_LIMITED.value

    def test_all_statuses_frozenset(self):
        expected = frozenset(s.value for s in Status)
        assert ALL_STATUSES == expected

    def test_status_iteration(self):
        members = list(Status)
        assert members[0] == Status.SUCCESS
        assert members[-1] == Status.RATE_LIMITED


# ===================================================================
# 5. status_for_error_code — exhaustive mapping
# ===================================================================

class TestStatusForAllErrorCodes:
    """Every error code should have a correct status mapping."""

    def test_vm_codes_map_to_error(self):
        vm_codes = [ec for ec in ErrorCode if ec.value.startswith("VM_")]
        for code in vm_codes:
            assert status_for_error_code(code.value) == Status.ERROR, \
                f"{code.value} should map to ERROR"

    def test_coop_timeout_codes_map_correctly(self):
        assert status_for_error_code("COOP_TIMEOUT") == Status.TIMEOUT
        assert status_for_error_code("COOP_TASK_EXPIRED") == Status.TIMEOUT

    def test_coop_refused_codes_map_correctly(self):
        assert status_for_error_code("COOP_NO_CAPABLE_AGENT") == Status.REFUSED
        assert status_for_error_code("COOP_AGENT_REFUSED") == Status.REFUSED
        assert status_for_error_code("COOP_INVALID_PARAMS") == Status.REFUSED

    def test_coop_error_codes_map_correctly(self):
        assert status_for_error_code("COOP_TRANSPORT_FAILURE") == Status.ERROR
        assert status_for_error_code("COOP_UNKNOWN_REQUEST") == Status.ERROR
        assert status_for_error_code("COOP_DUPLICATE_TASK") == Status.ERROR
        assert status_for_error_code("COOP_DESERIALIZATION_ERROR") == Status.ERROR

    def test_transport_partial(self):
        assert status_for_error_code("TRANSPORT_MERGE_CONFLICT") == Status.PARTIAL

    def test_transport_refused(self):
        assert status_for_error_code("TRANSPORT_AUTH_FAILURE") == Status.REFUSED

    def test_transport_rate_limited(self):
        assert status_for_error_code("TRANSPORT_RATE_LIMITED") == Status.RATE_LIMITED

    def test_transport_error_codes(self):
        for code in [
            "TRANSPORT_GIT_ERROR", "TRANSPORT_PUSH_FAILED", "TRANSPORT_PULL_FAILED",
            "TRANSPORT_REPO_NOT_FOUND", "TRANSPORT_NETWORK_ERROR",
        ]:
            assert status_for_error_code(code) == Status.ERROR, \
                f"{code} should map to ERROR"

    def test_trust_refused_codes(self):
        assert status_for_error_code("TRUST_SCORE_LOW") == Status.REFUSED
        assert status_for_error_code("TRUST_UNKNOWN_AGENT") == Status.REFUSED

    def test_trust_error_codes(self):
        assert status_for_error_code("TRUST_POISONING") == Status.ERROR
        assert status_for_error_code("TRUST_ATTESTATION_FAILED") == Status.ERROR

    def test_spec_codes_all_error(self):
        spec_codes = [ec for ec in ErrorCode if ec.value.startswith("SPEC_")]
        for code in spec_codes:
            assert status_for_error_code(code.value) == Status.ERROR, \
                f"{code.value} should map to ERROR"

    def test_security_refused_codes(self):
        assert status_for_error_code("SECURITY_CAP_REQUIRED") == Status.REFUSED
        assert status_for_error_code("SECURITY_CAP_DENIED") == Status.REFUSED
        assert status_for_error_code("SECURITY_UNVERIFIED_BYTECODE") == Status.REFUSED

    def test_security_error_codes(self):
        assert status_for_error_code("SECURITY_SANDBOX_VIOLATION") == Status.ERROR

    def test_unknown_code_fallback(self):
        assert status_for_error_code("TOTALLY_UNKNOWN_CODE") == Status.ERROR
        assert status_for_error_code("") == Status.ERROR
        assert status_for_error_code("vm_halted") == Status.ERROR  # case-sensitive

    def test_error_to_status_covers_all_error_codes(self):
        """Every ErrorCode should have an entry in _ERROR_TO_STATUS."""
        for ec in ErrorCode:
            assert ec.value in _ERROR_TO_STATUS, \
                f"Missing mapping for {ec.value}"


# ===================================================================
# 6. StatusOr edge cases
# ===================================================================

class TestStatusOrEdgeCases:
    def test_value_zero(self):
        """value=0 should be treated as a success (0 is falsy but valid)."""
        result = StatusOr(value=0)
        assert result.ok()
        assert result.value == 0

    def test_value_false(self):
        """value=False should be treated as a success."""
        result = StatusOr(value=False)
        assert result.ok()
        assert result.value is False

    def test_value_empty_string(self):
        """value="" should be treated as a success."""
        result = StatusOr(value="")
        assert result.ok()
        assert result.value == ""

    def test_value_empty_list(self):
        """value=[] should be treated as a success."""
        result = StatusOr(value=[])
        assert result.ok()
        assert result.value == []

    def test_value_none_explicit(self):
        """value=None with no status should default to ERROR."""
        result = StatusOr(value=None, status=Status.REFUSED, error_message="msg")
        assert not result.ok()
        assert result.status == Status.REFUSED

    def test_no_args(self):
        """StatusOr() with no arguments should be an error."""
        result = StatusOr()
        assert not result.ok()
        assert result.status == Status.ERROR

    def test_status_only(self):
        """StatusOr with only status should have empty error_message and error_code."""
        result = StatusOr(status=Status.PARTIAL)
        assert not result.ok()
        assert result.status == Status.PARTIAL
        assert result.error_message == ""
        assert result.error_code == ""

    def test_value_overrides_status(self):
        """When value is provided, it overrides any status/error info."""
        result = StatusOr(value=42, status=Status.ERROR, error_message="ignored")
        assert result.ok()
        assert result.value == 42
        assert result.error_message == ""
        assert result.error_code == ""

    def test_value_list_of_dicts(self):
        """Complex nested value should round-trip correctly."""
        val = [{"a": 1}, {"b": 2}]
        result = StatusOr(value=val)
        restored = StatusOr.from_dict(json.loads(result.to_json()))
        assert restored.ok()
        assert restored.value == val

    def test_to_dict_ok_structure(self):
        result = StatusOr(value=42)
        d = result.to_dict()
        assert "status" in d
        assert "value" in d
        assert d["status"] == "SUCCESS"
        assert d["value"] == 42
        assert "error_code" not in d
        assert "error_message" not in d

    def test_to_dict_error_structure(self):
        result = StatusOr(status=Status.TIMEOUT, error_message="slow", error_code="CODE")
        d = result.to_dict()
        assert "status" in d
        assert "error_code" in d
        assert "error_message" in d
        assert d["status"] == "TIMEOUT"
        assert "value" not in d

    def test_from_dict_minimal_error(self):
        """from_dict with only 'status' should work."""
        restored = StatusOr.from_dict({"status": "CANCELLED"})
        assert not restored.ok()
        assert restored.status == Status.CANCELLED
        assert restored.error_message == ""
        assert restored.error_code == ""

    def test_from_dict_missing_status_defaults_error(self):
        """from_dict with no 'status' key should default to ERROR."""
        restored = StatusOr.from_dict({})
        assert not restored.ok()
        assert restored.status == Status.ERROR

    def test_all_error_statuses(self):
        """Verify StatusOr works with every non-SUCCESS status."""
        for s in Status:
            if s == Status.SUCCESS:
                continue
            result = StatusOr(status=s, error_message=f"msg for {s.value}")
            assert not result.ok()
            assert result.status == s
            assert result.error_message == f"msg for {s.value}"

    def test_str_all_statuses(self):
        """Every status should appear in __str__ output."""
        for s in Status:
            if s == Status.SUCCESS:
                result = StatusOr(value=1)
                assert "OK" in str(result)
            else:
                result = StatusOr(status=s, error_message="test")
                assert s.value in str(result)


# ===================================================================
# 7. FleetError edge cases
# ===================================================================

class TestFleetErrorEdgeCases:
    def test_empty_code_and_message(self):
        """FleetError should accept empty strings."""
        err = FleetError(code="", message="")
        assert err.code == ""
        assert err.message == ""
        assert err.error_id  # still auto-generated

    def test_unicode_message(self):
        """FleetError should handle Unicode gracefully."""
        err = FleetError(code="TEST", message="Unicode: ñ é ü 🚀 你好")
        assert "🚀" in err.message
        restored = FleetError.from_json(err.to_json())
        assert restored.message == err.message

    def test_very_long_message(self):
        """FleetError should handle very long messages."""
        msg = "x" * 10000
        err = FleetError(code="TEST", message=msg)
        assert len(err.message) == 10000
        restored = FleetError.from_json(err.to_json())
        assert len(restored.message) == 10000

    def test_explicit_timestamp(self):
        err = FleetError(code="TEST", message="m", timestamp=1700000000.0)
        assert err.timestamp == 1700000000.0

    def test_explicit_error_id(self):
        err = FleetError(code="TEST", message="m", error_id="custom-id-123")
        assert err.error_id == "custom-id-123"

    def test_auto_error_id_format(self):
        """Auto-generated error_id should be 12 hex chars."""
        err1 = FleetError(code="TEST", message="m")
        assert len(err1.error_id) == 12
        assert all(c in "0123456789abcdef" for c in err1.error_id)

    def test_error_ids_are_unique(self):
        """Two FleetErrors should have different auto-generated IDs."""
        err1 = FleetError(code="TEST", message="m1")
        err2 = FleetError(code="TEST", message="m2")
        assert err1.error_id != err2.error_id

    def test_context_empty_by_default(self):
        err = FleetError(code="TEST", message="m")
        assert err.context == {}

    def test_context_preserves_types(self):
        """Context should handle various Python types."""
        ctx = {
            "int": 42,
            "float": 3.14,
            "bool": True,
            "null": None,
            "list": [1, 2, 3],
            "nested": {"a": "b"},
            "str": "hello",
        }
        err = FleetError(code="TEST", message="m", context=ctx)
        restored = FleetError.from_json(err.to_json())
        assert restored.context["int"] == 42
        assert restored.context["float"] == 3.14
        assert restored.context["bool"] is True
        assert restored.context["null"] is None
        assert restored.context["list"] == [1, 2, 3]
        assert restored.context["nested"] == {"a": "b"}
        assert restored.context["str"] == "hello"

    def test_repr_format(self):
        err = FleetError(code="VM_DIV_ZERO", message="divide by zero")
        r = repr(err)
        assert "FleetError(" in r
        assert "'VM_DIV_ZERO'" in r
        assert "'divide by zero'" in r

    def test_str_without_source(self):
        err = FleetError(code="TEST", message="just a message")
        s = str(err)
        assert "[TEST]" in s
        assert "just a message" in s
        assert "agent=" not in s

    def test_str_with_repo_only(self):
        err = FleetError(code="TEST", message="m", source_repo="my-repo")
        s = str(err)
        assert "(my-repo)" in s
        assert "agent=" not in s

    def test_str_with_agent_only(self):
        err = FleetError(code="TEST", message="m", source_agent="bot-01")
        s = str(err)
        assert "agent=bot-01" in s

    def test_is_exception(self):
        """FleetError should be catchable as a standard Exception."""
        err = FleetError(code="TEST", message="m")
        assert isinstance(err, Exception)
        try:
            raise err
        except Exception as e:
            assert isinstance(e, FleetError)

    def test_exception_args(self):
        """Exception base should get the formatted message."""
        err = FleetError(code="VM_HALTED", message="machine stopped")
        assert len(err.args) == 1
        assert "VM_HALTED" in err.args[0]

    def test_json_sort_keys(self):
        """to_json should produce sorted keys for deterministic output."""
        err = FleetError(code="TEST", message="m", source_repo="r", context={"z": 1, "a": 2})
        json_str = err.to_json()
        parsed = json.loads(json_str)
        keys = list(parsed.keys())
        assert keys == sorted(keys)

    def test_from_dict_with_extra_keys_ignored(self):
        """from_dict should ignore unknown keys."""
        d = {
            "code": "TEST",
            "message": "m",
            "extra_key": "should be ignored",
            "another_extra": 42,
        }
        err = FleetError.from_dict(d)
        assert err.code == "TEST"
        assert not hasattr(err, "extra_key")


# ===================================================================
# 8. ErrorChain edge cases
# ===================================================================

class TestErrorChainEdgeCases:
    def test_wrap_returns_self(self):
        """wrap() should return the chain for chaining."""
        chain = ErrorChain()
        result = chain.wrap(FleetError(code="A", message="a"))
        assert result is chain

    def test_from_dict_empty_errors_list(self):
        restored = ErrorChain.from_dict({"errors": []})
        assert not restored
        assert len(restored) == 0

    def test_from_dict_missing_errors_key(self):
        restored = ErrorChain.from_dict({})
        assert not restored
        assert len(restored) == 0

    def test_chain_with_many_errors(self):
        chain = ErrorChain()
        for i in range(20):
            chain.wrap(FleetError(code=f"ERR_{i}", message=f"error {i}"))
        assert len(chain) == 20
        assert chain.root().code == "ERR_0"  # type: ignore
        assert chain.outermost().code == "ERR_19"  # type: ignore

    def test_chain_round_trip_dict(self):
        e1 = fleet_error("VM_HALTED", "stopped", pc=0)
        e2 = fleet_error("COOP_TIMEOUT", "timed out", retries=5)
        chain = ErrorChain().wrap(e1).wrap(e2)
        d = chain.to_dict()
        restored = ErrorChain.from_dict(d)
        assert len(restored) == 2
        assert restored.root().code == "VM_HALTED"  # type: ignore
        assert restored.root().context["pc"] == 0  # type: ignore
        assert restored.outermost().context["retries"] == 5  # type: ignore

    def test_chain_to_json_structure(self):
        chain = ErrorChain().wrap(FleetError(code="A", message="a"))
        d = json.loads(chain.to_json())
        assert "errors" in d
        assert len(d["errors"]) == 1
        assert d["errors"][0]["code"] == "A"


# ===================================================================
# 9. Cross-language consistency (Python ↔ Go)
# ===================================================================

class TestCrossLanguageConsistency:
    """Verify Python error/status/severity codes match the Go constants file."""

    @classmethod
    def setup_class(cls):
        go_path = os.path.join(
            os.path.dirname(__file__), "..", "src", "GO_CONSTANTS.go"
        )
        with open(go_path) as f:
            cls.go_content = f.read()

    def _extract_go_string_consts(self, prefix: str) -> set:
        """Extract Go const string values matching a given prefix pattern."""
        pattern = rf'{prefix}\s*=\s*"([^"]+)"'
        return set(re.findall(pattern, self.go_content))

    def test_vm_error_codes_match_go(self):
        go_vals = self._extract_go_string_consts(r"ErrVM\w+")
        py_vals = {ec.value for ec in ErrorCode if ec.value.startswith("VM_")}
        assert go_vals == py_vals, f"Mismatch: Go={go_vals - py_vals}, Py={py_vals - go_vals}"

    def test_coop_error_codes_match_go(self):
        go_vals = self._extract_go_string_consts(r"ErrCOOP\w+")
        py_vals = {ec.value for ec in ErrorCode if ec.value.startswith("COOP_")}
        assert go_vals == py_vals

    def test_transport_error_codes_match_go(self):
        go_vals = self._extract_go_string_consts(r"ErrTransport\w+")
        py_vals = {ec.value for ec in ErrorCode if ec.value.startswith("TRANSPORT_")}
        assert go_vals == py_vals

    def test_trust_error_codes_match_go(self):
        go_vals = self._extract_go_string_consts(r"ErrTrust\w+")
        py_vals = {ec.value for ec in ErrorCode if ec.value.startswith("TRUST_")}
        assert go_vals == py_vals

    def test_spec_error_codes_match_go(self):
        go_vals = self._extract_go_string_consts(r"ErrSpec\w+")
        py_vals = {ec.value for ec in ErrorCode if ec.value.startswith("SPEC_")}
        assert go_vals == py_vals

    def test_security_error_codes_match_go(self):
        go_vals = self._extract_go_string_consts(r"ErrSecurity\w+")
        py_vals = {ec.value for ec in ErrorCode if ec.value.startswith("SECURITY_")}
        assert go_vals == py_vals

    def test_status_codes_match_go(self):
        go_vals = self._extract_go_string_consts(r"Status\w+")
        py_vals = {s.value for s in Status}
        assert go_vals == py_vals, f"Mismatch: Go={go_vals - py_vals}, Py={py_vals - go_vals}"

    def test_severity_codes_match_go(self):
        go_vals = self._extract_go_string_consts(r"Severity\w+")
        py_vals = {s.value for s in Severity}
        assert go_vals == py_vals

    def test_go_all_error_codes_list_completeness(self):
        """Verify Go AllErrorCodes list has the same count as Python."""
        match = re.search(r'var AllErrorCodes = \[\]string\{(.*?)\}', self.go_content, re.DOTALL)
        assert match
        body = match.group(1)
        go_refs = re.findall(r'Err\w+', body)
        # Strip duplicates from refs (variable names may be repeated in comments)
        go_unique = set(go_refs)
        assert len(go_unique) == 41

    def test_go_all_status_codes_list_completeness(self):
        """Verify Go AllStatusCodes list has the same count as Python."""
        match = re.search(r'var AllStatusCodes = \[\]string\{(.*?)\}', self.go_content, re.DOTALL)
        assert match
        body = match.group(1)
        go_refs = re.findall(r'Status\w+', body)
        go_unique = set(go_refs)
        assert len(go_unique) == 8


# ===================================================================
# 10. AgentId edge cases
# ===================================================================

class TestAgentIdEdgeCases:
    def test_unicode_fields(self):
        a = AgentId(name="代理-01", repo_url="https://例え.com/repo", role="执行器")
        restored = AgentId.from_json(a.to_json())
        assert restored.name == "代理-01"
        assert restored.role == "执行器"

    def test_empty_capabilities_from_dict(self):
        a = AgentId.from_dict({"name": "x", "repo_url": "y", "capabilities": []})
        assert a.capabilities == []

    def test_to_dict_structure(self):
        a = AgentId(name="a", repo_url="b", role="r", capabilities=["c1"])
        d = a.to_dict()
        assert set(d.keys()) == {"name", "repo_url", "role", "capabilities"}
        assert d["capabilities"] == ["c1"]

    def test_from_dict_extra_keys_ignored(self):
        a = AgentId.from_dict({"name": "x", "repo_url": "y", "extra": True})
        assert a.name == "x"
        assert a.repo_url == "y"

    def test_equality(self):
        a1 = AgentId(name="x", repo_url="y")
        a2 = AgentId(name="x", repo_url="y")
        a3 = AgentId(name="x", repo_url="z")
        assert a1 == a2
        assert a1 != a3


# ===================================================================
# 11. TaskId edge cases
# ===================================================================

class TestTaskIdEdgeCases:
    def test_different_agents_different_hashes(self):
        t1 = TaskId(source_agent="agent-a", timestamp=1000.0)
        t2 = TaskId(source_agent="agent-b", timestamp=1000.0)
        assert t1.unique_hash != t2.unique_hash

    def test_different_timestamps_different_hashes(self):
        t1 = TaskId(source_agent="agent-a", timestamp=1000.0)
        t2 = TaskId(source_agent="agent-a", timestamp=2000.0)
        assert t1.unique_hash != t2.unique_hash

    def test_hash_length_is_16(self):
        t = TaskId(source_agent="a", timestamp=1.0)
        assert len(t.unique_hash) == 16

    def test_hash_is_hex(self):
        t = TaskId(source_agent="a", timestamp=1.0)
        assert all(c in "0123456789abcdef" for c in t.unique_hash)

    def test_explicit_hash_preserved(self):
        t = TaskId(source_agent="a", timestamp=1.0, unique_hash="mycustomhash1")
        assert t.unique_hash == "mycustomhash1"
        restored = TaskId.from_dict(t.to_dict())
        assert restored.unique_hash == "mycustomhash1"

    def test_from_dict_minimal(self):
        t = TaskId.from_dict({"source_agent": "a"})
        assert t.source_agent == "a"
        assert t.timestamp > 0
        assert len(t.unique_hash) == 16

    def test_from_json_round_trip_preserves_timestamp(self):
        t = TaskId(source_agent="a", timestamp=12345.678, unique_hash="abcd1234efgh5678")
        restored = TaskId.from_json(t.to_json())
        assert restored.timestamp == 12345.678


# ===================================================================
# 12. RepoRef edge cases
# ===================================================================

class TestRepoRefEdgeCases:
    def test_default_branch(self):
        r = RepoRef(owner="o", name="n")
        assert r.branch == "main"

    def test_full_name_with_slash_in_name(self):
        r = RepoRef(owner="org", name="sub/project")
        assert r.full_name == "org/sub/project"

    def test_from_dict_minimal(self):
        r = RepoRef.from_dict({"owner": "o", "name": "n"})
        assert r.branch == "main"
        assert r.commit_hash == ""

    def test_empty_commit_hash(self):
        r = RepoRef(owner="o", name="n", commit_hash="")
        assert r.commit_hash == ""

    def test_round_trip_with_all_fields(self):
        r = RepoRef(owner="SuperInstance", name="flux-runtime",
                     branch="feature/test", commit_hash="a" * 40)
        restored = RepoRef.from_json(r.to_json())
        assert restored == r

    def test_to_dict_structure(self):
        r = RepoRef(owner="o", name="n", branch="b", commit_hash="c")
        d = r.to_dict()
        assert set(d.keys()) == {"owner", "name", "branch", "commit_hash"}


# ===================================================================
# 13. Capability edge cases
# ===================================================================

class TestCapabilityEdgeCases:
    def test_confidence_exactly_zero(self):
        c = Capability(name="test", confidence=0.0)
        assert c.confidence == 0.0

    def test_confidence_exactly_one(self):
        c = Capability(name="test", confidence=1.0)
        assert c.confidence == 1.0

    def test_confidence_very_small_positive(self):
        c = Capability(name="test", confidence=1e-15)
        assert c.confidence == 1e-15

    def test_confidence_very_large(self):
        c = Capability(name="test", confidence=999.0)
        assert c.confidence == 1.0

    def test_confidence_very_negative(self):
        c = Capability(name="test", confidence=-999.0)
        assert c.confidence == 0.0

    def test_default_confidence(self):
        c = Capability(name="test")
        assert c.confidence == 0.0

    def test_round_trip(self):
        c = Capability(name="deep-think", confidence=0.87, evidence_url="https://proof.io")
        restored = Capability.from_json(c.to_json())
        assert restored == c
        assert restored.confidence == 0.87

    def test_from_dict_minimal(self):
        c = Capability.from_dict({"name": "test"})
        assert c.confidence == 0.0
        assert c.evidence_url == ""


# ===================================================================
# 14. FleetAddress edge cases
# ===================================================================

class TestFleetAddressEdgeCases:
    def test_default_patterns(self):
        a = FleetAddress(name="test")
        assert a.role_pattern == "*"
        assert a.capability_pattern == "*"
        assert a.repo_url == ""

    def test_from_dict_minimal(self):
        a = FleetAddress.from_dict({"name": "target"})
        assert a.name == "target"
        assert a.role_pattern == "*"
        assert a.capability_pattern == "*"

    def test_round_trip_all_fields(self):
        a = FleetAddress(
            name="matcher",
            role_pattern="executor-*",
            capability_pattern="vm-*",
            repo_url="https://github.com/org/repo",
        )
        restored = FleetAddress.from_json(a.to_json())
        assert restored == a

    def test_to_dict_structure(self):
        a = FleetAddress(name="n", role_pattern="r", capability_pattern="c", repo_url="u")
        d = a.to_dict()
        assert set(d.keys()) == {"name", "role_pattern", "capability_pattern", "repo_url"}


# ===================================================================
# 15. _stable_hash utility
# ===================================================================

class TestStableHash:
    def test_deterministic(self):
        h1 = _stable_hash("a", "b")
        h2 = _stable_hash("a", "b")
        assert h1 == h2

    def test_different_inputs_different_hashes(self):
        h1 = _stable_hash("a", "b")
        h2 = _stable_hash("a", "c")
        assert h1 != h2

    def test_length(self):
        h = _stable_hash("test")
        assert len(h) == 16

    def test_is_hex(self):
        h = _stable_hash("test")
        assert all(c in "0123456789abcdef" for c in h)

    def test_single_part(self):
        h = _stable_hash("only_one")
        assert len(h) == 16

    def test_many_parts(self):
        h = _stable_hash("a", "b", "c", "d", "e")
        assert len(h) == 16


# ===================================================================
# 16. Public API / __init__.py exports
# ===================================================================

class TestPublicAPI:
    def test_version_exists(self):
        import src
        assert hasattr(src, "__version__")
        assert isinstance(src.__version__, str)

    def test_all_exports_exist(self):
        import src
        expected = [
            "ErrorCode", "Severity", "FleetError", "ErrorChain", "fleet_error",
            "Status", "StatusOr",
            "AgentId", "TaskId", "RepoRef", "Capability", "FleetAddress",
        ]
        for name in expected:
            assert hasattr(src, name), f"Missing export: {name}"

    def test_all_matches_actual_exports(self):
        import src
        for name in src.__all__:
            assert hasattr(src, name), f"__all__ lists {name} but it's not exported"

    def test_all_length(self):
        import src
        assert len(src.__all__) == 12


# ===================================================================
# 17. FleetError serialization with all fields
# ===================================================================

class TestFleetErrorFullSerialization:
    def test_full_field_round_trip(self):
        err = FleetError(
            code="VM_CYCLE_LIMIT",
            message="exceeded limit",
            severity=Severity.FATAL.value,
            source_repo="flux-vm",
            source_agent="runner-01",
            timestamp=1700000000.5,
            error_id="abc123def456",
            context={"cycles": 10000, "reason": "loop detected"},
        )
        json_str = err.to_json()
        restored = FleetError.from_json(json_str)
        assert restored.code == err.code
        assert restored.message == err.message
        assert restored.severity == err.severity
        assert restored.source_repo == err.source_repo
        assert restored.source_agent == err.source_agent
        assert restored.timestamp == err.timestamp
        assert restored.error_id == err.error_id
        assert restored.context == err.context

    def test_json_is_valid(self):
        """to_json should produce valid JSON."""
        err = FleetError(code="TEST", message="m")
        json_str = err.to_json()
        # Should not raise
        parsed = json.loads(json_str)
        assert isinstance(parsed, dict)


# ===================================================================
# 18. Integration: ErrorChain + StatusOr + Status
# ===================================================================

class TestDeepIntegration:
    def test_error_chain_outermost_to_statusor(self):
        e1 = fleet_error("TRANSPORT_NETWORK_ERROR", "connection reset")
        e2 = fleet_error("COOP_TRANSPORT_FAILURE", "can't reach agent")
        chain = ErrorChain().wrap(e1).wrap(e2)
        outer = chain.outermost()
        result = StatusOr(
            status=status_for_error_code(outer.code),  # type: ignore
            error_message=outer.message,  # type: ignore
            error_code=outer.code,  # type: ignore
        )
        assert not result.ok()
        assert result.status == Status.ERROR
        json_str = result.to_json()
        restored = StatusOr.from_dict(json.loads(json_str))
        assert not restored.ok()

    def test_statusor_ok_with_agent_id(self):
        agent = AgentId(name="bot", repo_url="https://github.com/org/repo")
        result = StatusOr(value=agent.to_dict())
        assert result.ok()
        restored_agent = AgentId.from_dict(result.value)
        assert restored_agent.name == "bot"

    def test_full_pipeline_error_to_json_to_statusor(self):
        """Full pipeline: create error → serialize → deserialize → StatusOr."""
        err = fleet_error(
            "SECURITY_SANDBOX_VIOLATION",
            "file access blocked",
            source_repo="guard",
            source_agent="monitor",
            path="/tmp/test",
            pid=12345,
        )
        json_str = err.to_json()
        restored_err = FleetError.from_json(json_str)
        status = status_for_error_code(restored_err.code)
        result = StatusOr(
            status=status,
            error_message=restored_err.message,
            error_code=restored_err.code,
        )
        assert not result.ok()
        assert result.status == Status.ERROR
        assert result.error_code == "SECURITY_SANDBOX_VIOLATION"


# ===================================================================
# 19. Type round-trip consistency across all types
# ===================================================================

class TestAllTypesRoundTrip:
    def test_all_types_to_json_from_json(self):
        """Every data type should survive a JSON round-trip."""
        # AgentId
        a = AgentId(name="a", repo_url="u", role="r", capabilities=["c"])
        assert AgentId.from_json(a.to_json()) == a

        # TaskId
        t = TaskId(source_agent="a", timestamp=1.0, unique_hash="0123456789abcdef")
        rt = TaskId.from_json(t.to_json())
        assert rt.source_agent == t.source_agent
        assert rt.unique_hash == t.unique_hash

        # RepoRef
        r = RepoRef(owner="o", name="n", branch="b", commit_hash="c")
        assert RepoRef.from_json(r.to_json()) == r

        # Capability
        c = Capability(name="c", confidence=0.5, evidence_url="u")
        assert Capability.from_json(c.to_json()) == c

        # FleetAddress
        fa = FleetAddress(name="n", role_pattern="r", capability_pattern="c", repo_url="u")
        assert FleetAddress.from_json(fa.to_json()) == fa

    def test_all_types_to_dict_from_dict(self):
        """Every data type should survive a dict round-trip."""
        a = AgentId(name="a", repo_url="u")
        assert AgentId.from_dict(a.to_dict()) == a

        t = TaskId(source_agent="a", timestamp=1.0, unique_hash="0123456789abcdef")
        rt = TaskId.from_dict(t.to_dict())
        assert rt.source_agent == t.source_agent
        assert rt.unique_hash == t.unique_hash

        r = RepoRef(owner="o", name="n", branch="b", commit_hash="c")
        assert RepoRef.from_dict(r.to_dict()) == r

        c = Capability(name="c", confidence=0.5)
        assert Capability.from_dict(c.to_dict()) == c

        fa = FleetAddress(name="n")
        assert FleetAddress.from_dict(fa.to_dict()) == fa


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
