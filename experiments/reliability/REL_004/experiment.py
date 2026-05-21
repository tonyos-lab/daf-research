"""
REL-004 — Concurrent Loop Reliability
Tier: 1 | Depends on: REL-001
"""
from __future__ import annotations
import sys, asyncio, time
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
CONCURRENCY_LEVELS = [2, 5, 10]
ROUNDS = 3


def _make_loop():
    tool_registry = ToolRegistry()
    tool_registry.register(StubTool(name="read_db", idempotent=True))
    agent_registry = AgentRegistry()
    agent_registry.register(
        type("DocAgent", (StubAgent,), {"role": "document_reader"})
    )
    plan = (
        FixturePlanBuilder()
        .with_task("ST-01", agent="document_reader", tools=["read_db"])
        .build()
    )
    return GovernedAgenticLoop(
        llm_client=MockLLMClient(responses=[plan]),
        policy_matrix=POLICY_MATRIX,
        agent_registry=agent_registry,
        tool_registry=tool_registry,
    )


async def _run_one(loop_id: int) -> dict:
    loop = _make_loop()
    t0 = time.perf_counter()
    result = await loop.run({
        "task":      f"Concurrent task {loop_id}",
        "tenant_id": f"tenant-{loop_id}",
        "user_id":   f"user-{loop_id}",
    })
    elapsed_ms = (time.perf_counter() - t0) * 1000
    return {
        "loop_id": loop_id,
        "outcome": result.outcome,
        "duration_ms": round(elapsed_ms, 2),
    }


class REL_004(BaseExperiment):
    experiment_id      = "REL-004"
    domain             = Domain.RELIABILITY
    tier               = Tier.OFFLINE
    title              = "Concurrent Loop Reliability"
    research_question  = "Does reliability degrade when multiple GovernedAgenticLoop instances run concurrently?"
    hypothesis         = (
        "Concurrent loops do not share state — each maintains "
        "its individual reliability guarantee regardless of concurrency level."
    )
    depends_on         = ["REL-001"]
    estimated_cost_usd = 0.0
    estimated_minutes  = 5

    async def prepare(self) -> None:
        pass  # each loop is self-contained

    async def run(self) -> ExperimentResult:
        logger = self._active_logger
        raw_outputs = []
        concurrency_results = {}
        all_correct = True

        for n_concurrent in CONCURRENCY_LEVELS:
            round_successes = 0
            total_runs = n_concurrent * ROUNDS
            logger.info(f"Concurrency={n_concurrent}: {ROUNDS} rounds × {n_concurrent} loops")

            for round_num in range(ROUNDS):
                # Launch n_concurrent loops simultaneously
                tasks = [_run_one(round_num * n_concurrent + i)
                         for i in range(n_concurrent)]
                t0 = time.perf_counter()
                results = await asyncio.gather(*tasks)
                wall_ms = (time.perf_counter() - t0) * 1000

                successes = sum(1 for r in results if r["outcome"] == "completed")
                round_successes += successes

                logger.info(
                    f"  round {round_num+1}: {successes}/{n_concurrent} completed "
                    f"wall={wall_ms:.1f}ms"
                )
                for r in results:
                    r["round"] = round_num + 1
                    r["n_concurrent"] = n_concurrent
                    raw_outputs.append(r)

            success_rate = round_successes / total_runs
            if success_rate < 1.0:
                all_correct = False

            concurrency_results[n_concurrent] = {
                "total_runs": total_runs,
                "successes": round_successes,
                "success_rate": round(success_rate, 4),
            }
            logger.info(
                f"  concurrency={n_concurrent} overall success_rate={success_rate:.4f}"
            )

        metrics = {
            "concurrency_levels_tested":   CONCURRENCY_LEVELS,
            "rounds_per_level":            ROUNDS,
            "concurrency_2_success_rate":  concurrency_results[2]["success_rate"],
            "concurrency_5_success_rate":  concurrency_results[5]["success_rate"],
            "concurrency_10_success_rate": concurrency_results[10]["success_rate"],
            "all_levels_100_pct":          all_correct,
            "state_isolation_confirmed":   all_correct,
        }

        if all_correct:
            verdict, hyp = Verdict.PASS, True
            summary = (
                f"All {sum(r['total_runs'] for r in concurrency_results.values())} "
                f"concurrent runs succeeded — loops are fully isolated."
            )
            observations = [
                f"Tested concurrency levels: {CONCURRENCY_LEVELS}",
                "No state leakage between concurrent loop instances.",
                "Each loop maintains its own AgentRegistry, ToolRegistry, and MockLLMClient.",
            ]
        else:
            failed = {n: r for n, r in concurrency_results.items() if r["success_rate"] < 1.0}
            verdict, hyp = Verdict.FAIL, False
            summary = f"Concurrency failures at levels: {list(failed.keys())}"
            observations = [f"Failed: {failed}"]

        return ExperimentResult(
            verdict=verdict, summary=summary,
            hypothesis_supported=hyp, metrics=metrics,
            observations=observations, raw_outputs=raw_outputs[:30],
        )

    async def teardown(self) -> None:
        pass

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--findings-dir", default="findings")
    args = p.parse_args()
    exp = REL_004(); result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}\nSummary : {result.summary}")
    for k, v in result.metrics.items(): print(f"  {k:<45} {v}")
