# Fleet-Stdlib Adoption Guide

Step-by-step migration instructions for integrating `flux-fleet-stdlib` into
fleet repositories.  This guide covers `flux-coop-runtime`, `flux-sandbox`,
and any future repo that needs canonical error codes or status types.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Install fleet-stdlib](#install-fleet-stdlib)
3. [Migrate flux-coop-runtime](#migrate-flux-coop-runtime)
4. [Migrate flux-sandbox](#migrate-flux-sandbox)
5. [Common Patterns](#common-patterns)
6. [Rollback Strategy](#rollback-strategy)

---

## Prerequisites

- Python 3.10+
- `flux-fleet-stdlib` source at a path importable as `flux_fleet_stdlib`

---

## Install fleet-stdlib

If using a workspace layout (all repos share a parent directory), add the
stdlib to your `PYTHONPATH` or install it in editable mode:

```bash
# Option A: PYTHONPATH
export PYTHONPATH="/home/z/my-project/repos/flux-fleet-stdlib/src:$PYTHONPATH"

# Option B: pip editable install
cd /home/z/my-project/repos/flux-fleet-stdlib
pip install -e .
```

Verify the import works:

```python
from flux_fleet_stdlib import ErrorCode, FleetError, Status
print(ErrorCode.COOP_TIMEOUT)  # COOP_TIMEOUT
```

---

## Migrate flux-coop-runtime

### Step 1: Add the compat shim

The file `src/fleet_compat.py` is already provided.  It re-exports all
legacy names so no existing code breaks immediately.

### Step 2: Redirect imports (mechanical find-and-replace)

| Before | After |
|--------|-------|
| `from src.runtime import ERR_NO_CAPABLE_AGENT` | `from src.fleet_compat import ERR_NO_CAPABLE_AGENT` |
| `from src.runtime import CooperativeRuntimeError` | `from src.fleet_compat import CooperativeRuntimeError` |

### Step 3: Use structured errors (recommended)

**Before:**

```python
from src.runtime import CooperativeRuntimeError, ERR_TIMEOUT

raise CooperativeRuntimeError(
    f"{ERR_TIMEOUT}: No response from {agent} within {timeout_ms}ms"
)
```

**After:**

```python
from src.fleet_compat import CooperativeRuntimeError, ErrorCode

raise CooperativeRuntimeError(
    code=ErrorCode.COOP_TIMEOUT.value,
    message=f"No response from {agent} within {timeout_ms}ms",
    source_agent=agent,
    context={"timeout_ms": timeout_ms},
)
```

### Step 4: Wrap legacy exceptions at boundaries

At transport / external boundaries, wrap old-style exceptions:

```python
from src.fleet_compat import to_fleet_error

try:
    transport.send_task(task)
except GitTransportError as exc:
    raise to_fleet_error(exc, default_code="TRANSPORT_GIT_ERROR")
```

### Step 5: Use fleet Status for responses

**Before:**

```python
return CooperativeResponse.error(
    task_id=task.task_id,
    source_agent=self.transport.agent_name,
    target_agent=task.source_agent,
    error_code="TASK_EXPIRED",
    error_message="Task has expired",
)
```

**After:**

```python
from src.fleet_compat import ERR_TASK_EXPIRED

return CooperativeResponse.error(
    task_id=task.task_id,
    source_agent=self.transport.agent_name,
    target_agent=task.source_agent,
    error_code=ERR_TASK_EXPIRED,  # now "COOP_TASK_EXPIRED"
    error_message="Task has expired",
)
```

### Error code mapping reference

| Old constant | Old value | New value (fleet-stdlib) |
|---|---|---|
| `ERR_NO_CAPABLE_AGENT` | `"NO_CAPABLE_AGENT"` | `"COOP_NO_CAPABLE_AGENT"` |
| `ERR_TIMEOUT` | `"TIMEOUT"` | `"COOP_TIMEOUT"` |
| `ERR_TRANSPORT_FAILURE` | `"TRANSPORT_FAILURE"` | `"TRANSPORT_GIT_ERROR"` |
| `ERR_TASK_EXPIRED` | `"TASK_EXPIRED"` | `"COOP_TASK_EXPIRED"` |
| `ERR_AGENT_REFUSED` | `"AGENT_REFUSED"` | `"COOP_AGENT_REFUSED"` |

---

## Migrate flux-sandbox

### Step 1: Add the compat shim

The file `src/fleet_compat.py` is already provided.

### Step 2: Map FailureType to fleet Status

**Before:**

```python
from src.failure.injector import FailureType

if failure_type == FailureType.TIMEOUT:
    # handle timeout ...
```

**After:**

```python
from src.fleet_compat import failure_to_fleet_status

fleet_status = failure_to_fleet_status(FailureType.TIMEOUT)
# fleet_status == Status.TIMEOUT
```

### Step 3: Annotate simulation results with fleet codes

**Before:**

```python
result = SimulationResult(scenario_name=name)
# result.error is a plain string, no structured codes
```

**After:**

```python
from src.fleet_compat import simulation_result_to_status, enrich_step_record_fleet

fleet_status = simulation_result_to_status(
    has_error=(result.error is not None),
    completed_all_steps=(len(harness.message_queue) == 0),
    max_steps_reached=(step_count >= max_steps),
)

# Enrich individual step records for JSON export:
for step in result.steps:
    fleet_enriched = enrich_step_record_fleet(
        dataclasses.asdict(step),
        failure=step.failure,
    )
```

### Step 4: Wrap simulation errors in FleetError

```python
from src.fleet_compat import simulation_error

try:
    agent.receive(message)
except Exception as exc:
    raise simulation_error(
        code="COOP_TRANSPORT_FAILURE",
        message=str(exc),
        scenario_name=scenario.name,
        step_num=step_num,
        agent_name=agent_name,
    )
```

### FailureType mapping reference

| FailureType | fleet Status | fleet ErrorCode |
|---|---|---|
| `TIMEOUT` | `TIMEOUT` | `COOP_TIMEOUT` |
| `MESSAGE_LOSS` | `ERROR` | `TRANSPORT_NETWORK_ERROR` |
| `DUPLICATE` | `PARTIAL` | `COOP_TRANSPORT_FAILURE` |
| `DELAYED` | `PENDING` | `COOP_TIMEOUT` |
| `CORRUPTED` | `ERROR` | `COOP_DESERIALIZATION_ERROR` |

---

## Common Patterns

### Pattern 1: Raising a fleet error with context

```python
from flux_fleet_stdlib import ErrorCode, fleet_error

raise fleet_error(
    ErrorCode.COOP_NO_CAPABLE_AGENT.value,
    f"Cannot resolve target '{target}'",
    source_repo="flux-coop-runtime",
    source_agent=self.transport.agent_name,
    target=target,
    min_confidence=0.5,
)
```

### Pattern 2: Returning StatusOr from handlers

```python
from flux_fleet_stdlib import Status, StatusOr

def handle_task(task):
    if task.is_expired():
        return StatusOr(status=Status.TIMEOUT, error_message="task expired")
    result = execute(task)
    return StatusOr(value=result)
```

### Pattern 3: Error chains for wrapped transport errors

```python
from flux_fleet_stdlib import ErrorCode, ErrorChain, FleetError

chain = ErrorChain()
chain.wrap(FleetError(
    code=ErrorCode.TRANSPORT_GIT_ERROR,
    message="git push failed: remote refs rejected",
    source_repo="flux-coop-runtime",
))
chain.wrap(FleetError(
    code=ErrorCode.COOP_TRANSPORT_FAILURE,
    message="Failed to send cooperative task",
    source_repo="flux-coop-runtime",
))
# chain.root() -> the git error
# chain.outermost() -> the coop error
```

### Pattern 4: Cross-repo error comparison

```python
from flux_fleet_stdlib import ErrorCode

# Any repo can check error codes consistently:
if response.error_code == ErrorCode.COOP_TIMEOUT.value:
    retry_with_longer_timeout()
```

---

## Rollback Strategy

### Reverting flux-coop-runtime

1. Revert imports back to `from src.runtime import ...`
2. The old `CooperativeRuntimeError` class and `ERR_*` constants in
   `runtime.py` are **unchanged** — they remain fully functional.
3. Delete `src/fleet_compat.py`.
4. No data migration is needed; error codes in serialized messages may
   show the new fleet-standard values but consumers should handle both
   old and new codes during the transition window.

### Reverting flux-sandbox

1. Remove `from src.fleet_compat import ...` statements.
2. The original `FailureType` enum and `SimulationHarness` are untouched.
3. Delete `src/fleet_compat.py`.
4. Any enriched JSON exports containing `fleet_status` / `fleet_error_code`
   fields can be safely ignored by old consumers (extra keys are harmless).

### Gradual migration (recommended)

Both compat shims support a **soft migration** path:

- Old-style `raise CooperativeRuntimeError("TIMEOUT: ...")` calls work
  without changes because the shim parses the legacy string format.
- New structured calls coexist alongside old ones.
- Adopt repo-by-repo, file-by-file — no big-bang requirement.
- Run tests after each file migration to catch edge cases.
