// Package fleetstdlib provides shared constants that mirror the Python
// flux-fleet-stdlib error codes, status codes, and severity levels.
//
// Every Go repo in the FLUX fleet should import this package (or copy the
// constants) so that error handling uses a single taxonomy.
package fleetstdlib

// ── VM domain ────────────────────────────────────────────────────────────
const (
        ErrVMHalted          = "VM_HALTED"
        ErrVMCycleLimit      = "VM_CYCLE_LIMIT"
        ErrVMDivZero         = "VM_DIV_ZERO"
        ErrVMStackOverflow   = "VM_STACK_OVERFLOW"
        ErrVMStackUnderflow  = "VM_STACK_UNDERFLOW"
        ErrVMInvalidOpcode   = "VM_INVALID_OPCODE"
        ErrVMTypeError       = "VM_TYPE_ERROR"
        ErrVMResourceError      = "VM_RESOURCE_ERROR"
        ErrVMOutOfMemory       = "VM_OUT_OF_MEMORY"
        ErrVMUnknownInstruction = "VM_UNKNOWN_INSTRUCTION"
)

// ── COOP domain ──────────────────────────────────────────────────────────
const (
        ErrCOOPTimeout          = "COOP_TIMEOUT"
        ErrCOOPNoCapableAgent   = "COOP_NO_CAPABLE_AGENT"
        ErrCOOPTransportFailure = "COOP_TRANSPORT_FAILURE"
        ErrCOOPTaskExpired      = "COOP_TASK_EXPIRED"
        ErrCOOPAgentRefused     = "COOP_AGENT_REFUSED"
        ErrCOOPUnknownRequest     = "COOP_UNKNOWN_REQUEST"
        ErrCOOPDuplicateTask      = "COOP_DUPLICATE_TASK"
        ErrCOOPInvalidParams      = "COOP_INVALID_PARAMS"
        ErrCOOPDeserializationErr = "COOP_DESERIALIZATION_ERROR"
)

// ── TRANSPORT domain ─────────────────────────────────────────────────────
const (
        ErrTransportGitError     = "TRANSPORT_GIT_ERROR"
        ErrTransportPushFailed   = "TRANSPORT_PUSH_FAILED"
        ErrTransportPullFailed   = "TRANSPORT_PULL_FAILED"
        ErrTransportMergeConflict = "TRANSPORT_MERGE_CONFLICT"
        ErrTransportAuthFailure    = "TRANSPORT_AUTH_FAILURE"
        ErrTransportRepoNotFound   = "TRANSPORT_REPO_NOT_FOUND"
        ErrTransportRateLimited    = "TRANSPORT_RATE_LIMITED"
        ErrTransportNetworkError   = "TRANSPORT_NETWORK_ERROR"
)

// ── TRUST domain ─────────────────────────────────────────────────────────
const (
        ErrTrustScoreLow     = "TRUST_SCORE_LOW"
        ErrTrustPoisoning    = "TRUST_POISONING"
        ErrTrustUnknownAgent    = "TRUST_UNKNOWN_AGENT"
        ErrTrustAttestationFailed = "TRUST_ATTESTATION_FAILED"
)

// ── SPEC domain ──────────────────────────────────────────────────────────
const (
        ErrSpecOpcodeConflict  = "SPEC_OPCODE_CONFLICT"
        ErrSpecFormatViolation = "SPEC_FORMAT_VIOLATION"
        ErrSpecEncodingError   = "SPEC_ENCODING_ERROR"
        ErrSpecMissingHandler   = "SPEC_MISSING_HANDLER"
        ErrSpecVersionMismatch  = "SPEC_VERSION_MISMATCH"
        ErrSpecUnknownOpcode    = "SPEC_UNKNOWN_OPCODE"
)

// ── SECURITY domain ──────────────────────────────────────────────────────
const (
        ErrSecurityCapRequired      = "SECURITY_CAP_REQUIRED"
        ErrSecurityCapDenied        = "SECURITY_CAP_DENIED"
        ErrSecuritySandboxViolation = "SECURITY_SANDBOX_VIOLATION"
        ErrSecurityUnverifiedBytecode = "SECURITY_UNVERIFIED_BYTECODE"
)

// ── Status codes ─────────────────────────────────────────────────────────
const (
        StatusSuccess    = "SUCCESS"
        StatusPending    = "PENDING"
        StatusTimeout    = "TIMEOUT"
        StatusRefused    = "REFUSED"
        StatusError      = "ERROR"
        StatusCancelled  = "CANCELLED"
        StatusPartial    = "PARTIAL"
        StatusRateLimited = "RATE_LIMITED"
)

// ── Severity levels ──────────────────────────────────────────────────────
const (
        SeverityFatal   = "FATAL"
        SeverityError   = "ERROR"
        SeverityWarning = "WARNING"
        SeverityInfo    = "INFO"
)

// AllErrorCodes is the complete set of fleet error code strings.
var AllErrorCodes = []string{
        // VM
        ErrVMHalted, ErrVMCycleLimit, ErrVMDivZero, ErrVMStackOverflow,
        ErrVMStackUnderflow, ErrVMInvalidOpcode, ErrVMTypeError, ErrVMResourceError,
        ErrVMOutOfMemory, ErrVMUnknownInstruction,
        // COOP
        ErrCOOPTimeout, ErrCOOPNoCapableAgent, ErrCOOPTransportFailure,
        ErrCOOPTaskExpired, ErrCOOPAgentRefused, ErrCOOPUnknownRequest,
        ErrCOOPDuplicateTask, ErrCOOPInvalidParams, ErrCOOPDeserializationErr,
        // TRANSPORT
        ErrTransportGitError, ErrTransportPushFailed, ErrTransportPullFailed,
        ErrTransportMergeConflict, ErrTransportAuthFailure, ErrTransportRepoNotFound,
        ErrTransportRateLimited, ErrTransportNetworkError,
        // TRUST
        ErrTrustScoreLow, ErrTrustPoisoning, ErrTrustUnknownAgent,
        ErrTrustAttestationFailed,
        // SPEC
        ErrSpecOpcodeConflict, ErrSpecFormatViolation, ErrSpecEncodingError,
        ErrSpecMissingHandler, ErrSpecVersionMismatch, ErrSpecUnknownOpcode,
        // SECURITY
        ErrSecurityCapRequired, ErrSecurityCapDenied, ErrSecuritySandboxViolation,
        ErrSecurityUnverifiedBytecode,
}

// AllStatusCodes is the complete set of fleet status code strings.
var AllStatusCodes = []string{
        StatusSuccess, StatusPending, StatusTimeout, StatusRefused,
        StatusError, StatusCancelled, StatusPartial, StatusRateLimited,
}

// IsFleetErrorCode returns true if the given string is a known fleet error code.
func IsFleetErrorCode(code string) bool {
        for _, c := range AllErrorCodes {
                if c == code {
                        return true
                }
        }
        return false
}
