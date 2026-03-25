# Skill: verify-frontmatter-schema

## 1. Purpose

Verify that a governed markdown file conforms exactly to the Governance OS frontmatter schema.

This skill is used to ensure metadata consistency and schema compliance for all governed documents.

---

## 2. Use Cases

Use this skill when:

- validating pipeline markdown files
- checking governance documents for required metadata
- verifying schema conformance before declaration or execution

---

## 3. Required Inputs

- target_file_content OR target_file_path
- active_frontmatter_schema (explicit definition or reference)

---

## 4. Expected Output

```
STATUS: SUCCESS

OUTPUT:
## Status
<COMPLIANT | NON_COMPLIANT>

## Scope
<file or files evaluated>

## Findings
- <list of observations>

## Violations
- <list of schema violations or NONE>

## Conclusion
<final determination>
```

---

## 5. Validation Rules

The skill MUST verify:

- presence of frontmatter block
- required fields exist
- field types are correct
- no unexpected fields (if schema is strict)
- required values are non-empty
- field naming matches schema exactly

---

## 6. Constraints

- no schema inference
- no auto-correction
- no field guessing
- no modification of source content
- no assumption of missing schema

---

## 7. Fail-Closed Conditions

Return FAIL_CLOSED when:

- schema is missing
- file content is missing
- schema reference is invalid or not provided
- frontmatter cannot be parsed deterministically

---

## 8. Example Fail

```
STATUS: FAIL_CLOSED
REASON: MISSING_REFERENCE
DETAIL:
Frontmatter schema not provided
```

---

## 9. Notes

- This skill is verification-only
- It does not modify or repair documents
- It must remain deterministic and schema-driven

---

## 10. Version

skill_version: v1.0.0
compatibility: governance-os >= 0.1.0
