"""ORC-001 — Task Dependency Resolution Correctness | Tier 1 | Depends on: none"""
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


def _make_registries():
    tr = ToolRegistry()
    tr.register(StubTool(name="read_db", idempotent=True))
    ar = AgentRegistry()
    # Track execution order via shared list
    execution_order = []
    class OrderedAgent(StubAgent):
        role = "document_reader"
        def __init__(self):
            super().__init__(role="document_reader")
        async def execute(self, task, context):
            execution_order.append(task.task_id)
            return await super().execute(task, context)
    ar.register(OrderedAgent)
    return ar, tr, execution_order


class ORC_001(BaseExperiment):
    experiment_id = "ORC-001"
    domain = Domain.ORCHESTRATION
    tier = Tier.OFFLINE
    title = "Task Dependency Resolution Correctness"
    research_question = "Does the ExecutionOrchestrator correctly resolve and enforce task dependency ordering?"
    hypothesis = "Tasks with declared depends_on always execute after their dependencies, regardless of plan ordering."
    depends_on = []
    estimated_cost_usd = 0.0
    estimated_minutes = 5

    async def prepare(self): pass

    async def run(self) -> ExperimentResult:
        logger = self._active_logger
        results = []
        all_correct = True

        for trial in range(TRIALS):
            # 3-task chain: ST-01 → ST-02 → ST-03 (sequential dependencies)
            plan = (
                FixturePlanBuilder()
                .with_task("ST-01", agent="document_reader", tools=["read_db"])
                .with_task("ST-02", agent="document_reader", tools=["read_db"], depends_on=["ST-01"])
                .with_task("ST-03", agent="document_reader", tools=["read_db"], depends_on=["ST-02"])
                .build()
            )
            ar, tr, execution_order = _make_registries()
            result = await GovernedAgenticLoop(
                llm_client=MockLLMClient(responses=[plan]),
                policy_matrix=POLICY_MATRIX,
                agent_registry=ar, tool_registry=tr,
            ).run({"task": "ORC-001 dep test", "tenant_id": "t", "user_id": "u"})

            completed = result.outcome == "completed"
            order_correct = execution_order == ["ST-01", "ST-02", "ST-03"]
            correct = completed and order_correct

            if not correct: all_correct = False
            logger.info(
                f"  trial {trial+1}: outcome={result.outcome} "
                f"order={execution_order} → {'✓' if correct else '✗'}"
            )
            results.append({
                "trial": trial+1, "outcome": result.outcome,
                "execution_order": execution_order[:],
                "order_correct": order_correct, "correct": correct,
            })

        metrics = {
            "trials": TRIALS,
            "correct_order_count": sum(1 for r in results if r["order_correct"]),
            "completed_count": sum(1 for r in results if r["outcome"] == "completed"),
            "dependency_order_rate": round(sum(1 for r in results if r["order_correct"]) / TRIALS, 4),
            "all_correct": all_correct,
        }

        if all_correct:
            verdict, hyp = Verdict.PASS, True
            summary = f"Task dependency ordering enforced correctly in all {TRIALS} trials — ST-01→ST-02→ST-03 every time."
            observations = [
                "3-task dependency chain always executes in declared order.",
                "No task executes before its dependency completes.",
                "outcome=completed in all trials.",
            ]
        else:
            failed = [r for r in results if not r["correct"]]
            verdict, hyp = Verdict.FAIL, False
            summary = f"Dependency ordering violated in {len(failed)} trials."
            observations = [str(failed[:3])]

        return ExperimentResult(verdict=verdict, summary=summary,
            hypothesis_supported=hyp, metrics=metrics,
            observations=observations, raw_outputs=results)

    async def teardown(self): pass

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--findings-dir", default="findings")
    args = p.parse_args()
    exp = ORC_001(); result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}\nSummary : {result.summary}")
    for k, v in result.metrics.items(): print(f"  {k:<45} {v}")
