"""
experiments/cost/CST_001/experiment.py
====================================
CST-001 — Quality-Cost Tradeoff by Model Tier

Research Question:
    For each call type, what is the quality-cost tradeoff across model tiers?

Hypothesis:
    Haiku produces acceptable plan quality for simple single-agent tasks at <20% of the cost of Sonnet.

Tier: 2 # Tier 2 — requires Docker / LLM_API_KEY
Depends on: none
Estimated cost: $5.00
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


class CST_001(BaseExperiment):

    experiment_id       = "CST-001"
    domain              = Domain.COST
    tier                = Tier.SERVICES
    title               = "Quality-Cost Tradeoff by Model Tier"
    research_question   = (
        "For each call type, what is the quality-cost tradeoff across model tiers?"
    )
    hypothesis          = (
        "Haiku produces acceptable plan quality for simple single-agent tasks at <20% of the cost of Sonnet."
    )
    depends_on          = []
    estimated_cost_usd  = 5.0
    estimated_minutes   = 45

    # ------------------------------------------------------------------
    # Lifecycle — implement these three methods
    # ------------------------------------------------------------------

    async def prepare(self) -> None:
        """
        Set up fixtures, registries, and policy matrix.
        TODO: implement for CST-001.
        """
        raise NotImplementedError(
            f"{self.experiment_id}.prepare() is not yet implemented. "
            f"See experiments/cost/CST_001/EXPERIMENT.md for guidance."
        )

    async def run(self) -> ExperimentResult:
        """
        Execute the experiment and return a structured result.
        TODO: implement for CST-001.
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
    parser = argparse.ArgumentParser(description="Run CST-001")
    parser.add_argument("--findings-dir", default="findings")
    args = parser.parse_args()

    exp    = CST_001()
    result = exp.execute(findings_dir=args.findings_dir)

    print(f"\nVerdict : {result.verdict.value.upper()}")
    print(f"Summary : {result.summary}")
