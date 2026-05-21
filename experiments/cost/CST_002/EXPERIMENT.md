# CST-002 — Optimal Planning Orchestrator Tier

---

## Identity

| Field              | Value |
|--------------------|-------|
| **Experiment ID**  | CST-002 |
| **Domain**         | cost |
| **Tier**           | 2 (requires Docker stack and/or LLM_API_KEY) |
| **Status**         | defined |
| **Claimed by**     | unclaimed |
| **Depends on**     | CST-001 |
| **Estimated cost** | $3.00 (live API) |
| **Estimated time** | 30 minutes |

---

## Research Question

Which model tier produces the best cost-per-compliant-plan ratio for the PlanningOrchestrator?

---

## Hypothesis

Sonnet produces the optimal cost-per-compliant-plan ratio for multi-agent plans with compliance constraints.

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
   python -c "from experiments.cost.CST_002.experiment import CST_002; print('ready')"
   ```
   Expected output: `ready`

> TODO: Add any experiment-specific preparation steps.

---

## Execution

```bash
python -m daf.research.runner experiments/cost/CST_002/experiment.py
```

**Expected duration:** 30 minutes
**Expected cost:** $3.00 (live API)

---

## Result Recording

```
findings/CST-002/CST-002_run_NNN.log
findings/CST-002/CST-002_run_NNN.json
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
| CST-001 | depends on |

---

_Experiment Spec — CST-002 — v1.0 — TonyOS Lab_
