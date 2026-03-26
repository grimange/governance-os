"""Governance OS MCP server — governed tool surface for AI execution agents.

Tools expose high-level, governance-aware operations. All tool calls are
recorded in an ExecutionTrace and validated before finalization is accepted.

Entry point: governance_os.mcp.server:mcp (FastMCP instance).
Run with: python -m governance_os.mcp.server
Or via script: govos-mcp
"""
