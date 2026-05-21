"""
experiments/cost/CST_005/experiment.py
====================================
CST-005 — Replan Cost Overhead

Research Question:
    What is the average additional cost incurred per replan iteration?

Hypothesis:
    Each replan iteration adds approximately the same cost as the initial plan call.

Tier: 2 # Tier 2 — requires Docker / LLM_API_KEY
Depends on: CST-003
Estimated cost: $2.00
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


class CST_005(BaseExperiment):

    experiment_id       = "CST-005"
    domain              = Domain.COST
    tier                = Tier.SERVICES
    title               = "Replan Cost Overhead"
    research_question   = (
        "What is the average additional cost incurred per replan iteration?"
    )
    hypothesis          = (
        "Each replan iteration adds approximately the same cost as the initial plan call."
    )
    depends_on          = ['CST-003']
    estimated_cost_usd  = 2.0
    estimated_minutes   = 30

    # ------------------------------------------------------------------
    # Lifecycle — implement these three methods
    # ------------------------------------------------------------------

    async def prepare(self) -> None:
        """
        Set up fixtures, registries, and policy matrix.
        TODO: implement for CST-005.
        """
        raise NotImplementedError(
            f"{self.experiment_id}.prepare() is not yet implemented. "
            f"See experiments/cost/CST_005/EXPERIMENT.md for guidance."
        )

    async def run(self) -> ExperimentResult:
        """
        Execute the experiment and return a structured result.
        TODO: implement for CST-005.
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
    parser = argparse.ArgumentParser(description="Run CST-005")
    parser.add_argument("--findings-dir", default="findings")
    args = parser.parse_args()

    exp    = CST_005()
    result = exp.execute(findings_dir=args.findings_dir)

    print(f"\nVerdict : {result.verdict.value.upper()}")
    print(f"Summary : {result.summary}")
