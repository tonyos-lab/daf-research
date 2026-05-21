"""
experiments/reliability/REL_005/experiment.py
===========================================
REL-005 — Live API Reliability Baseline

Research Question:
    What is the empirical per-call success rate against the live Anthropic API under normal conditions?

Hypothesis:
    Live API calls succeed at ≥99% over 100 consecutive planning calls under normal load.

Tier: 2 # Tier 2 — requires Docker / LLM_API_KEY
Depends on: REL-001
Estimated cost: $2.50
Estimated time: 30 minutes

Status: SCAFFOLD — implement prepare(), run(), teardown()
"""

from __future__ import annotations

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Path setup — allows running directly: python experiment.py
# ---------------------------------------------------------------------------
_repo_root = Path(__file__).resolve().parents[3]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from daf.research.base import (
    BaseExperiment,
    ExperimentResult,
    Verdict,
    Domain,
    Tier,
)


class REL_005(BaseExperiment):

    experiment_id       = "REL-005"
    domain              = Domain.RELIABILITY
    tier                = Tier.SERVICES
    title               = "Live API Reliability Baseline"
    research_question   = (
        "What is the empirical per-call success rate against the live Anthropic API under normal conditions?"
    )
    hypothesis          = (
        "Live API calls succeed at ≥99% over 100 consecutive planning calls under normal load."
    )
    depends_on          = ['REL-001']
    estimated_cost_usd  = 2.5
    estimated_minutes   = 30

    # ------------------------------------------------------------------
    # Lifecycle — implement these three methods
    # ------------------------------------------------------------------

    async def prepare(self) -> None:
        """
        Set up fixtures, registries, and policy matrix.
        TODO: implement for REL-005.
        """
        raise NotImplementedError(
            f"{self.experiment_id}.prepare() is not yet implemented. "
            f"See experiments/reliability/REL_005/EXPERIMENT.md for guidance."
        )

    async def run(self) -> ExperimentResult:
        """
        Execute the experiment and return a structured result.
        TODO: implement for REL-005.
        """
        raise NotImplementedError(
            f"{self.experiment_id}.run() is not yet implemented."
        )

    async def teardown(self) -> None:
        """Clean up after run(). May be a no-op."""
        pass  # TODO: add teardown if needed


# ---------------------------------------------------------------------------
# Direct execution entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run REL-005")
    parser.add_argument("--findings-dir", default="findings")
    args = parser.parse_args()

    exp    = REL_005()
    result = exp.execute(findings_dir=args.findings_dir)

    print(f"\nVerdict : {result.verdict.value.upper()}")
    print(f"Summary : {result.summary}")
