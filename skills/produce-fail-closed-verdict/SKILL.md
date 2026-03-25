# Skill: produce-fail-closed-verdict

## 1. Purpose

Produce a minimal, deterministic FAIL_CLOSED response when a task cannot be completed within Governance OS constraints.

This skill standardizes failure behavior and prevents speculative continuation.

---

## 2. Use Cases

Use this skill when:

- required inputs are missing
- task instructions are ambiguous
- constraints prevent valid execution
- required references are not provided
- output would require unsupported assumptions

---

## 3. Required Inputs

- task_context (structured description of the task)
- detected_failure_condition (explicit reason why execution cannot proceed)

Optional:
- missing_fields (if applicable)
- violated_constraints (if applicable)
- missing_references (if applicable)

---

## 4. Expected Output

```
STATUS: FAIL_CLOSED
REASON: <VALID_REASON_CODE>
DETAIL:
<minimal grounded explanation>
```

---

## 5. Reason Code Selection

The REASON must be selected from the approved set:

- INPUT_INSUFFICIENT
- AMBIGUOUS_TASK
- CONSTRAINT_VIOLATION
- MISSING_REFERENCE
- FORMAT_UNSATISFIABLE
- AUTHORIZATION_MISSING
- PATH_NON_PORTABLE
- UNSUPPORTED_ASSERTION_RISK

---

## 6. Selection Rules

When choosing a reason code:

1. Prefer the earliest blocking condition
2. Prefer structural issues over semantic issues
3. Use INPUT_INSUFFICIENT if required data is missing
4. Use CONSTRAINT_VIOLATION if rules conflict
5. Use MISSING_REFERENCE if a named dependency is absent
6. Use UNSUPPORTED_ASSERTION_RISK if claims cannot be justified

---

## 7. Detail Rules

DETAIL must:

- be concise
- be factual
- reference the exact missing or invalid element
- not include speculation
- not include recovery suggestions unless explicitly requested

---

## 8. Constraints

- no additional output beyond FAIL_CLOSED structure
- no explanation outside DETAIL
- no task continuation
- no suggestion of next steps unless explicitly required
- no mixing multiple failure reasons

---

## 9. Fail-Closed Conditions

This skill MUST be used when:

- any required input field is missing
- task objective is not clearly bounded
- required schema or reference is absent
- expected_output cannot be satisfied
- execution would violate constraints

---

## 10. Examples

### Example 1

```
STATUS: FAIL_CLOSED
REASON: INPUT_INSUFFICIENT
DETAIL:
Missing required field: expected_output
```

### Example 2

```
STATUS: FAIL_CLOSED
REASON: MISSING_REFERENCE
DETAIL:
Required schema not provided: docs/contracts/frontmatter-schema.md
```

---

## 11. Notes

- This skill enforces governance discipline
- It is preferred over partial or speculative execution
- It ensures deterministic failure behavior

---

## 12. Version

skill_version: v1.0.0
compatibility: governance-os >= 0.1.0
