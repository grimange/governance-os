# Governance Doctrine

**Version:** 1.0.0
**Authority:** <!-- name or role -->

## Purpose

Describe the purpose and scope of this governance doctrine.

## Principles

1. **Principle Name** — Description of the governance principle.
2. **Principle Name** — Description of the governance principle.

## Required Practices

- [ ] All pipeline stages must have formal contracts.
- [ ] All contracts must declare explicit outputs and success criteria.
- [ ] Dependency declarations must use numeric ids.
- [ ] All output paths must be repo-relative (no absolute paths).

## Prohibited Practices

- [ ] No pipeline may declare outputs outside the repository root.
- [ ] No contract may be stored inside an artifacts directory.

## Governance Roles

| Role | Responsibility |
|---|---|
| Operator | Executes governed pipeline stages |
| Reviewer | Validates contract completeness |
| Authority | Owns governance doctrine |

## Change Policy

Doctrine changes require:
1. Author a change proposal.
2. Review by authority role.
3. Version increment.
4. Re-validation of all contracts against new doctrine.
