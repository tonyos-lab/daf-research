"""
experiments/cost/CST_006/experiment.py
====================================
CST-006 — Cost Estimation Accuracy

Research Question:
    How accurately does the PlanningOrchestrator estimate cost before execution?

Hypothesis:
    Pre-execution cost estimates are within ±15% of actual incurred costs for standard plan types.

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


class CST_006(BaseExperiment):

    experiment_id       = "CST-006"
    domain              = Domain.COST
    tier                = Tier.SERVICES
    title               = "Cost Estimation Accuracy"
    research_question   = (
        "How accurately does the PlanningOrchestrator estimate cost before execution?"
    )
    hypothesis          = (
        "Pre-execution cost estimates are within ±15% of actual incurred costs for standard plan types."
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
        TODO: implement for CST-006.
        """
        raise NotImplementedError(
            f"{self.experiment_id}.prepare() is not yet implemented. "
            f"See experiments/cost/CST_006/EXPERIMENT.md for guidance."
        )

    async def run(self) -> ExperimentResult:
        """
        Execute the experiment and return a structured result.
        TODO: implement for CST-006.
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
    parser = argparse.ArgumentParser(description="Run CST-006")
    parser.add_argument("--findings-dir", default="findings")
    args = parser.parse_args()

    exp    = CST_006()
    result = exp.execute(findings_dir=args.findings_dir)

    print(f"\nVerdict : {result.verdict.value.upper()}")
    print(f"Summary : {result.summary}")
