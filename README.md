# flux-fleet-stdlib

**Shared error codes, status types, and common utilities for the entire FLUX fleet — the common language every repo speaks.**

## Problem

Each fleet repo invents its own error codes. `flux-coop-runtime` has `ERR_NO_CAPABLE_AGENT`, `ERR_TIMEOUT`, etc. `flux-runtime` has its own `VMError` subclasses. The Go VM has its own sentinel errors. There's no shared taxonomy, no shared codes, no way for an agent in repo A to understand an error from repo B.

## Solution

`flux-fleet-stdlib` is a shared library of error codes, status codes, and common types that every fleet repo can import.

## Error Codes

Organized by domain, 35+ canonical codes:

| Domain | Codes |
|--------|-------|
| **VM** | `VM_HALTED`, `VM_CYCLE_LIMIT`, `VM_DIV_ZERO`, `VM_STACK_OVERFLOW`, `VM_STACK_UNDERFLOW`, `VM_INVALID_OPCODE`, `VM_TYPE_ERROR`, `VM_RESOURCE_ERROR` |
| **COOP** | `COOP_TIMEOUT`, `COOP_NO_CAPABLE_AGENT`, `COOP_TRANSPORT_FAILURE`, `COOP_TASK_EXPIRED`, `COOP_AGENT_REFUSED`, `COOP_UNKNOWN_REQUEST` |
| **TRANSPORT** | `TRANSPORT_GIT_ERROR`, `TRANSPORT_PUSH_FAILED`, `TRANSPORT_PULL_FAILED`, `TRANSPORT_MERGE_CONFLICT`, `TRANSPORT_AUTH_FAILURE` |
| **TRUST** | `TRUST_SCORE_LOW`, `TRUST_POISONING`, `TRUST_UNKNOWN_AGENT` |
| **SPEC** | `SPEC_OPCODE_CONFLICT`, `SPEC_FORMAT_VIOLATION`, `SPEC_ENCODING_ERROR`, `SPEC_MISSING_HANDLER` |
| **SECURITY** | `SECURITY_CAP_REQUIRED`, `SECURITY_CAP_DENIED`, `SECURITY_SANDBOX_VIOLATION`, `SECURITY_UNVERIFIED_BYTECODE` |

## Status Codes

`SUCCESS`, `PENDING`, `TIMEOUT`, `REFUSED`, `ERROR`, `CANCELLED`, `PARTIAL`, `RATE_LIMITED`

## Python Usage

```python
from src.errors import ErrorCode, fleet_error, FleetError, ErrorChain
from src.status import Status, StatusOr, status_for_error_code
from src.types import AgentId, TaskId, RepoRef, Capability, FleetAddress

# Creating errors
err = fleet_error(
    ErrorCode.VM_CYCLE_LIMIT.value,
    "Agent exceeded 10,000 cycles",
    source_repo="flux-coop-runtime",
    source_agent="executor-01",
    cycle_count=10247,
)

# Serializing for wire transport
json_blob = err.to_json()

# Deserializing in another repo
restored = FleetError.from_json(json_blob)
print(restored.code, restored.context["cycle_count"])

# Error chains (causal history)
chain = ErrorChain()
chain.wrap(fleet_error("TRANSPORT_GIT_ERROR", "clone failed"))
chain.wrap(fleet_error("COOP_TRANSPORT_FAILURE", "could not contact agent"))
print(chain.root().code)      # TRANSPORT_GIT_ERROR
print(chain.outermost().code)  # COOP_TRANSPORT_FAILURE

# StatusOr (like Rust's Result)
result = StatusOr(value=42)
if result.ok():
    print(result.value)  # 42

result = StatusOr(status=Status.REFUSED, error_message="nope", error_code="COOP_AGENT_REFUSED")
if not result.ok():
    print(result.error_code)

# Convert error codes to statuses
status = status_for_error_code("COOP_TIMEOUT")  # Status.TIMEOUT

# Shared types — all support JSON round-trips
agent = AgentId(name="executor-01", repo_url="https://github.com/SuperInstance/flux-runtime",
                role="vm-executor", capabilities=["vm-run", "bytecode-verify"])
print(agent.to_json())

cap = Capability(name="vm-run", confidence=0.95)
print(cap.confidence)  # 0.95 (auto-clamped to [0.0, 1.0])
```

## Go Usage

The file `src/GO_CONSTANTS.go` contains the same error codes, status codes, and severity levels as Go `const` strings:

```go
package main

import (
    "fmt"
    fleet "flux-fleet-stdlib/src"  // or copy the constants
)

func main() {
    if fleet.IsFleetErrorCode(code) {
        fmt.Println("Known fleet error:", code)
    }
    fmt.Println(fleet.ErrCOOPTimeout)       // "COOP_TIMEOUT"
    fmt.Println(fleet.StatusRefused)        // "REFUSED"
    fmt.Println(fleet.SeverityFatal)        // "FATAL"
}
```

## Shared Types

| Type | Fields | Purpose |
|------|--------|---------|
| `AgentId` | `name`, `repo_url`, `role`, `capabilities` | Unique agent identity |
| `TaskId` | `source_agent`, `timestamp`, `unique_hash` | Opaque task identifier |
| `RepoRef` | `owner`, `name`, `branch`, `commit_hash` | Git repository pointer |
| `Capability` | `name`, `confidence` (0.0–1.0), `evidence_url` | Named capability with score |
| `FleetAddress` | `name`, `role_pattern`, `capability_pattern`, `repo_url` | Fleet routing address |

All types support `to_json()` / `from_json()` serialization.

## Running Tests

```bash
cd flux-fleet-stdlib
python -m pytest tests/test_stdlib.py -v
```

## Design Principles

1. **Same strings everywhere** — error code values are plain strings (`"COOP_TIMEOUT"`) that work as Python enum values, Go constants, and Rust `&str` constants.
2. **Zero dependencies** — stdlib only. No external packages.
3. **Wire-ready** — every type has JSON serialization for git-based message transport.
4. **Rich context** — `FleetError` carries `source_repo`, `source_agent`, `timestamp`, `error_id`, and an arbitrary `context` dict.
5. **Composable** — `ErrorChain` wraps nested errors. `StatusOr<T>` wraps success/failure.

## Version

0.1.0 — initial release.
