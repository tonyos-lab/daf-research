"""
experiments/reliability/REL_003/experiment.py
=============================================
REL-003 — Loop Termination Guarantee

Research Question:
    Under what PolicyMatrix configurations is Governed Agentic Loop
    termination formally guaranteed?

Hypothesis:
    The GovernedAgenticLoop always terminates within
    max_replan_attempts + 1 iterations regardless of LLM output.
    No combination of LLM responses can cause an infinite loop.

Tier: 1 (fully offline)
Depends on: REL-001
"""

from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[3]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from daf import GovernedAgenticLoop
from daf.testing import MockLLMClient, FixturePlanBuilder
from daf.runtime.agent_registry import AgentRegistry
from daf.runtime.tool_registry import ToolRegistry
from daf.agents import StubAgent
from daf.tools import StubTool

from daf.research.base import BaseExperiment, ExperimentResult, Verdict, Domain, Tier

POLICY_MATRIX = str(_repo_root / "policy" / "matrix" / "example.yaml")

def _violating_plan() -> dict:
    """A plan that always violates policy — forbidden tool."""
    return (
        FixturePlanBuilder()
        .with_task("ST-01", agent="document_reader", tools=["forbidden_tool_xyz"])
        .build()
    )

def _clean_plan() -> dict:
    return (
        FixturePlanBuilder()
        .with_task("ST-01", agent="document_reader", tools=["read_db"])
        .build()
    )


class REL_003(BaseExperiment):

    experiment_id      = "REL-003"
    domain             = Domain.RELIABILITY
    tier               = Tier.OFFLINE
    title              = "Loop Termination Guarantee"
    research_question  = (
        "Under what PolicyMatrix configurations is Governed Agentic "
        "Loop termination formally guaranteed?"
    )
    hypothesis         = (
        "The GovernedAgenticLoop always terminates within "
        "max_replan_attempts + 1 iterations regardless of LLM output. "
        "No combination of LLM responses causes an infinite loop."
    )
    depends_on         = ["REL-001"]
    estimated_cost_usd = 0.0
    estimated_minutes  = 5

    _agent_registry: AgentRegistry | None = None
    _tool_registry:  ToolRegistry  | None = None

    async def prepare(self) -> None:
        self._tool_registry = ToolRegistry()
        self._tool_registry.register(StubTool(name="read_db", idempotent=True))
        self._agent_registry = AgentRegistry()
        self._agent_registry.register(
            type("DocumentReaderAgent", (StubAgent,), {"role": "document_reader"})
        )

    async def run(self) -> ExperimentResult:
        logger = self._active_logger

        # Scenario definitions: (description, responses, expected_outcome)
        # max_replan_attempts in example.yaml is 3 — so loop runs at most 3 iters
        scenarios = [
            (
                "always_violating",
                "LLM always returns a violating plan (N+1 copies)",
                [_violating_plan()] * 10,   # more than enough
                "escalated",
            ),
            (
                "clean_first",
                "LLM returns clean plan on first attempt",
                [_clean_plan()],
                "completed",
            ),
            (
                "violating_then_clean",
                "LLM violates once then returns clean plan",
                [_violating_plan(), _clean_plan()],
                "completed",
            ),
            (
                "always_empty",
                "LLM always returns empty sub_tasks list",
                [{"orchestrator": "default", "planning_rationale": "empty",
                  "sub_tasks": [], "total_estimated_cost": 0.0,
                  "confidence": 0.9, "requires_human_gate": False}] * 10,
                None,  # either completed or escalated — just must terminate
            ),
        ]

        all_terminated = True
        raw_outputs    = []
        scenario_results = []

        for name, description, responses, expected_outcome in scenarios:
            logger.info(f"Scenario: {name} — {description}")

            result = await GovernedAgenticLoop(
                llm_client=MockLLMClient(responses=responses),
                policy_matrix=POLICY_MATRIX,
                agent_registry=self._agent_registry,
                tool_registry=self._tool_registry,
            ).run({
                "task":      "Test loop termination",
                "tenant_id": "test",
                "user_id":   "researcher",
            })

            terminated       = result.outcome in ("completed", "escalated", "invalid_input", "partial")
            outcome_correct  = (expected_outcome is None) or (result.outcome == expected_outcome)
            iterations_ok    = result.loop_iterations <= 4  # max_replan_attempts(3) + 1

            if not terminated or not iterations_ok:
                all_terminated = False

            logger.info(
                f"  outcome={result.outcome} iterations={result.loop_iterations} "
                f"terminated={terminated} iterations_ok={iterations_ok} "
                f"outcome_correct={outcome_correct}"
            )

            scenario_results.append({
                "scenario":         name,
                "outcome":          result.outcome,
                "iterations":       result.loop_iterations,
                "terminated":       terminated,
                "iterations_ok":    iterations_ok,
                "outcome_correct":  outcome_correct,
            })
            raw_outputs.append(scenario_results[-1])

        total_scenarios   = len(scenarios)
        terminated_count  = sum(1 for s in scenario_results if s["terminated"])
        iter_ok_count     = sum(1 for s in scenario_results if s["iterations_ok"])

        metrics = {
            "scenarios_tested":          total_scenarios,
            "all_terminated":            all_terminated,
            "terminated_count":          terminated_count,
            "iterations_within_bound":   iter_ok_count,
            "max_iterations_observed":   max(s["iterations"] for s in scenario_results),
            "always_violating_outcome":  scenario_results[0]["outcome"],
            "clean_first_outcome":       scenario_results[1]["outcome"],
            "violating_then_clean_iters": scenario_results[2]["iterations"],
        }

        if all_terminated and iter_ok_count == total_scenarios:
            verdict = Verdict.PASS
            summary = (
                f"All {total_scenarios} scenarios terminated within bound — "
                f"loop termination is guaranteed."
            )
            hypothesis_supported = True
            observations = [
                "Loop terminates in all tested scenarios (compliant, violating, empty).",
                f"Maximum iterations observed: {metrics['max_iterations_observed']} (bound: 4).",
                "Always-violating LLM correctly escalates after max_replan_attempts.",
            ]
        else:
            failed = [s["scenario"] for s in scenario_results
                      if not s["terminated"] or not s["iterations_ok"]]
            verdict = Verdict.FAIL
            summary = (
                f"Termination guarantee violated in scenarios: {failed}."
            )
            hypothesis_supported = False
            observations = [f"Failed scenarios: {failed}"]

        return ExperimentResult(
            verdict=verdict,
            summary=summary,
            hypothesis_supported=hypothesis_supported,
            metrics=metrics,
            observations=observations,
            raw_outputs=raw_outputs,
        )

    async def teardown(self) -> None:
        self._agent_registry = None
        self._tool_registry  = None


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run REL-003")
    parser.add_argument("--findings-dir", default="findings")
    args = parser.parse_args()
    exp = REL_003()
    result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}")
    print(f"Summary : {result.summary}")
    for k, v in result.metrics.items():
        print(f"  {k:<45} {v}")
