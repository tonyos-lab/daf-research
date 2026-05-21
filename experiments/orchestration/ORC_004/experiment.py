"""ORC-004 — Budget Tracking Accuracy | Tier 1 | Depends on: none"""
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


class ORC_004(BaseExperiment):
    experiment_id = "ORC-004"
    domain = Domain.ORCHESTRATION
    tier = Tier.OFFLINE
    title = "Budget Tracking Accuracy"
    research_question = "Does the BudgetTracker accurately reflect cumulative cost across all tasks in a workflow?"
    hypothesis = "Total cost in FinalResponse equals the sum of individual task estimated_costs to floating-point precision."
    depends_on = []
    estimated_cost_usd = 0.0
    estimated_minutes = 5

    async def prepare(self): pass

    async def run(self) -> ExperimentResult:
        logger = self._active_logger
        results = []
        all_correct = True

        # Test cases: list of per-task costs
        cost_cases = [
            ("single_task",      [0.02]),
            ("two_tasks",        [0.02, 0.03]),
            ("three_tasks",      [0.01, 0.02, 0.03]),
            ("zero_cost_tasks",  [0.0, 0.0]),
            ("mixed_costs",      [0.005, 0.015, 0.008]),
        ]

        for name, task_costs in cost_cases:
            for trial in range(TRIALS):
                tr = ToolRegistry()
                tr.register(StubTool(name="read_db", idempotent=True))
                ar = AgentRegistry()
                ar.register(type("DocAgent", (StubAgent,), {"role": "document_reader"}))

                # Configure each agent instance with the specified cost_usd
                # StubAgent.cost_usd is what gets tracked in AgentResult and FinalResponse
                builder = FixturePlanBuilder()
                for i, cost in enumerate(task_costs, 1):
                    deps = [f"ST-{i-1:02d}"] if i > 1 else []
                    builder.with_task(
                        f"ST-{i:02d}", agent="document_reader",
                        tools=["read_db"], estimated_cost=cost,
                        depends_on=deps,
                    )
                plan = builder.build()

                # Create agent class with matching cost_usd
                task_cost_map = {f"ST-{i:02d}": cost for i, cost in enumerate(task_costs, 1)}
                call_idx = [0]

                class CostTrackingAgent(StubAgent):
                    role = "document_reader"
                    def __init__(self):
                        task_ids = list(task_cost_map.keys())
                        cost = task_cost_map.get(task_ids[min(call_idx[0], len(task_ids)-1)], 0.0)
                        call_idx[0] += 1
                        super().__init__(role="document_reader", cost_usd=cost)

                tr2 = ToolRegistry()
                tr2.register(StubTool(name="read_db", idempotent=True))
                ar2 = AgentRegistry()
                ar2.register(CostTrackingAgent)

                result = await GovernedAgenticLoop(
                    llm_client=MockLLMClient(responses=[plan]),
                    policy_matrix=POLICY_MATRIX,
                    agent_registry=ar2, tool_registry=tr2,
                ).run({"task": f"ORC-004 {name}", "tenant_id": "t", "user_id": "u"})

                expected_cost = sum(task_costs)
                actual_cost   = result.total_cost_usd
                # Allow floating-point tolerance
                cost_correct  = abs(actual_cost - expected_cost) < 1e-9
                completed     = result.outcome == "completed"
                correct = cost_correct and completed

                if not correct: all_correct = False

            logger.info(
                f"  {name:<25} expected={expected_cost:.6f} "
                f"actual={actual_cost:.6f} diff={abs(actual_cost-expected_cost):.2e} "
                f"→ {'✓' if cost_correct else '✗'}"
            )
            results.append({
                "case": name, "task_costs": task_costs,
                "expected": expected_cost, "actual": actual_cost,
                "cost_correct": cost_correct, "correct": correct,
            })

        metrics = {
            "cases_tested": len(cost_cases),
            "all_costs_accurate": all_correct,
            "max_cost_error": max(abs(r["actual"] - r["expected"]) for r in results),
            "single_task_cost_ok": results[0]["cost_correct"],
            "multi_task_accumulation_ok": results[2]["cost_correct"],
            "zero_cost_ok": results[3]["cost_correct"],
        }

        if all_correct:
            verdict, hyp = Verdict.PASS, True
            summary = "Budget tracking is accurate to floating-point precision across all task count and cost combinations."
            observations = [
                "Single-task costs tracked correctly.",
                "Multi-task costs accumulate correctly.",
                "Zero-cost tasks don't corrupt the total.",
                "Floating-point costs tracked to 1e-9 precision.",
            ]
        else:
            failed = [r for r in results if not r["correct"]]
            verdict, hyp = Verdict.FAIL, False
            summary = f"Budget tracking inaccuracy in cases: {[r['case'] for r in failed]}"
            observations = [str(failed)]

        return ExperimentResult(verdict=verdict, summary=summary,
            hypothesis_supported=hyp, metrics=metrics,
            observations=observations, raw_outputs=results)

    async def teardown(self): pass

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--findings-dir", default="findings")
    args = p.parse_args()
    exp = ORC_004(); result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}\nSummary : {result.summary}")
    for k, v in result.metrics.items(): print(f"  {k:<45} {v}")
