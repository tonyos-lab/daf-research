# OBS-005 — Grafana Dashboard Coverage

---

## Identity

| Field              | Value |
|--------------------|-------|
| **Experiment ID**  | OBS-005 |
| **Domain**         | observability |
| **Tier**           | 2 (requires Docker stack and/or LLM_API_KEY) |
| **Status**         | defined |
| **Claimed by**     | unclaimed |
| **Depends on**     | OBS-004 |
| **Estimated cost** | $0.00 (live API) |
| **Estimated time** | 30 minutes |

---

## Research Question

Do the Grafana dashboards expose all metrics required for operational monitoring?

---

## Hypothesis

The default Grafana dashboard covers loop duration, cost per workflow, violation rate, and escalation rate.

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

**Tier 2 — satisfied by RESEARCH_SETUP.md:**
- [ ] Python virtual environment active
- [ ] `pip install -r requirements.txt` complete
- [ ] `pip install -r requirements-dev.txt` complete
- [ ] DAF importable (`python -c "import daf"` succeeds)
- [ ] Research infrastructure importable

**Additional for Tier 2:**
- [ ] `docker-compose up -d` running
- [ ] `LLM_API_KEY` set in `.env`

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
   python -c "from experiments.observability.OBS_005.experiment import OBS_005; print('ready')"
   ```
   Expected output: `ready`

> TODO: Add any experiment-specific preparation steps.

---

## Execution

```bash
python -m daf.research.runner experiments/observability/OBS_005/experiment.py
```

**Expected duration:** 30 minutes
**Expected cost:** $0.00 (live API)

---

## Result Recording

```
findings/OBS-005/OBS-005_run_NNN.log
findings/OBS-005/OBS-005_run_NNN.json
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
| OBS-004 | depends on |

---

_Experiment Spec — OBS-005 — v1.0 — TonyOS Lab_
