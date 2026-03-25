# Skill: write-governed-markdown-lane

## 1. Purpose

Generate a fully structured Governance OS markdown lane file that conforms to canonical frontmatter and document structure requirements.

This skill is used for creating new governed pipeline lanes in a deterministic, schema-compliant format.

---

## 2. Use Cases

Use this skill when:

- creating new pipeline lanes
- generating implementation, verification, or declaration markdown files
- standardizing lane structure across the repository

---

## 3. Required Inputs

- lane_id
- title
- pipeline_stage
- pipeline_summary
- depends_on (may be empty list if allowed)
- outputs (may be empty list if allowed)

Optional:
- category
- lane
- additional metadata (only if explicitly allowed by schema)

---

## 4. Expected Output

A complete markdown file with:

1. Valid frontmatter
2. Required sections in body
3. No placeholders unless explicitly requested

Example shape:

```
STATUS: SUCCESS

OUTPUT:
---
id: <lane_id>
title: <title>
pipeline_stage: <pipeline_stage>
pipeline_summary: <pipeline_summary>
depends_on: []
outputs: []
---

## Purpose
...

## Scope
...

## Inputs
...

## Outputs
...

## Procedure
...

## Constraints
...

## Failure Conditions
...
```

---

## 5. Frontmatter Rules

- All required fields must be present
- Field names must match schema exactly
- No extra fields unless allowed
- Values must not be empty unless explicitly permitted

---

## 6. Body Structure Rules

The document MUST include:

- Purpose
- Scope
- Inputs
- Outputs
- Procedure
- Constraints
- Failure Conditions

No section may be omitted.

---

## 7. Constraints

- no invented dependencies
- no invented outputs
- no schema deviation
- no APNTalk-specific assumptions unless provided
- no placeholder text unless explicitly requested

---

## 8. Fail-Closed Conditions

Return FAIL_CLOSED when:

- lane_id is missing
- title is missing
- pipeline_stage is missing
- pipeline_summary is missing
- schema requirements are not provided but required
- required structural elements cannot be produced

---

## 9. Example Fail

```
STATUS: FAIL_CLOSED
REASON: INPUT_INSUFFICIENT
DETAIL:
Missing required field: lane_id
```

---

## 10. Notes

- This skill produces new artifacts
- It must not reference non-existent files
- It must remain deterministic and schema-aligned

---

## 11. Version

skill_version: v1.0.0
compatibility: governance-os >= 0.1.0
