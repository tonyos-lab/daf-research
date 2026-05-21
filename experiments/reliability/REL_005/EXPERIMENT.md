# REL-005 — Live API Reliability Baseline

---

## Identity

| Field              | Value |
|--------------------|-------|
| **Experiment ID**  | REL-005 |
| **Domain**         | reliability |
| **Tier**           | 2 (requires Docker stack and/or LLM_API_KEY) |
| **Status**         | defined |
| **Claimed by**     | unclaimed |
| **Depends on**     | REL-001 |
| **Estimated cost** | $2.50 (live API) |
| **Estimated time** | 30 minutes |

---

## Research Question

What is the empirical per-call success rate against the live Anthropic API under normal conditions?

---

## Hypothesis

Live API calls succeed at ≥99% over 100 consecutive planning calls under normal load.

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
   python -c "from experiments.reliability.REL_005.experiment import REL_005; print('ready')"
   ```
   Expected output: `ready`

> TODO: Add any experiment-specific preparation steps.

---

## Execution

```bash
python -m daf.research.runner experiments/reliability/REL_005/experiment.py
```

**Expected duration:** 30 minutes
**Expected cost:** $2.50 (live API)

---

## Result Recording

```
findings/REL-005/REL-005_run_NNN.log
findings/REL-005/REL-005_run_NNN.json
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
| REL-001 | depends on |

---

_Experiment Spec — REL-005 — v1.0 — TonyOS Lab_
