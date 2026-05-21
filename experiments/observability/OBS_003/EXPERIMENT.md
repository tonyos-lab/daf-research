# OBS-003 — Audit Record Immutability

---

## Identity

| Field              | Value |
|--------------------|-------|
| **Experiment ID**  | OBS-003 |
| **Domain**         | observability |
| **Tier**           | 1 (offline — no API key, no Docker) |
| **Status**         | defined |
| **Claimed by**     | unclaimed |
| **Depends on**     | OBS-001 |
| **Estimated cost** | $0.00 (offline) |
| **Estimated time** | 5 minutes |

---

## Research Question

Can audit records be modified after they are written to the store?

---

## Hypothesis

AuditRecord is frozen at creation — no field can be mutated after write.

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
   python -c "from experiments.observability.OBS_003.experiment import OBS_003; print('ready')"
   ```
   Expected output: `ready`

> TODO: Add any experiment-specific preparation steps.

---

## Execution

```bash
python -m daf.research.runner experiments/observability/OBS_003/experiment.py
```

**Expected duration:** 5 minutes
**Expected cost:** $0.00 (offline)

---

## Result Recording

```
findings/OBS-003/OBS-003_run_NNN.log
findings/OBS-003/OBS-003_run_NNN.json
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
| OBS-001 | depends on |

---

_Experiment Spec — OBS-003 — v1.0 — TonyOS Lab_
