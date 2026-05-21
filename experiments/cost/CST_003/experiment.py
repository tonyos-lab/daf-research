"""
experiments/cost/CST_003/experiment.py
====================================
CST-003 — Full Loop Cost Model

Research Question:
    What is the total cost distribution of a GovernedAgenticLoop run across plan types?

Hypothesis:
    90% of workflow costs are incurred in the planning stage; execution stage cost is negligible for mock tools.

Tier: 2 # Tier 2 — requires Docker / LLM_API_KEY
Depends on: CST-001, CST-002
Estimated cost: $4.00
Estimated time: 45 minutes

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


class CST_003(BaseExperiment):

    experiment_id       = "CST-003"
    domain              = Domain.COST
    tier                = Tier.SERVICES
    title               = "Full Loop Cost Model"
    research_question   = (
        "What is the total cost distribution of a GovernedAgenticLoop run across plan types?"
    )
    hypothesis          = (
        "90% of workflow costs are incurred in the planning stage; execution stage cost is negligible for mock tools."
    )
    depends_on          = ['CST-001', 'CST-002']
    estimated_cost_usd  = 4.0
    estimated_minutes   = 45

    # ------------------------------------------------------------------
    # Lifecycle — implement these three methods
    # ------------------------------------------------------------------

    async def prepare(self) -> None:
        """
        Set up fixtures, registries, and policy matrix.
        TODO: implement for CST-003.
        """
        raise NotImplementedError(
            f"{self.experiment_id}.prepare() is not yet implemented. "
            f"See experiments/cost/CST_003/EXPERIMENT.md for guidance."
        )

    async def run(self) -> ExperimentResult:
        """
        Execute the experiment and return a structured result.
        TODO: implement for CST-003.
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
    parser = argparse.ArgumentParser(description="Run CST-003")
    parser.add_argument("--findings-dir", default="findings")
    args = parser.parse_args()

    exp    = CST_003()
    result = exp.execute(findings_dir=args.findings_dir)

    print(f"\nVerdict : {result.verdict.value.upper()}")
    print(f"Summary : {result.summary}")
