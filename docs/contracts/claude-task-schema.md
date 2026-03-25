# Claude Task Schema

## 1. Purpose

Defines the canonical input structure for tasks sent to Claude within Governance OS.

Claude must only operate on structured, bounded, and explicit task definitions.

---

## 2. Required Fields

Every task MUST include:

- task_id
- task_type
- objective
- inputs
- context
- constraints
- expected_output
- fail_closed_conditions

Missing any required field MUST trigger FAIL_CLOSED.

---

## 3. Field Definitions

### task_id
Unique identifier for the task.

### task_type
Type of task being executed.

Allowed examples:
- verification
- implementation
- analysis
- closure

---

### objective
Clear, bounded description of what must be achieved.

Must:
- be explicit
- be single-scope
- not require inference

---

### inputs
All required materials.

Examples:
- files
- raw content
- artifact lists

Claude MUST NOT assume additional inputs.

---

### context
Supporting information required to interpret inputs.

Examples:
- schema references
- governance rules
- repository mode

---

### constraints
Execution rules Claude must obey.

Common constraints:
- no speculation
- no invented files
- no scope expansion
- fail closed on missing references

---

### expected_output
Defines exact output requirements.

Must include:
- format (markdown, json, file, etc.)
- required sections (if structured)

---

### fail_closed_conditions
Explicit conditions that require failure.

Examples:
- missing_required_input
- ambiguous_task
- constraint_conflict
- missing_reference

---

## 4. Canonical Example

```yaml
task_id: verify-frontmatter-001
task_type: verification
objective: Verify that the supplied document conforms to the governance-os frontmatter contract.
inputs:
  files:
    - docs/pipelines/example.md
context:
  schema_reference: docs/contracts/frontmatter-schema.md
  repository_mode: governed
constraints:
  - no speculation
  - no invented files
  - no scope expansion
  - fail closed on missing schema reference
expected_output:
  format: markdown
  required_sections:
    - status
    - scope
    - findings
    - violations
    - conclusion
fail_closed_conditions:
  - missing_required_input
  - ambiguous_task
  - constraint_conflict
  - missing_schema_reference
```

---

## 5. Rules

Claude MUST:

- treat the schema as authoritative
- not infer missing fields
- not extend task scope
- fail closed if ambiguity exists

Claude MUST NOT:

- reinterpret task intent
- merge multiple tasks
- invent context
- bypass constraints

---

## 6. Validation Requirements

Before execution, task input must be validated for:

- presence of all required fields
- non-empty objective
- valid constraint definitions
- expected_output completeness

Invalid tasks must not be executed.

---

## 7. Version

schema_version: v1.0.0
compatibility: governance-os >= 0.1.0
