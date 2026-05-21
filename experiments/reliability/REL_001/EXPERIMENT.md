# REL-001 — Per-Call Reliability Characterisation

---

## Identity

| Field              | Value |
|--------------------|-------|
| **Experiment ID**  | REL-001 |
| **Domain**         | reliability |
| **Tier**           | 1 (offline — no API key, no Docker) |
| **Status**         | defined |
| **Claimed by**     | unclaimed |
| **Depends on**     | none |
| **Estimated cost** | $0.00 |
| **Estimated time** | 2–5 minutes |

---

## Research Question

> "Can per-call reliability be formally characterised as a function
> of call type and model tier?"
> — PBAS Research Backlog, Priority Question #1

---

## Hypothesis

The DAF GovernedAgenticLoop, when driven by a MockLLMClient
configured to fail after N calls, produces a measurable and
deterministic failure rate across repeated runs. Specifically:
a MockLLMClient with `fail_after=N` will produce exactly N
successful plan calls followed by exactly 1 LLM error, giving
a per-call success rate of N/(N+1), reproducibly across all runs.

---

## What This Experiment Measures

This experiment characterises the reliability behaviour of the
GovernedAgenticLoop's planning stage under controlled failure
injection. It uses MockLLMClient's `fail_after` parameter to
simulate LLM provider failures at known points, then measures
whether DAF surfaces these failures deterministically and
consistently. This establishes the baseline reliability contract
of the planning stage — a foundational measurement that all other
reliability experiments (REL-002 through REL-007) depend on.

---

## Metrics

| Metric Key | Type | Unit | Description |
|------------|------|------|-------------|
| `total_runs` | int | — | Total experiment iterations executed |
| `successful_runs` | int | — | Runs that completed without LLM error |
| `failed_runs` | int | — | Runs that raised LLMClientError |
| `success_rate` | float | ratio 0–1 | successful_runs / total_runs |
| `expected_success_rate` | float | ratio 0–1 | Theoretical N/(N+1) |
| `rate_matches_expected` | bool | — | True if measured rate == expected |
| `mean_duration_ms` | float | ms | Mean wall-clock time per loop run |
| `std_duration_ms` | float | ms | Std deviation of wall-clock time |

---

## Prerequisites

**Tier 1 — satisfied by RESEARCH_SETUP.md:**
- [ ] Python virtual environment active
- [ ] `pip install -r requirements.txt` complete
- [ ] `pip install -r requirements-dev.txt` complete
- [ ] DAF importable (`python -c "import daf"` succeeds)
- [ ] Research infrastructure importable (`python -c "from daf.research import BaseExperiment"` succeeds)

**Additional prerequisites for REL-001:**
- [ ] None — base setup is sufficient.

---

## Preparation Steps

1. Navigate to the DAF project root:
   ```bash
   cd /path/to/daf
   ```

2. Activate the virtual environment:
   ```bash
   source .venv/bin/activate        # Linux/macOS
   source .venv/Scripts/activate    # Windows Git Bash
   ```

3. Verify readiness:
   ```bash
   python -c "
   from experiments.reliability.REL_001.experiment import REL001
   print('REL-001 ready')
   "
   ```
   Expected output: `REL-001 ready`

---

## Execution

**Standard runner:**
```bash
python -m daf.research.runner experiments/reliability/REL_001/experiment.py
```

**Direct execution:**
```bash
python experiments/reliability/REL_001/experiment.py
```

**Or from Python:**
```python
from experiments.reliability.REL_001.experiment import REL001

exp = REL001()
result = exp.execute(findings_dir="findings")

print(result.verdict)        # "pass" or "fail"
print(result.summary)        # one-sentence conclusion
print(result.metrics)        # all measured values
```

**Expected duration:** 2–5 minutes
**Expected cost:** $0.00

### What to watch for during execution

- The log will show `--- RUN ---` followed by iteration progress lines
- Each iteration logs `[HH:MM:SS] INFO   iter N: outcome=...`
- Normal completion shows `--- RESULTS ---` with verdict `pass`
- If `rate_matches_expected` is `false`, the verdict will be `fail`
- Safe to abort at any time with Ctrl+C — no external state is modified

---

## Result Recording

When the experiment completes, two files are automatically written:

```
findings/REL-001/REL-001_run_001.log
findings/REL-001/REL-001_run_001.json
```

### Checklist — a complete result includes:

- [ ] `.log` file exists and ends with `END OF LOG`
- [ ] `.json` file is valid JSON (`python -m json.tool findings/REL-001/REL-001_run_001.json`)
- [ ] `verdict` is `pass`, `fail`, or `error`
- [ ] All 8 metric keys from the Metrics table are present in `.json`
- [ ] `hypothesis_supported` is `true` or `false` (not null)
- [ ] `summary` is a single sentence
- [ ] `observations` list has at least 1 entry

### Committing findings

```bash
git add findings/REL-001/
git commit -m "research(REL-001): run NNN — <one-line verdict>"
```

---

## Expected Outcomes

| Scenario | Expected Verdict | Notes |
|----------|-----------------|-------|
| MockLLMClient fails deterministically | `pass` | Hypothesis supported |
| Non-deterministic failure count observed | `fail` | Investigate MockLLMClient impl |
| Unexpected exception during run | `error` | Check log for traceback |

---

## Interpreting Results

A `pass` verdict confirms that DAF's planning stage surfaces LLM
failures deterministically — the measured success rate matches the
theoretical N/(N+1) exactly. This is the expected result and supports
the hypothesis.

A `fail` verdict means the measured rate deviated from the expected
rate. This would suggest non-determinism in how MockLLMClient or
GovernedAgenticLoop handles failures — a finding that would require
investigation before any further reliability experiments proceed.

An `inconclusive` result is not expected for this experiment since
the MockLLMClient is fully deterministic by design.

---

## Known Limitations

- This experiment uses MockLLMClient, not a real LLM provider.
  It measures DAF's internal reliability handling, not provider-level
  reliability. REL-005 extends this to live API calls.
- Wall-clock timing measurements may vary across machines and OS
  schedulers. The `mean_duration_ms` metric is informational only
  at this stage.
- This experiment does not measure reliability under concurrency.
  That is covered by REL-004.

---

## Related Experiments

| Experiment ID | Relationship |
|---------------|-------------|
| REL-002 | Feeds into — REL-001 results are input to composability testing |
| REL-003 | Feeds into — loop termination bounds require reliability baseline |
| REL-005 | Extends — live API reliability uses same measurement approach |

---

## References

- PBAS Research Backlog — Priority Question #1
- DAF `daf/testing/__init__.py` — MockLLMClient.fail_after parameter
- DAF `daf/loop.py` — GovernedAgenticLoop planning stage

---

_REL-001 Experiment Spec — v1.0 — TonyOS Lab_
