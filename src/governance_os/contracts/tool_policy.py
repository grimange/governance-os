"""Tool policy contract schema for governance-os MCP.

A ToolPolicy defines what tool usage is required, what is forbidden,
and what must be present for a run to be considered valid.

Policies are loaded from profiles and applied to execution traces by the validator.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from governance_os.contracts.failure_codes import FailureCode


class ToolPolicy(BaseModel):
    """Governance policy constraining which tools must be used and in what order.

    All fields have safe defaults. Stricter policies narrow the allowed tool surface
    and add sequence and evidence requirements.
    """

    mode: str = "standard_code_change"
    """Human-readable policy mode identifier. Used in reporting and traces."""

    fail_code_on_missing: FailureCode = FailureCode.TOOLING_UNAVAILABLE_FAIL_CLOSED
    """Failure code emitted when required tooling is absent at run start."""

    allowed_tools: list[str] = Field(default_factory=list)
    """Explicit allowlist of tool names. Empty list means all tools are allowed."""

    required_tools: list[str] = Field(default_factory=list)
    """Tools that MUST appear in the execution trace for the run to be valid."""

    forbidden_command_classes: list[str] = Field(default_factory=list)
    """Classes of action that are forbidden.

    Recognised classes:
    - ``unmanaged_write``: file changes outside govos_write_patch
    - ``direct_shell``: raw shell execution not via governed tools
    - ``destructive_git``: force-push, reset --hard, branch -D, etc.
    """

    required_sequence: list[str] = Field(default_factory=list)
    """Ordered list of tool names that must appear in this relative order.

    Tools not in this list may appear at any position.
    Only the relative order of listed tools is enforced.
    """

    required_before_complete: list[str] = Field(default_factory=list)
    """Tools that must have been called before finalization is accepted."""

    completion_requirements: list[str] = Field(default_factory=list)
    """Human-readable criteria that must be satisfied before finalization.

    These are for documentation and reporting; machine enforcement uses
    required_tools, required_sequence, and required_before_complete.
    """

    model_config = {"frozen": True}


# ---------------------------------------------------------------------------
# Built-in policies (correspond to Phase 6 profiles)
# ---------------------------------------------------------------------------


READ_ONLY_AUDIT: ToolPolicy = ToolPolicy(
    mode="read_only_audit",
    required_tools=[
        "govos_get_task_contract",
        "govos_read_repo_map",
        "govos_finalize_result",
    ],
    forbidden_command_classes=["unmanaged_write", "direct_shell"],
    required_sequence=[
        "govos_get_task_contract",
        "govos_finalize_result",
    ],
    required_before_complete=["govos_finalize_result"],
    completion_requirements=[
        "Contract loaded via govos_get_task_contract.",
        "Repo map read via govos_read_repo_map.",
        "Run finalized via govos_finalize_result.",
    ],
)

STANDARD_CODE_CHANGE: ToolPolicy = ToolPolicy(
    mode="standard_code_change",
    required_tools=[
        "govos_get_task_contract",
        "govos_read_repo_map",
        "govos_write_patch",
        "govos_finalize_result",
    ],
    forbidden_command_classes=["unmanaged_write"],
    required_sequence=[
        "govos_get_task_contract",
        "govos_write_patch",
        "govos_finalize_result",
    ],
    required_before_complete=["govos_write_patch", "govos_finalize_result"],
    completion_requirements=[
        "Contract loaded via govos_get_task_contract.",
        "All file changes applied via govos_write_patch.",
        "Run finalized via govos_finalize_result.",
    ],
)

HIGH_ASSURANCE_RELEASE: ToolPolicy = ToolPolicy(
    mode="high_assurance_release",
    required_tools=[
        "govos_get_task_contract",
        "govos_read_repo_map",
        "govos_write_patch",
        "govos_run_tests",
        "govos_record_evidence",
        "govos_finalize_result",
    ],
    forbidden_command_classes=["unmanaged_write", "direct_shell"],
    required_sequence=[
        "govos_get_task_contract",
        "govos_write_patch",
        "govos_run_tests",
        "govos_record_evidence",
        "govos_finalize_result",
    ],
    required_before_complete=[
        "govos_run_tests",
        "govos_record_evidence",
        "govos_finalize_result",
    ],
    completion_requirements=[
        "Contract loaded via govos_get_task_contract.",
        "All file changes applied via govos_write_patch.",
        "Tests executed and passed via govos_run_tests.",
        "Evidence recorded via govos_record_evidence.",
        "Run finalized via govos_finalize_result.",
    ],
)

# Registry: mode name → policy
POLICY_REGISTRY: dict[str, ToolPolicy] = {
    READ_ONLY_AUDIT.mode: READ_ONLY_AUDIT,
    STANDARD_CODE_CHANGE.mode: STANDARD_CODE_CHANGE,
    HIGH_ASSURANCE_RELEASE.mode: HIGH_ASSURANCE_RELEASE,
}
