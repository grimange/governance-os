# Governance

This repository is managed at the **governed** level by [governance-os](https://github.com/your-org/governance-os).

## Structure

| Path | Purpose |
|---|---|
| `governance/pipelines/` | Pipeline contract documents |
| `governance/skills/` | Reusable skill references (optional) |
| `governance/doctrine/` | Governance doctrine (optional) |
| `docs/governance/` | Governance documentation |
| `artifacts/governance/` | Governance audit artifacts and registry snapshots |
| `governance.yaml` | Governance-os configuration |

## Commands

```
govos scan                      # discover pipeline contracts
govos verify                    # validate contracts and dependency graph
govos status                    # report pipeline readiness
govos preflight                 # run all preflight checks
govos registry build            # build registry snapshot
govos registry verify           # verify registry integrity
govos audit readiness           # audit governance coverage
govos audit coverage            # audit uncontracted surfaces
govos audit drift               # audit output artifact drift
govos authority verify          # validate source-of-truth
govos discover candidates       # find ungoverned pipeline surfaces
```

## Governance maturity

This repository operates at the **governed** level:
- All pipeline stages have formal contracts
- Registry snapshots are maintained
- Authority roots are declared
- Audit coverage is monitored
