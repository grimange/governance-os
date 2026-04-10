# governance-os Extension Architecture

This document describes the extension model for governance-os — how profiles,
plugins, and templates are registered, discovered, and activated.

---

## Design Principles

All extensions in governance-os are:

- **First-party only** — no third-party or user-defined extensions.
- **Statically registered** — no dynamic loading, no setuptools entry-points,
  no file-system discovery.
- **Deterministic** — activation order is fixed; same inputs always produce
  the same active set.
- **Inspectable** — all registered extensions are visible via CLI and API.
- **Fail-closed** — unknown extension IDs produce warnings; invalid
  combinations produce errors.

---

## Profiles

A *profile* defines repo-level governance conventions: expected surfaces,
default active plugins, supported scaffold templates, and scaffold groups.

### Registered profiles

| ID        | Description                                          |
|-----------|------------------------------------------------------|
| `generic` | Vendor-neutral, no agent-specific assumptions (default) |
| `codex`   | Codex-oriented; adds AGENTS.md checks and session contracts |

### Resolution

```
effective profile = explicit --profile arg
                  > profile field in governance.yaml
                  > "generic" (default)
```

`resolve_profile(profile_id)` always returns a `ProfileDefinition`.
For an unknown ID it silently falls back to `GENERIC`.
Use `is_known_profile(profile_id)` to check registration without triggering
fallback behavior.

### API

```python
from governance_os.profiles import (
    PROFILES,          # dict[str, ProfileDefinition] — all registered profiles
    is_known_profile,  # is_known_profile(id: str) -> bool
    list_profiles,     # list_profiles() -> list[ProfileDefinition]
    resolve_profile,   # resolve_profile(id: str | None) -> ProfileDefinition
)
```

### CLI

```
govos profile list             # list all registered profiles
govos profile show <id>        # show details; exits 2 if not found
govos profile validate [path]  # check repo satisfies profile expected surfaces
```

---

## Plugins

A *plugin* contributes additional validation checks on top of the core runtime.
Plugins implement the `Plugin` abstract base class and are registered statically.

### Registered plugins

| ID                   | Description                                |
|----------------------|--------------------------------------------|
| `authority`          | Validates source-of-truth configuration    |
| `doctrine`           | Validates governance doctrine files        |
| `skills`             | Validates skill definitions                |
| `codex_instructions` | Codex-specific checks (AGENTS.md presence) |
| `multi_agent`        | Multi-agent role coverage checks           |

### Activation

Plugin activation is deterministic and profile-driven:

1. Start with `profile.default_plugins` (ordered).
2. Append `enabled_plugins` from `governance.yaml` (deduplicated, config order).
3. Remove `disabled_plugins` from `governance.yaml`.
4. Drop any IDs not present in `PLUGIN_REGISTRY`.

Unknown plugin IDs in `enabled_plugins` or `disabled_plugins` emit a
`PLUGIN_UNKNOWN` WARNING issue via `validate_plugin_ids()`.

### Validation

```python
from governance_os.plugins import validate_plugin_ids

issues = validate_plugin_ids(["nonexistent", "authority"])
# issues contains one WARNING for "nonexistent"
```

### API

```python
from governance_os.plugins import (
    Plugin,            # Abstract base class
    PLUGIN_REGISTRY,   # dict[str, Plugin] — all registered plugins
    is_known_plugin,   # is_known_plugin(id: str) -> bool
    list_plugins,      # list_plugins() -> list[Plugin]
    validate_plugin_ids,  # validate_plugin_ids(ids: list[str]) -> list[Issue]
)

# High-level API
import governance_os.api as api
api.plugin_list()          # list[Plugin]
api.plugin_show("skills")  # Plugin | None
```

### CLI

```
govos plugin list         # list all registered plugins
govos plugin show <id>    # show details; exits 2 if not found
```

---

## Templates

A *template* selects the scaffold content written by `govos init`.

### Registered templates

| ID            | Visible to users | Requires profile |
|---------------|-----------------|-----------------|
| `minimal`     | yes             | any              |
| `governed`    | yes             | any              |
| `multi-agent` | yes             | `codex` only    |
| `standard`    | no (internal)   | any              |

`VALID_TEMPLATES` contains only the user-facing templates.
`multi-agent` requires `--profile codex`; other combinations raise `ValueError`.

---

## Adding extensions (first-party only)

All extensions require code changes — there is no runtime registration API.

### To add a profile:

1. Define a `ProfileDefinition` in `src/governance_os/profiles/definitions.py`.
2. Register it in `PROFILES` in `src/governance_os/profiles/registry.py`.
3. Add tests to `tests/test_extension_architecture.py`.

### To add a plugin:

1. Implement `Plugin` ABC in a new file under `src/governance_os/plugins/`.
2. Instantiate and register it in `_PLUGIN_REGISTRY` in
   `src/governance_os/plugins/registry.py`.
3. Update the docstring in `src/governance_os/plugins/__init__.py`.
4. Add tests to `tests/test_extension_architecture.py`.

Third-party plugins, user-defined profiles, and entry-point discovery are
**not supported**.

---

## Issue codes

| Code             | Severity | Produced by             |
|------------------|----------|-------------------------|
| `PLUGIN_UNKNOWN` | WARNING  | `validate_plugin_ids()` |
