# ORC-003 — Multi-Agent Plan Execution Isolation

---

## Identity

| Field              | Value |
|--------------------|-------|
| **Experiment ID**  | ORC-003 |
| **Domain**         | orchestration |
| **Tier**           | 1 (offline — no API key, no Docker) |
| **Status**         | defined |
| **Claimed by**     | unclaimed |
| **Depends on**     | ORC-002 |
| **Estimated cost** | $0.00 (offline) |
| **Estimated time** | 10 minutes |

---

## Research Question

Do multiple agents in a single plan share any mutable state?

---

## Hypothesis

Two agents executing in the same plan cannot read or write each other's ScopedContext.

---

## What This Experiment Measures

> TODO: Fill in a 3–5 sentence plain-language description of what
> this experiment actually does. See EXPERIMENT_TEMPLATE.md for guidance.

---

## Metrics

| Metric Key | Type | Unit | Description |
|------------|------|------|-------------|
| `total_runs` | int | — | Total iterations executed |
| `pass_count` | int | — | Iterations matching expected behaviour |
| `fail_count` | int | — | Iterations deviating from expected behaviour |
| `pass_rate`  | float | ratio 0–1 | pass_count / total_runs |

> TODO: Add experiment-specific metrics above.

---

## Prerequisites

**Tier 1 — satisfied by RESEARCH_SETUP.md:**
- [ ] Python virtual environment active
- [ ] `pip install -r requirements.txt` complete
- [ ] `pip install -r requirements-dev.txt` complete
- [ ] DAF importable (`python -c "import daf"` succeeds)
- [ ] Research infrastructure importable

**Additional prerequisites:** None — base setup is sufficient.

---

## Preparation Steps

1. Navigate to the DAF project root and activate venv:
   ```bash
   cd /path/to/daf
   source .venv/bin/activate   # Linux/macOS
   source .venv/Scripts/activate  # Windows Git Bash
   ```

2. Verify readiness:
   ```bash
   python -c "from experiments.orchestration.ORC_003.experiment import ORC_003; print('ready')"
   ```
   Expected output: `ready`

> TODO: Add any experiment-specific preparation steps.

---

## Execution

```bash
python -m daf.research.runner experiments/orchestration/ORC_003/experiment.py
```

**Expected duration:** 10 minutes
**Expected cost:** $0.00 (offline)

---

## Result Recording

```
findings/ORC-003/ORC-003_run_NNN.log
findings/ORC-003/ORC-003_run_NNN.json
```

### Checklist:
- [ ] `.log` file ends with `END OF LOG`
- [ ] `.json` is valid JSON
- [ ] `verdict` is `pass`, `fail`, `inconclusive`, or `error`
- [ ] All metrics present
- [ ] `hypothesis_supported` is `true` or `false`

---

## Related Experiments

| Experiment ID | Relationship |
|---------------|-------------|
| ORC-002 | depends on |

---

_Experiment Spec — ORC-003 — v1.0 — TonyOS Lab_
