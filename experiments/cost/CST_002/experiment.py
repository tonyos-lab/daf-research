"""
experiments/cost/CST_002/experiment.py
====================================
CST-002 — Optimal Planning Orchestrator Tier

Research Question:
    Which model tier produces the best cost-per-compliant-plan ratio for the PlanningOrchestrator?

Hypothesis:
    Sonnet produces the optimal cost-per-compliant-plan ratio for multi-agent plans with compliance constraints.

Tier: 2 # Tier 2 — requires Docker / LLM_API_KEY
Depends on: CST-001
Estimated cost: $3.00
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


class CST_002(BaseExperiment):

    experiment_id       = "CST-002"
    domain              = Domain.COST
    tier                = Tier.SERVICES
    title               = "Optimal Planning Orchestrator Tier"
    research_question   = (
        "Which model tier produces the best cost-per-compliant-plan ratio for the PlanningOrchestrator?"
    )
    hypothesis          = (
        "Sonnet produces the optimal cost-per-compliant-plan ratio for multi-agent plans with compliance constraints."
    )
    depends_on          = ['CST-001']
    estimated_cost_usd  = 3.0
    estimated_minutes   = 30

    # ------------------------------------------------------------------
    # Lifecycle — implement these three methods
    # ------------------------------------------------------------------

    async def prepare(self) -> None:
        """
        Set up fixtures, registries, and policy matrix.
        TODO: implement for CST-002.
        """
        raise NotImplementedError(
            f"{self.experiment_id}.prepare() is not yet implemented. "
            f"See experiments/cost/CST_002/EXPERIMENT.md for guidance."
        )

    async def run(self) -> ExperimentResult:
        """
        Execute the experiment and return a structured result.
        TODO: implement for CST-002.
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
    parser = argparse.ArgumentParser(description="Run CST-002")
    parser.add_argument("--findings-dir", default="findings")
    args = parser.parse_args()

    exp    = CST_002()
    result = exp.execute(findings_dir=args.findings_dir)

    print(f"\nVerdict : {result.verdict.value.upper()}")
    print(f"Summary : {result.summary}")
