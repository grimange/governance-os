"""Backward-compatibility shim — delegates to governance_os.scaffolding.init."""

from governance_os.scaffolding.init import ScaffoldResult, format_result, init_repo

__all__ = ["ScaffoldResult", "format_result", "init_repo"]
