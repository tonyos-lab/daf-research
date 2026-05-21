"""
REL-006 — Replan Loop Convergence Rate
Tier: 1 | Depends on: REL-003
"""
from __future__ import annotations
import sys
from pathlib import Path
_r = Path(__file__).resolve().parents[3]
if str(_r) not in sys.path: sys.path.insert(0, str(_r))

from daf import GovernedAgenticLoop
from daf.testing import MockLLMClient, FixturePlanBuilder
from daf.runtime.agent_registry import AgentRegistry
from daf.runtime.tool_registry import ToolRegistry
from daf.agents import StubAgent
from daf.tools import StubTool
from daf.research.base import BaseExperiment, ExperimentResult, Verdict, Domain, Tier

POLICY_MATRIX = str(_r / "policy" / "matrix" / "example.yaml")
TRIALS = 20


def _clean_plan():
    return (
        FixturePlanBuilder()
        .with_task("ST-01", agent="document_reader", tools=["read_db"])
        .build()
    )


def _violating_plan():
    return (
        FixturePlanBuilder()
        .with_task("ST-01", agent="document_reader", tools=["forbidden_tool"])
        .build()
    )


class REL_006(BaseExperiment):
    experiment_id      = "REL-006"
    domain             = Domain.RELIABILITY
    tier               = Tier.OFFLINE
    title              = "Replan Loop Convergence Rate"
    research_question  = "At what rate does the replan loop converge to a compliant plan after a violation?"
    hypothesis         = (
        "When the LLM produces a compliant plan on its second attempt, "
        "the loop converges in exactly 2 iterations 100% of the time."
    )
    depends_on         = ["REL-003"]
    estimated_cost_usd = 0.0
    estimated_minutes  = 5

    _agent_registry: AgentRegistry | None = None
    _tool_registry:  ToolRegistry  | None = None

    async def prepare(self) -> None:
        self._tool_registry = ToolRegistry()
        self._tool_registry.register(StubTool(name="read_db", idempotent=True))
        self._agent_registry = AgentRegistry()
        self._agent_registry.register(
            type("DocAgent", (StubAgent,), {"role": "document_reader"})
        )

    async def run(self) -> ExperimentResult:
        logger = self._active_logger
        raw_outputs = []

        # Scenario A: violate once then clean (converges in 2 iterations)
        logger.info("Scenario A: 1 violation then compliant plan")
        converge_2_count = 0
        for trial in range(TRIALS):
            result = await GovernedAgenticLoop(
                llm_client=MockLLMClient(
                    responses=[_violating_plan(), _clean_plan()]
                ),
                policy_matrix=POLICY_MATRIX,
                agent_registry=self._agent_registry,
                tool_registry=self._tool_registry,
            ).run({
                "task": "Convergence test A", "tenant_id": "rel", "user_id": "researcher"
            })
            converged_in_2 = (result.outcome == "completed" and result.loop_iterations == 2)
            if converged_in_2:
                converge_2_count += 1
            raw_outputs.append({
                "scenario": "A", "trial": trial + 1,
                "outcome": result.outcome, "iterations": result.loop_iterations,
                "converged_in_2": converged_in_2,
            })
        rate_A = converge_2_count / TRIALS
        logger.info(f"  convergence_in_2_rate={rate_A:.4f} ({converge_2_count}/{TRIALS})")

        # Scenario B: violate twice then clean (converges in 3 iterations)
        logger.info("Scenario B: 2 violations then compliant plan")
        converge_3_count = 0
        for trial in range(TRIALS):
            result = await GovernedAgenticLoop(
                llm_client=MockLLMClient(
                    responses=[_violating_plan(), _violating_plan(), _clean_plan()]
                ),
                policy_matrix=POLICY_MATRIX,
                agent_registry=self._agent_registry,
                tool_registry=self._tool_registry,
            ).run({
                "task": "Convergence test B", "tenant_id": "rel", "user_id": "researcher"
            })
            converged_in_3 = (result.outcome == "completed" and result.loop_iterations == 3)
            if converged_in_3:
                converge_3_count += 1
            raw_outputs.append({
                "scenario": "B", "trial": trial + 1,
                "outcome": result.outcome, "iterations": result.loop_iterations,
                "converged_in_3": converged_in_3,
            })
        rate_B = converge_3_count / TRIALS
        logger.info(f"  convergence_in_3_rate={rate_B:.4f} ({converge_3_count}/{TRIALS})")

        # Scenario C: immediate clean plan (converges in 1 iteration)
        logger.info("Scenario C: immediate clean plan")
        converge_1_count = 0
        for trial in range(TRIALS):
            result = await GovernedAgenticLoop(
                llm_client=MockLLMClient(responses=[_clean_plan()]),
                policy_matrix=POLICY_MATRIX,
                agent_registry=self._agent_registry,
                tool_registry=self._tool_registry,
            ).run({
                "task": "Convergence test C", "tenant_id": "rel", "user_id": "researcher"
            })
            converged_in_1 = (result.outcome == "completed" and result.loop_iterations == 1)
            if converged_in_1:
                converge_1_count += 1
        rate_C = converge_1_count / TRIALS
        logger.info(f"  convergence_in_1_rate={rate_C:.4f} ({converge_1_count}/{TRIALS})")

        all_deterministic = (rate_A == 1.0 and rate_B == 1.0 and rate_C == 1.0)

        metrics = {
            "trials_per_scenario":              TRIALS,
            "scenario_A_converge_in_2_rate":    round(rate_A, 4),
            "scenario_B_converge_in_3_rate":    round(rate_B, 4),
            "scenario_C_converge_in_1_rate":    round(rate_C, 4),
            "all_convergence_deterministic":    all_deterministic,
            "iteration_count_is_exact":         all_deterministic,
        }

        if all_deterministic:
            verdict, hyp = Verdict.PASS, True
            summary = (
                "Replan loop converges in exactly N+1 iterations when LLM "
                "produces compliant plan on attempt N+1 — 100% deterministic."
            )
            observations = [
                "1 violation → completed in exactly 2 iterations (100%).",
                "2 violations → completed in exactly 3 iterations (100%).",
                "0 violations → completed in exactly 1 iteration (100%).",
                "Iteration count is a pure function of violation count.",
            ]
        else:
            verdict, hyp = Verdict.FAIL, False
            summary = "Non-deterministic convergence detected."
            observations = [
                f"Scenario A rate: {rate_A} (expected 1.0)",
                f"Scenario B rate: {rate_B} (expected 1.0)",
                f"Scenario C rate: {rate_C} (expected 1.0)",
            ]

        return ExperimentResult(
            verdict=verdict, summary=summary,
            hypothesis_supported=hyp, metrics=metrics,
            observations=observations, raw_outputs=raw_outputs[:20],
        )

    async def teardown(self) -> None:
        self._agent_registry = None
        self._tool_registry  = None

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--findings-dir", default="findings")
    args = p.parse_args()
    exp = REL_006(); result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}\nSummary : {result.summary}")
    for k, v in result.metrics.items(): print(f"  {k:<45} {v}")
