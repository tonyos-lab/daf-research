# DAF Research Environment Setup

> **Run this once. All 38 experiments assume this is complete.**
> After setup, each experiment's own `EXPERIMENT.md` tells you
> everything else you need.

---

## Overview

DAF research experiments run in two tiers:

| Tier | Requires | Covers |
|------|----------|--------|
| **Tier 1** (offline) | Python venv only | REL, SEC, ORC, most HIL (~25 experiments) |
| **Tier 2** (services) | Docker + optional API key | OBS dashboards, live CST (~13 experiments) |

This guide sets up both. You can stop after Tier 1 if you only plan
to run offline experiments.

---

## Prerequisites

Before starting, verify these are installed on your machine:

```bash
python --version      # must be 3.11 or higher
git --version         # any recent version
docker --version      # required for Tier 2 only
```

If Python is below 3.11, install it from https://python.org before continuing.

---

## Step 1 — Clone the Repository

If you haven't already:

```bash
git clone https://github.com/tonyos-lab/daf.git
cd daf
```

If you already have the repo:

```bash
git pull origin main
```

---

## Step 2 — Create and Activate the Virtual Environment

**Linux / macOS:**
```bash
python -m venv .venv
source .venv/bin/activate
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

**Windows (Git Bash):**
```bash
python -m venv .venv
source .venv/Scripts/activate
```

You should see `(.venv)` in your terminal prompt. All subsequent
commands assume the venv is active.

---

## Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

This installs everything needed for both Tier 1 and Tier 2 experiments.

---

## Step 4 — Verify Base DAF Import

```bash
python -c "import daf; print('DAF OK')"
```

Expected output: `DAF OK`

If this fails, check that you are in the repo root and the venv is active.

---

## Step 5 — Verify Research Infrastructure

```bash
python -c "from daf.research import BaseExperiment, ExperimentLogger; print('Research infrastructure OK')"
```

Expected output: `Research infrastructure OK`

---

## Step 6 — Run the Verification Suite

Confirm all 561 base tests still pass (research infrastructure must
not break existing behaviour):

```bash
python -m pytest tests/unit/ tests/adversarial/ \
  tests/integration/test_example01_mocked.py \
  tests/integration/test_example02_mocked.py \
  tests/integration/test_example03_mocked.py -q
```

Expected output: `561 passed`

If any tests fail, do not proceed. Open an issue on GitHub.

---

## Step 7 — Create the Findings Directory

```bash
mkdir -p findings
```

This is where all experiment run files (.log and .json) will be written.
It is listed in `.gitignore` by default — commit only when you intend
to publish findings.

---

## ✅ Tier 1 Setup Complete

You can now run any Tier 1 experiment. Stop here unless you need
Tier 2 (observability dashboards or live LLM cost experiments).

---

## Tier 2 — Additional Setup

### Step 8 — Start the Docker Stack

```bash
docker-compose up -d
```

This starts:
- PostgreSQL (audit persistence)
- Redis (checkpoint store)
- OpenTelemetry Collector
- Grafana (dashboard — available at http://localhost:3000)

Verify services are healthy:

```bash
docker-compose ps
```

All services should show `Up`.

### Step 9 — Configure Environment Variables (live API experiments only)

```bash
cp .env.example .env
```

Edit `.env` and set:

```
LLM_API_KEY=sk-ant-...       # your Anthropic API key
```

**Cost warning:** Tier 2 experiments with a live API key will make
real API calls and incur real costs. Each experiment's `EXPERIMENT.md`
states the estimated cost before you run it.

### Step 10 — Verify Tier 2

```bash
python -m pytest tests/integration/test_phase1_loop.py -v
```

Expected: all tests pass.

---

## Directory Structure After Setup

```
daf/
  .venv/                    ← virtual environment (never commit)
  .env                      ← API keys (never commit)
  findings/                 ← experiment run outputs (commit selectively)
    REL-001/
      REL-001_run_001.log
      REL-001_run_001.json
  experiments/              ← experiment source code
    reliability/
      REL-001/
        experiment.py
        EXPERIMENT.md
    security/
    orchestration/
    cost/
    observability/
    human_in_loop/
  daf/
    research/
      __init__.py
      base.py               ← BaseExperiment
      logger.py             ← ExperimentLogger
      runner.py             ← CLI runner
```

---

## Running Any Experiment

Once setup is complete, the pattern for every experiment is identical:

```bash
# From the repo root, venv active:
python -m daf.research.runner experiments/{domain}/{experiment_id}/experiment.py
```

Or directly:

```bash
python experiments/reliability/REL-001/experiment.py
```

Each experiment writes its own `.log` and `.json` to `findings/`.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'daf'`**
→ Virtual environment is not active, or you are not in the repo root.

**`ModuleNotFoundError: No module named 'daf.research'`**
→ Pull latest from main — research infrastructure may be newer than your local copy.

**`docker-compose: command not found`**
→ Install Docker Desktop from https://docker.com (Tier 2 only).

**`561 passed` becomes a different number**
→ Your local branch may have uncommitted changes. Run `git status`.

---

## Getting Help

- Open an issue: https://github.com/tonyos-lab/daf/issues
- Research discussion: use the `research` label on GitHub Issues
- Contact: tony.ochinang@tonyos-lab.org

---

_DAF R&D Setup Guide — v1.0 — TonyOS Lab_
