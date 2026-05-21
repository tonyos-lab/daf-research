"""
REL-002 — Reliability Composability Under Sequential Tasks
Tier: 1 | Depends on: REL-001
"""
from __future__ import annotations
import sys, time, statistics
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


def _make_agent_class(role):
    return type(f"{role.title()}Agent", (StubAgent,), {"role": role})


def _plan_n_tasks(n: int) -> dict:
    builder = FixturePlanBuilder()
    for i in range(1, n + 1):
        deps = [f"ST-{i-1:02d}"] if i > 1 else []
        builder.with_task(
            f"ST-{i:02d}", agent="document_reader",
            tools=["read_db"], depends_on=deps,
        )
    return builder.build()


class REL_002(BaseExperiment):
    experiment_id      = "REL-002"
    domain             = Domain.RELIABILITY
    tier               = Tier.OFFLINE
    title              = "Reliability Composability Under Sequential Tasks"
    research_question  = "Does reliability compose predictably when multiple tasks are chained in a single plan?"
    hypothesis         = (
        "A multi-task plan where each task is independently reliable "
        "produces consistent outcomes across repeated runs — no task "
        "chain introduces hidden failure modes under nominal conditions."
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
        self._agent_registry.register(_make_agent_class("document_reader"))

    async def run(self) -> ExperimentResult:
        logger = self._active_logger
        raw_outputs = []
        chain_results = {}

        # Test 1, 2, 3, and 5-task chains
        for n_tasks in [1, 2, 3, 5]:
            successes = 0
            durations = []
            logger.info(f"Chain length {n_tasks}: running {TRIALS} trials")

            for trial in range(TRIALS):
                t0 = time.perf_counter()
                result = await GovernedAgenticLoop(
                    llm_client=MockLLMClient(responses=[_plan_n_tasks(n_tasks)]),
                    policy_matrix=POLICY_MATRIX,
                    agent_registry=self._agent_registry,
                    tool_registry=self._tool_registry,
                ).run({
                    "task":      f"Chain test {n_tasks} tasks",
                    "tenant_id": "rel-test", "user_id": "researcher",
                })
                elapsed_ms = (time.perf_counter() - t0) * 1000
                durations.append(elapsed_ms)

                if result.outcome == "completed":
                    successes += 1

                raw_outputs.append({
                    "chain_length": n_tasks, "trial": trial + 1,
                    "outcome": result.outcome, "duration_ms": round(elapsed_ms, 2),
                })

            rate = successes / TRIALS
            chain_results[n_tasks] = {
                "success_rate": round(rate, 4),
                "successes": successes,
                "mean_ms": round(statistics.mean(durations), 2),
                "std_ms": round(statistics.stdev(durations) if len(durations) > 1 else 0.0, 2),
            }
            logger.info(
                f"  chain={n_tasks} success_rate={rate:.4f} "
                f"mean={chain_results[n_tasks]['mean_ms']:.1f}ms"
            )

        # Composability hypothesis: all chains should succeed 100% under nominal conditions
        all_perfect = all(r["success_rate"] == 1.0 for r in chain_results.values())

        # Duration should grow roughly linearly with chain length (not exponentially)
        durations_by_chain = [chain_results[n]["mean_ms"] for n in [1, 2, 3, 5]]
        duration_ratio_5_to_1 = durations_by_chain[3] / max(durations_by_chain[0], 0.001)
        linear_growth = duration_ratio_5_to_1 <= 10.0  # 5-task chain takes at most 10x 1-task

        metrics = {
            "trials_per_chain":           TRIALS,
            "chain_lengths_tested":       [1, 2, 3, 5],
            "chain_1_success_rate":       chain_results[1]["success_rate"],
            "chain_2_success_rate":       chain_results[2]["success_rate"],
            "chain_3_success_rate":       chain_results[3]["success_rate"],
            "chain_5_success_rate":       chain_results[5]["success_rate"],
            "all_chains_100_pct":         all_perfect,
            "chain_1_mean_ms":            chain_results[1]["mean_ms"],
            "chain_5_mean_ms":            chain_results[5]["mean_ms"],
            "duration_ratio_5_to_1":      round(duration_ratio_5_to_1, 2),
            "duration_scales_linearly":   linear_growth,
        }

        if all_perfect and linear_growth:
            verdict, hyp = Verdict.PASS, True
            summary = (
                f"All chain lengths (1–5 tasks) succeed 100% across {TRIALS} trials — "
                f"reliability composes perfectly under nominal conditions."
            )
            observations = [
                "1, 2, 3, and 5-task chains all achieve 100% success rate.",
                f"Duration scales {duration_ratio_5_to_1:.1f}x from 1 to 5 tasks (linear).",
                "No hidden failure modes introduced by task chaining.",
            ]
        elif all_perfect:
            verdict, hyp = Verdict.PASS, True
            summary = "All chains 100% successful; duration growth is non-linear but acceptable."
            observations = [f"Duration ratio 5-to-1 chain: {duration_ratio_5_to_1:.1f}x"]
        else:
            failed = {n: r for n, r in chain_results.items() if r["success_rate"] < 1.0}
            verdict, hyp = Verdict.FAIL, False
            summary = f"Reliability degraded in chains: {list(failed.keys())}"
            observations = [f"Failed chains: {failed}"]

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
    exp = REL_002(); result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}\nSummary : {result.summary}")
    for k, v in result.metrics.items(): print(f"  {k:<45} {v}")
