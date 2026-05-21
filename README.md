# DAF Research — PBAS Empirical Validation

Empirical research validating the [Policy-Based Agentic Safety (PBAS)](https://github.com/tonyos-lab/daf) architecture.

**Tony Ochinang — TonyOS Lab**

---

## What this is

This repository contains 30 experiments across 6 domains that empirically validate the PBAS claims made in the DAF whitepaper. Each experiment tests a specific property of the governed agentic loop.

## Branch → DAF version mapping

Each branch tests against a specific version of DAF. Results in `findings/` always match the code version in `requirements.txt`.

| Branch | DAF version | Status |
|---|---|---|
| `main` | v0.1.1 | Baseline — 30 experiments |
| `v0.1.2` | v0.1.2 | Re-run after bug fixes (pending) |
| `v0.2.0` | v0.2.0 | New experiments for Stage 2 |

## Setup

```bash
git clone https://github.com/tonyos-lab/daf-research
cd daf-research
pip install -r requirements.txt
```

That's it. `requirements.txt` installs the correct DAF version for this branch automatically.

## Run an experiment

```bash
python experiments/reliability/REL_001/experiment.py
```

Results are written to `findings/REL-001/`.

## Run all experiments

```bash
python scripts/run_all.py
```

## Experiment domains

| Domain | Experiments | Description |
|---|---|---|
| Reliability | REL-001 to REL-007 | Loop termination, composability, concurrency |
| Security | SEC-001 to SEC-007 | Injection resistance, permission escalation, forgery |
| Observability | OBS-001 to OBS-003 | Audit completeness, immutability, compliance schema |
| Orchestration | ORC-001 to ORC-006 | Dependency ordering, scoped context, budget tracking |
| Cost | CST-004, CST-007 | Budget precision, mock vs live divergence |
| Human-in-Loop | HIL-001 to HIL-006 | Gate triggers, approval flow, timeout behaviour |

## Findings summary (v0.1.0 baseline)

| Status | Count | Experiments |
|---|---|---|
| ✅ Pass | 16 | REL-002,003,004,006,007 · SEC-002,003,004,005,007 · OBS-002,003 · ORC-001,005,006 |
| ❌ Fail | 4 | SEC-001 · ORC-003,004 · CST-004 |
| ❌ Error | 10 | REL-001 · OBS-001 · ORC-002 · SEC-006 · CST-007 · HIL-001–006 |

See [docs/research/README.md](docs/research/README.md) for full experiment descriptions and methodology.

## Contributing

See [RESEARCH_SETUP.md](RESEARCH_SETUP.md) for how to run, extend, and contribute experiments.
