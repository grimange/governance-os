# governance-os Governance Contract

This document specifies the observable, stable behavior of governance-os for human
operators and automation consumers.  All sections describe **shipped behavior**, not
aspirational goals.

---

## 1. Severity Levels

Every finding produced by governance-os carries exactly one of the following severity
levels.

| Level   | Value string | Effect on command outcome |
|---------|--------------|---------------------------|
| ERROR   | `"error"`    | Blocking — command exits 1 |
| WARNING | `"warning"`  | Advisory — command exits 0 |
| INFO    | `"info"`     | Informational — command exits 0 |

### Semantics

**ERROR** — A definite governance violation that the repository must resolve before it
can be considered governed.  Examples: missing required contract sections (title, stage,
purpose, outputs, success criteria), duplicate pipeline IDs, dependency cycles, absolute
output paths, missing authority root file.

**WARNING** — A governance concern that warrants attention but does not block automated
workflows.  Examples: lifecycle drift, duplicate slugs, uncontracted surfaces, weak
success criteria, missing planner/implementer role definitions.

**INFO** — Advisory information.  No action required.  Examples: missing optional scope
declaration, no implementation notes, empty artifact directories.

---

## 2. Exit Code Contract

| Code | Meaning |
|------|---------|
| 0    | **Pass** — validation succeeded; no ERROR-severity findings present |
| 1    | **Governance failure** — one or more ERROR-severity findings found |
| 2    | **Usage / input error** — invalid argument, unrecognised resource, or bad profile/template combination |

### Per-command exit behavior

| Command | Exit 0 | Exit 1 | Exit 2 |
|---------|--------|--------|--------|
| `govos init` | scaffold applied | — | invalid profile or template |
| `govos scan` | no parse errors | parse errors present | — |
| `govos verify` | no errors | schema or graph errors | — |
| `govos status` | always | — | — |
| `govos preflight` | no errors | errors present | — |
| `govos score` | always | — | — |
| `govos portability scan` | no errors | portability errors | — |
| `govos registry build/verify` | no errors | errors | — |
| `govos audit readiness/coverage/drift/multi-agent` | no errors | errors | — |
| `govos discover candidates` | always | — | — |
| `govos authority verify` | no errors | errors | — |
| `govos skills index` | always | — | — |
| `govos skills verify` | no errors | errors | — |
| `govos doctrine validate` | no errors | errors | — |
| `govos profile list` | always | — | — |
| `govos profile show` | profile found | — | profile not found |
| `govos profile validate` | all surfaces present | surfaces missing | — |
| `govos pipeline list` | always | — | — |
| `govos pipeline status` | pipeline found | — | pipeline not found |
| `govos pipeline verify` | no drift | drift detected | pipeline not found |

**Informational commands** (status, score, discover candidates, skills index,
pipeline list) always exit 0.  They surface information without making a
pass/fail determination.

---

## 3. Report Structure

All `--json` outputs conform to this top-level contract:

```json
{
  "schema_version": "1",
  "command":        "<govos sub-command>",
  "root":           "<absolute repo path>",
  "passed":         true | false,
  ...command-specific fields...
}
```

### Field guarantees

| Field | Type | Present in | Meaning |
|-------|------|------------|---------|
| `schema_version` | `"1"` | all outputs | Increment on breaking schema changes |
| `command` | string | all outputs | Identifies which command produced the report |
| `root` | string | all outputs | Absolute path to the repository root |
| `passed` | boolean | all outputs | True when no ERROR findings present |

**`passed` semantics for informational commands:**

- `status`, `discover candidates`, `skills index`, `score`, `pipeline list` — always `true`
- `pipeline lifecycle` — `true` when no pipeline is in FAILED state

### Issue object (present in `issues`, `findings`, `parse_errors` arrays)

```json
{
  "code":        "ISSUE_CODE",
  "severity":    "error" | "warning" | "info",
  "message":     "Human-readable explanation.",
  "path":        "/absolute/path/to/file" | null,
  "pipeline_id": "001" | null,
  "suggestion":  "Remediation hint." | null
}
```

The `source` field is present when set by the originating check module; omit
otherwise.

### Additional per-command fields

**scan**: `total` (int), `error_count` (int), `pipelines[]`, `parse_errors[]`

**verify**: `error_count` (int), `pipeline_count` (int), `issues[]`

**preflight**: `checks[]` (names of checks run), `error_count` (int),
`warning_count` (int), `issues[]`

**audit**: `mode` (string), `finding_count` (int), `error_count` (int),
`warning_count` (int), `findings[]`

**portability scan**: `issue_count` (int), `issues[]`

**authority verify**: `issue_count` (int), `issues[]`

**pipeline lifecycle**: `record_count` (int), `drift_count` (int),
`failed_count` (int), `records[]`

---

## 4. Fail-Closed Behavior

governance-os is fail-closed for the following conditions:

| Condition | Behavior |
|-----------|----------|
| Contract has schema errors (missing required sections) | Classify as DRAFT; block downstream pipelines |
| Dependency cycle detected | All pipelines in the cycle classified as BLOCKED |
| Unresolvable dependency reference | Issue emitted; governance score penalised |
| Invalid profile or template combination | Command exits 2 immediately |
| Unknown pipeline ID passed to `pipeline status/verify` | Command exits 2 immediately |
| Reviewer role missing in multi-agent setup | Severity ERROR (not WARNING) |
| `govos preflight` with schema/graph errors | Exits 1; does not partially pass |

### Conditions that do NOT fail-close by design

- Missing optional fields (scope, implementation notes) → WARNING or INFO only
- Lifecycle drift (declared ≠ effective) → WARNING; does not block preflight
- Uncontracted pipeline-like surfaces → WARNING; does not block preflight
- Missing output artifacts (drift audit) → WARNING; audit drift only, not preflight

---

## 5. Stable Issue Code Prefixes

Issue codes are stable identifiers for programmatic use.  They are grouped by prefix:

| Prefix | Originating check |
|--------|-------------------|
| `MISSING_`, `DUPLICATE_`, `EMPTY_`, `STAGE_INVALID` | Schema validation |
| `PORTABILITY_`, `ABSOLUTE_PATH`, `WINDOWS_DRIVE_PATH`, `HOME_RELATIVE_PATH`, `PATH_TRAVERSAL` | Portability |
| `AUTHORITY_` | Authority check |
| `AUDIT_`, `MULTIAGENT_` | Audit modes |
| `LIFECYCLE_` | Lifecycle state machine |
| `SKILL_`, `SKILLS_` | Skills index / verify |
| `SCAFFOLD_` | Scaffold validation |

---

## 6. Schema Version

The `schema_version` field in JSON output is currently `"1"`.

It will be incremented when a backwards-incompatible change is made to a report
structure (e.g., renaming or removing a field, changing a field type).

Adding new fields to an existing report is not a breaking change and does not
require a schema version bump.

Consumers should check `schema_version` to detect structural changes in
downstream automation.
