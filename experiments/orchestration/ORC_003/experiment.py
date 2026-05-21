"""ORC-003 — Multi-Agent Plan Execution Isolation | Tier 1 | Depends on: ORC-002"""
from __future__ import annotations
import sys, asyncio
from pathlib import Path
_r = Path(__file__).resolve().parents[3]
if str(_r) not in sys.path: sys.path.insert(0, str(_r))

from daf import GovernedAgenticLoop
from daf.testing import MockLLMClient, FixturePlanBuilder
from daf.runtime.agent_registry import AgentRegistry
from daf.runtime.tool_registry import ToolRegistry
from daf.runtime.tool import ToolNotFoundError
from daf.agents import StubAgent
from daf.tools import StubTool
from daf.research.base import BaseExperiment, ExperimentResult, Verdict, Domain, Tier

POLICY_MATRIX = str(_r / "policy" / "matrix" / "example.yaml")
TRIALS = 10


class ORC_003(BaseExperiment):
    experiment_id = "ORC-003"
    domain = Domain.ORCHESTRATION
    tier = Tier.OFFLINE
    title = "Multi-Agent Plan Execution Isolation"
    research_question = "Do multiple agents in a single plan share any mutable state?"
    hypothesis = "Two agents executing in the same plan cannot read or write each other's ScopedContext — each agent only sees its own permitted tools."
    depends_on = ["ORC-002"]
    estimated_cost_usd = 0.0
    estimated_minutes = 5

    async def prepare(self): pass

    async def run(self) -> ExperimentResult:
        logger = self._active_logger
        results = []
        all_correct = True

        for trial in range(TRIALS):
            # Track what each agent sees
            seen_tools = {}

            class ReaderAgent(StubAgent):
                role = "document_reader"
                async def execute(self, task, context):
                    seen_tools["document_reader"] = list(context.tools.names())
                    # Try to access risk_analyzer's tool — should fail
                    try:
                        context.tools.get("llm_extraction")
                        seen_tools["reader_accessed_analyzer_tool"] = True
                    except ToolNotFoundError:
                        seen_tools["reader_accessed_analyzer_tool"] = False
                    return await StubAgent.execute(self, task, context)

            class RiskAgent(StubAgent):
                role = "risk_analyzer"
                async def execute(self, task, context):
                    seen_tools["risk_analyzer"] = list(context.tools.names())
                    # Try to access document_reader's tool — should fail
                    try:
                        context.tools.get("read_db")
                        seen_tools["analyzer_accessed_reader_tool"] = True
                    except ToolNotFoundError:
                        seen_tools["analyzer_accessed_reader_tool"] = False
                    return await StubAgent.execute(self, task, context)

            tr = ToolRegistry()
            tr.register(StubTool(name="read_db",        idempotent=True))
            tr.register(StubTool(name="llm_extraction",  idempotent=True))
            tr.register(StubTool(name="llm_evaluation",  idempotent=True))

            ar = AgentRegistry()
            ar.register(ReaderAgent)
            ar.register(RiskAgent)

            plan = (
                FixturePlanBuilder()
                .with_task("ST-01", agent="document_reader", tools=["read_db"])
                .with_task("ST-02", agent="risk_analyzer",   tools=["llm_extraction"],
                           depends_on=["ST-01"])
                .build()
            )

            result = await GovernedAgenticLoop(
                llm_client=MockLLMClient(responses=[plan]),
                policy_matrix=POLICY_MATRIX,
                agent_registry=ar, tool_registry=tr,
            ).run({"task": "ORC-003 isolation test", "tenant_id": "t", "user_id": "u"})

            completed = result.outcome == "completed"
            reader_isolated = not seen_tools.get("reader_accessed_analyzer_tool", True)
            analyzer_isolated = not seen_tools.get("analyzer_accessed_reader_tool", True)
            reader_only_sees_own = seen_tools.get("document_reader", []) == ["read_db"]
            analyzer_tools = sorted(seen_tools.get("risk_analyzer", []))
            analyzer_only_sees_own = set(analyzer_tools) == {"llm_extraction", "llm_evaluation"}

            correct = all([completed, reader_isolated, analyzer_isolated,
                          reader_only_sees_own, analyzer_only_sees_own])
            if not correct: all_correct = False

            logger.info(
                f"  trial {trial+1}: outcome={result.outcome} "
                f"reader_isolated={reader_isolated} analyzer_isolated={analyzer_isolated} "
                f"→ {'✓' if correct else '✗'}"
            )
            results.append({
                "trial": trial+1, "outcome": result.outcome,
                "reader_isolated": reader_isolated,
                "analyzer_isolated": analyzer_isolated,
                "reader_tools": seen_tools.get("document_reader", []),
                "analyzer_tools": seen_tools.get("risk_analyzer", []),
                "correct": correct,
            })

        metrics = {
            "trials": TRIALS,
            "all_correct": all_correct,
            "reader_isolation_rate":   round(sum(1 for r in results if r["reader_isolated"]) / TRIALS, 4),
            "analyzer_isolation_rate": round(sum(1 for r in results if r["analyzer_isolated"]) / TRIALS, 4),
            "completed_rate":          round(sum(1 for r in results if r["outcome"] == "completed") / TRIALS, 4),
        }

        if all_correct:
            verdict, hyp = Verdict.PASS, True
            summary = f"Multi-agent isolation confirmed — each agent sees only its permitted tools across {TRIALS} trials."
            observations = [
                "document_reader cannot access risk_analyzer's llm_extraction tool.",
                "risk_analyzer cannot access document_reader's read_db tool.",
                "Each agent's tools.names() returns only its own permitted tools.",
                "Plan completes successfully despite strict isolation.",
            ]
        else:
            failed = [r for r in results if not r["correct"]]
            verdict, hyp = Verdict.FAIL, False
            summary = f"Agent isolation failure in {len(failed)} trials."
            observations = [str(failed[:2])]

        return ExperimentResult(verdict=verdict, summary=summary,
            hypothesis_supported=hyp, metrics=metrics,
            observations=observations, raw_outputs=results)

    async def teardown(self): pass

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--findings-dir", default="findings")
    args = p.parse_args()
    exp = ORC_003(); result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}\nSummary : {result.summary}")
    for k, v in result.metrics.items(): print(f"  {k:<45} {v}")
