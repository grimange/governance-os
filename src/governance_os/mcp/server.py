"""Governance OS MCP server.

Exposes governed tools for AI execution agents (Codex, Claude Code, etc.).
All tool calls are recorded in an ExecutionTrace and validated at finalization.

Tools (Phase 1 — required entry-point set):
  govos_get_task_contract  — load pipeline contract, initiate governed run
  govos_read_repo_map      — read all pipeline lifecycle states
  govos_write_patch        — apply a managed file change
  govos_finalize_result    — validate and finalize the governed run

Tools (Phase 4 — expanded tool surface):
  govos_search_code        — search source code (read-only)
  govos_get_file_context   — read a file for context (read-only)
  govos_run_tests          — run pytest test suite
  govos_run_lint           — run ruff linter
  govos_record_evidence    — record evidence reference
  govos_git_status         — read git status (read-only)

Usage:
  python -m governance_os.mcp.server     # run as MCP server (stdio)
  govos-mcp                              # via project script entry point

MCP SDK: mcp>=1.0.0 (FastMCP)
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from governance_os.mcp.tools.finalize_result import govos_finalize_result
from governance_os.mcp.tools.get_file_context import govos_get_file_context
from governance_os.mcp.tools.get_task_contract import govos_get_task_contract
from governance_os.mcp.tools.git_status import govos_git_status
from governance_os.mcp.tools.read_repo_map import govos_read_repo_map
from governance_os.mcp.tools.record_evidence import govos_record_evidence
from governance_os.mcp.tools.run_lint import govos_run_lint
from governance_os.mcp.tools.run_tests import govos_run_tests
from governance_os.mcp.tools.search_code import govos_search_code
from governance_os.mcp.tools.write_patch import govos_write_patch

# ---------------------------------------------------------------------------
# FastMCP instance
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "governance-os-mcp",
    instructions=(
        "Governance OS MCP server. "
        "Begin every governed run with govos_get_task_contract. "
        "All file changes must go through govos_write_patch. "
        "End every run with govos_finalize_result. "
        "The governance validator runs at finalization and enforces policy."
    ),
)

# ---------------------------------------------------------------------------
# Phase 1 — Minimal required tool surface
# ---------------------------------------------------------------------------

mcp.tool()(govos_get_task_contract)
mcp.tool()(govos_read_repo_map)
mcp.tool()(govos_write_patch)
mcp.tool()(govos_finalize_result)

# ---------------------------------------------------------------------------
# Phase 4 — Expanded tool surface
# ---------------------------------------------------------------------------

mcp.tool()(govos_search_code)
mcp.tool()(govos_get_file_context)
mcp.tool()(govos_run_tests)
mcp.tool()(govos_run_lint)
mcp.tool()(govos_record_evidence)
mcp.tool()(govos_git_status)


# ---------------------------------------------------------------------------
# Entry points
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the MCP server in stdio transport mode."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
