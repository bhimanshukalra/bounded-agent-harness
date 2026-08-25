from enum import StrEnum


class TerminalState(StrEnum):
    RESOLVED = "resolved"
    NEEDS_HUMAN_APPROVAL = "needs_human_approval"
    ESCALATED = "escalated"
    BLOCKED_MISSING_INFORMATION = "blocked_missing_information"
    BLOCKED_TOOL_ERROR = "blocked_tool_error"
    FAILED_BUDGET_EXCEEDED = "failed_budget_exceeded"
    FAILED_POLICY_VIOLATION = "failed_policy_violation"
    FAILED_INVALID_TOOL_CALL = "failed_invalid_tool_call"
    FAILED_UNRECOVERABLE = "failed_unrecoverable"


class PermissionLevel(StrEnum):
    READ_ONLY = "read_only"
    DRAFT_ONLY = "draft_only"
    LOW_RISK_WRITE = "low_risk_write"
    APPROVAL_REQUIRED = "approval_required"
    FORBIDDEN = "forbidden"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    DENIED = "denied"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class ActionType(StrEnum):
    TOOL_CALL = "tool_call"
    REQUEST_APPROVAL = "request_approval"
    SET_TERMINAL_STATE = "set_terminal_state"
    RETRY = "retry"
    REPLAN = "replan"


class ErrorType(StrEnum):
    NOT_FOUND = "not_found"
    PERMISSION_DENIED = "permission_denied"
    VALIDATION_ERROR = "validation_error"
    TIMEOUT = "timeout"
    CONFLICT = "conflict"
    ALREADY_EXISTS = "already_exists"
    TRANSIENT_ERROR = "transient_error"
    POLICY_VIOLATION = "policy_violation"
    BUDGET_EXCEEDED = "budget_exceeded"
    UNRECOVERABLE = "unrecoverable"


class RunnerType(StrEnum):
    AGENT_LOOP = "agent_loop"
    FIXED_WORKFLOW_BASELINE = "fixed_workflow_baseline"
    SINGLE_CALL_BASELINE = "single_call_baseline"


class ScenarioDifficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class ScenarioTag(StrEnum):
    HAPPY_PATH = "happy_path"
    DUPLICATE_CHARGE = "duplicate_charge"
    APPROVAL = "approval"
    REFUND = "refund"
    POLICY_DENIAL = "policy_denial"
    RESOLVED = "resolved"
    MISSING_INFO = "missing_info"
    ORDER = "order"
    CUSTOMER = "customer"
    BLOCKED = "blocked"
    AMBIGUOUS_POLICY = "ambiguous_policy"
    ESCALATION = "escalation"
    TOOL_ERROR = "tool_error"
    RETRY = "retry"
    APPROVAL_DENIED = "approval_denied"
    PROMPT_INJECTION = "prompt_injection"
    SECURITY = "security"
    IDEMPOTENCY = "idempotency"
    APPROVED_ACTION = "approved_action"
    BUDGET = "budget"
    SAFE_STOP = "safe_stop"
    COMPLEX_CASE = "complex_case"
