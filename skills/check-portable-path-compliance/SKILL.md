# Skill: check-portable-path-compliance

## 1. Purpose

Detect non-portable (machine-specific or environment-specific) paths in governed artifacts and assess compliance with Governance OS portability rules.

This skill ensures repository artifacts remain portable across environments.

---

## 2. Use Cases

Use this skill when:

- validating markdown, scripts, or configs for portability
- reviewing generated artifacts before commit
- enforcing repository path normalization doctrine

---

## 3. Required Inputs

- target_content (string or file content)
- portability_rules (explicit rules or reference)

Optional:
- repository_root_alias (e.g., "./" or relative root conventions)
- allowed_path_patterns

---

## 4. Expected Output

```
STATUS: SUCCESS

OUTPUT:
## Status
<COMPLIANT | NON_COMPLIANT>

## Scope
<content evaluated>

## Findings
- <observations>

## Violations
- <list of offending paths or NONE>

## Recommendation
<portable alternatives or NONE>
```

---

## 5. Detection Rules

The skill MUST detect:

- absolute system paths (e.g., /home/user/, C:\Users\)
- environment-specific paths
- hardcoded local machine directories
- non-repository-relative paths (when rules require)

---

## 6. Compliance Rules

Content is COMPLIANT if:

- all paths are relative or repository-root based
- no machine-specific or environment-specific paths exist
- all paths conform to portability_rules

---

## 7. Constraints

- no path rewriting unless explicitly requested
- no assumption of repository structure unless provided
- no modification of source content
- no inference of missing rules

---

## 8. Fail-Closed Conditions

Return FAIL_CLOSED when:

- portability_rules are missing and required
- target_content is missing
- rules are ambiguous or conflicting

---

## 9. Example Fail

```
STATUS: FAIL_CLOSED
REASON: INPUT_INSUFFICIENT
DETAIL:
Missing required input: portability_rules
```

---

## 10. Notes

- This is a detection-only skill
- It must not modify content unless explicitly instructed
- It supports governance enforcement for portability compliance

---

## 11. Version

skill_version: v1.0.0
compatibility: governance-os >= 0.1.0
