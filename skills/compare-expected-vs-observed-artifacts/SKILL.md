# Skill: compare-expected-vs-observed-artifacts

## 1. Purpose

Compare a defined set of expected artifacts against a provided set of observed artifacts and determine completeness, mismatch, and admissibility status.

This skill supports verification, validation, and closure preparation within Governance OS.

---

## 2. Use Cases

Use this skill when:

- verifying pipeline outputs
- validating artifact completeness
- preparing closure or declaration inputs
- detecting missing or unexpected artifacts

---

## 3. Required Inputs

- expected_artifacts (list)
- observed_artifacts (list)

Optional:
- artifact_metadata (if available)
- admissibility_rules (if defined)

---

## 4. Expected Output

```
STATUS: SUCCESS

OUTPUT:
## Status
<COMPLETE | INCOMPLETE | MISMATCH>

## Scope
<artifact sets compared>

## Matched Artifacts
- <list or NONE>

## Missing Artifacts
- <list or NONE>

## Unexpected Artifacts
- <list or NONE>

## Conclusion
<deterministic result based on comparison>
```

---

## 5. Comparison Rules

The skill MUST:

- perform exact matching unless rules specify otherwise
- treat missing expected artifacts as failure indicators
- treat unexpected artifacts as potential violations
- not assume existence of unprovided artifacts

---

## 6. Status Determination

- COMPLETE: all expected artifacts are present and no unexpected artifacts exist
- INCOMPLETE: one or more expected artifacts are missing
- MISMATCH: unexpected artifacts are present or structure deviates

---

## 7. Constraints

- no artifact invention
- no assumption of external state
- no modification of artifact lists
- no closure declaration unless explicitly requested

---

## 8. Fail-Closed Conditions

Return FAIL_CLOSED when:

- expected_artifacts is missing
- observed_artifacts is missing
- artifact lists are not in valid format
- admissibility_rules required but not provided

---

## 9. Example Fail

```
STATUS: FAIL_CLOSED
REASON: INPUT_INSUFFICIENT
DETAIL:
Missing required input: expected_artifacts
```

---

## 10. Notes

- This skill is comparison-only
- It does not generate or modify artifacts
- It supports higher-level verification and closure processes

---

## 11. Version

skill_version: v1.0.0
compatibility: governance-os >= 0.1.0
