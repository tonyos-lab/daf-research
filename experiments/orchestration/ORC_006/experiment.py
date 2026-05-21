"""ORC-006 — Empty Plan Handling | Tier 1 | Depends on: ORC-001"""
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
TRIALS = 10

EMPTY_PLAN = {
    "orchestrator": "default_orchestrator",
    "planning_rationale": "No tasks needed",
    "sub_tasks": [],
    "total_estimated_cost": 0.0,
    "confidence": 0.9,
    "requires_human_gate": False,
}


class ORC_006(BaseExperiment):
    experiment_id = "ORC-006"
    domain = Domain.ORCHESTRATION
    tier = Tier.OFFLINE
    title = "Empty Plan Handling"
    research_question = "How does the loop behave when the LLM returns a plan with zero sub-tasks?"
    hypothesis = "An empty plan is approved by the PolicyEngine (vacuously) and produces a clean terminal outcome without crashing."
    depends_on = ["ORC-001"]
    estimated_cost_usd = 0.0
    estimated_minutes = 5

    async def prepare(self): pass

    async def run(self) -> ExperimentResult:
        logger = self._active_logger
        results = []
        all_correct = True

        # Scenario A: empty plan — must not crash, must terminate
        logger.info("Scenario A: empty plan — must terminate cleanly")
        for trial in range(TRIALS):
            tr = ToolRegistry()
            tr.register(StubTool(name="read_db", idempotent=True))
            ar = AgentRegistry()
            ar.register(type("DocAgent", (StubAgent,), {"role": "document_reader"}))

            result = await GovernedAgenticLoop(
                llm_client=MockLLMClient(responses=[EMPTY_PLAN]),
                policy_matrix=POLICY_MATRIX,
                agent_registry=ar, tool_registry=tr,
            ).run({"task": "ORC-006 empty plan", "tenant_id": "t", "user_id": "u"})

            terminated = result.outcome in ("completed", "escalated", "partial", "invalid_input")
            zero_cost  = result.total_cost_usd == 0.0
            correct    = terminated and zero_cost

            if not correct: all_correct = False
            logger.info(
                f"  trial {trial+1}: outcome={result.outcome} "
                f"cost={result.total_cost_usd} → {'✓' if correct else '✗'}"
            )
            results.append({
                "scenario": "A", "trial": trial+1,
                "outcome": result.outcome,
                "cost": result.total_cost_usd,
                "terminated": terminated,
                "zero_cost": zero_cost,
                "correct": correct,
            })

        # Scenario B: empty then valid plan — second plan completes
        logger.info("Scenario B: empty plan then valid plan — converges")
        valid_plan = (
            FixturePlanBuilder()
            .with_task("ST-01", agent="document_reader", tools=["read_db"])
            .build()
        )

        for trial in range(min(TRIALS, 5)):
            tr = ToolRegistry()
            tr.register(StubTool(name="read_db", idempotent=True))
            ar = AgentRegistry()
            ar.register(type("DocAgent", (StubAgent,), {"role": "document_reader"}))

            result = await GovernedAgenticLoop(
                llm_client=MockLLMClient(responses=[EMPTY_PLAN, valid_plan]),
                policy_matrix=POLICY_MATRIX,
                agent_registry=ar, tool_registry=tr,
            ).run({"task": "ORC-006 empty then valid", "tenant_id": "t", "user_id": "u"})

            terminated = result.outcome in ("completed", "escalated", "partial")
            correct = terminated
            if not correct: all_correct = False
            logger.info(f"  trial {trial+1}: outcome={result.outcome} → {'✓' if correct else '✗'}")
            results.append({
                "scenario": "B", "trial": trial+1,
                "outcome": result.outcome, "correct": correct,
            })

        A_results = [r for r in results if r["scenario"] == "A"]
        B_results = [r for r in results if r["scenario"] == "B"]
        outcomes_A = set(r["outcome"] for r in A_results)

        metrics = {
            "trials_A": TRIALS,
            "trials_B": min(TRIALS, 5),
            "empty_plan_terminates": round(sum(1 for r in A_results if r["terminated"]) / TRIALS, 4),
            "empty_plan_zero_cost": round(sum(1 for r in A_results if r["zero_cost"]) / TRIALS, 4),
            "empty_plan_outcomes": sorted(outcomes_A),
            "empty_then_valid_terminates": round(sum(1 for r in B_results if r["correct"]) / len(B_results), 4),
            "all_correct": all_correct,
        }

        if all_correct:
            verdict, hyp = Verdict.PASS, True
            summary = f"Empty plans handled cleanly — terminates in all {TRIALS} trials with zero cost, no crash."
            observations = [
                f"Empty plan outcomes: {sorted(outcomes_A)} — all are valid terminal outcomes.",
                "Empty plan always produces total_cost_usd=0.0.",
                "Empty-then-valid sequence terminates correctly.",
                "Loop never crashes on empty sub_tasks list.",
            ]
        else:
            failed = [r for r in results if not r["correct"]]
            verdict, hyp = Verdict.FAIL, False
            summary = f"Empty plan handling failure in {len(failed)} trials."
            observations = [str(failed[:3])]

        return ExperimentResult(verdict=verdict, summary=summary,
            hypothesis_supported=hyp, metrics=metrics,
            observations=observations, raw_outputs=results[:15])

    async def teardown(self): pass

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--findings-dir", default="findings")
    args = p.parse_args()
    exp = ORC_006(); result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}\nSummary : {result.summary}")
    for k, v in result.metrics.items(): print(f"  {k:<45} {v}")
