"""Internal plugin system for governance-os.

Plugins add optional validation checks on top of the core runtime.
They are first-party, statically registered, and simple to inspect.

Plugins may contribute:
  - checks/validators (via run_checks())
  - profile-specific validation rules

Plugins do NOT:
  - load dynamically from user paths
  - use setuptools entry-point discovery
  - have dependency graphs or lifecycle hooks

Available plugins:
  authority          — validates source-of-truth configuration
  doctrine           — validates governance doctrine files
  skills             — validates skill definitions
  codex_instructions — Codex-specific checks (AGENTS.md)
"""
