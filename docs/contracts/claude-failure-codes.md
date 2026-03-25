# Claude Failure Codes

## 1. Purpose

Defines the canonical failure codes that Claude must use when returning a FAIL_CLOSED response within Governance OS.

These codes ensure:
- consistency
- machine-parseability
- governance alignment
- deterministic failure handling

---

## 2. Usage Rules

Claude MUST:

- use ONLY codes defined in this document
- select the MOST SPECIFIC applicable code
- not invent new codes
- not combine multiple codes
- not use lowercase or mixed case

Claude MUST NOT:

- use free-form reason text in place of codes
- omit REASON when failing
- downgrade a failure to success

---

## 3. Failure Codes

### INPUT_INSUFFICIENT

Definition:
Required task material is missing.

Examples:
- missing inputs.files
- missing expected_output
- missing required context

---

### AMBIGUOUS_TASK

Definition:
Task allows multiple materially different interpretations.

Examples:
- unclear objective
- conflicting instructions
- missing scope boundary

---

### CONSTRAINT_VIOLATION

Definition:
Task cannot be completed without breaking constraints.

Examples:
- requires speculation but constraint forbids it
- requires generating content outside allowed scope

---

### MISSING_REFERENCE

Definition:
A required reference is not provided.

Examples:
- schema file not included
- artifact path referenced but not supplied

---

### FORMAT_UNSATISFIABLE

Definition:
Requested output format cannot be produced from given inputs.

Examples:
- missing data required for required sections
- incompatible format requirements

---

### AUTHORIZATION_MISSING

Definition:
Task requires authority not granted in inputs.

Examples:
- declaring verification status without evidence
- performing closure without authorization

---

### PATH_NON_PORTABLE

Definition:
Execution would introduce non-portable paths.

Examples:
- absolute system paths
- environment-specific paths

---

### UNSUPPORTED_ASSERTION_RISK

Definition:
Task would require claims not grounded in evidence.

Examples:
- asserting completion without artifacts
- claiming verification without proof

---

## 4. Selection Guidance

When multiple failures apply:

1. Choose the earliest blocking condition
2. Prefer structural failure over semantic failure
3. Prefer INPUT_INSUFFICIENT when data is missing
4. Prefer CONSTRAINT_VIOLATION when rules conflict
5. Prefer UNSUPPORTED_ASSERTION_RISK when claims cannot be justified

---

## 5. Example Usage

```
STATUS: FAIL_CLOSED
REASON: MISSING_REFERENCE
DETAIL:
Required schema not provided: docs/contracts/frontmatter-schema.md
```

---

## 6. Version

failure_code_version: v1.0.0
compatibility: governance-os >= 0.1.0
