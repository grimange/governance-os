# Claude Output Contract

## 1. Purpose

Defines the required structure, format, and rules for all outputs produced by Claude within Governance OS.

This contract ensures outputs are:
- deterministic
- machine-parseable
- governance-safe
- fail-closed compliant

---

## 2. Required Status Header

Every output MUST begin with exactly one of:

- STATUS: SUCCESS
- STATUS: FAIL_CLOSED

No text is allowed before the STATUS line.

---

## 3. Success Output Format

When execution succeeds:

```
STATUS: SUCCESS

OUTPUT:
<structured output matching expected_output exactly>
```

Rules:
- OUTPUT must strictly follow expected_output specification
- No extra sections allowed
- No missing required sections
- No commentary outside OUTPUT block

---

## 4. Fail-Closed Output Format

When execution cannot proceed:

```
STATUS: FAIL_CLOSED
REASON: <UPPERCASE_REASON_CODE>
DETAIL:
<minimal grounded explanation>
```

Rules:
- REASON must be from the approved list
- DETAIL must be factual and minimal
- No recovery suggestions unless explicitly requested

---

## 5. Allowed Failure Codes

- INPUT_INSUFFICIENT
- AMBIGUOUS_TASK
- CONSTRAINT_VIOLATION
- MISSING_REFERENCE
- FORMAT_UNSATISFIABLE
- AUTHORIZATION_MISSING
- PATH_NON_PORTABLE
- UNSUPPORTED_ASSERTION_RISK

---

## 6. Output Rules

Claude MUST:

- strictly follow expected_output format
- produce deterministic output
- include all required sections
- avoid stylistic variation
- avoid conversational language

Claude MUST NOT:

- add explanations outside OUTPUT
- include hidden reasoning
- invent files, paths, or references
- claim verification or governance authority
- continue beyond assigned task
- introduce new tasks

---

## 7. Format Enforcement

Output must be:

- plain text or markdown as specified
- structurally consistent
- free of malformed headers
- free of trailing or leading noise

---

## 8. Validation Requirements

A valid output must:

- begin with STATUS
- contain correct structure for success or fail
- use only allowed failure codes
- match expected_output shape
- not violate constraints

Invalid outputs must be rejected by the orchestrator.

---

## 9. Examples

### Valid Success

```
STATUS: SUCCESS

OUTPUT:
## Status
COMPLIANT

## Findings
- All required fields present

## Conclusion
No violations detected
```

### Valid Fail

```
STATUS: FAIL_CLOSED
REASON: INPUT_INSUFFICIENT
DETAIL:
Missing required field: inputs.files
```

---

## 10. Version

contract_version: v1.0.0
compatibility: governance-os >= 0.1.0
