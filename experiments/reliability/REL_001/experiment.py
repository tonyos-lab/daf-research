"""
experiments/reliability/REL_001/experiment.py
=============================================
REL-001 — Per-Call Reliability Characterisation

Research Question:
    Can per-call reliability be formally characterised as a function
    of call type and model tier?

Hypothesis:
    A MockLLMClient with fail_after=N raises LLMClientError on exactly
    call number N+1, giving exactly N successful calls before failure.
    This holds deterministically for N in [0, 1, 2, 3, 5].

Tier: 1 (fully offline — no API key, no Docker required)
Depends on: none
"""

from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[3]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from daf.testing import MockLLMClient, FixturePlanBuilder
from daf.runtime.llm_client import LLMClientError

from daf.research.base import (
    BaseExperiment,
    ExperimentResult,
    Verdict,
    Domain,
    Tier,
)

FAIL_AFTER_VALUES = [0, 1, 2, 3, 5]


class REL_001(BaseExperiment):

    experiment_id      = "REL-001"
    domain             = Domain.RELIABILITY
    tier               = Tier.OFFLINE
    title              = "Per-Call Reliability Characterisation"
    research_question  = (
        "Can per-call reliability be formally characterised as a "
        "function of call type and model tier?"
    )
    hypothesis         = (
        "A MockLLMClient with fail_after=N raises LLMClientError on "
        "exactly call N+1, giving exactly N successful calls. "
        "This holds deterministically for N in [0, 1, 2, 3, 5]."
    )
    depends_on         = []
    estimated_cost_usd = 0.0
    estimated_minutes  = 2

    # minimal valid plan dict — reused across all calls
    _PLAN: dict = {}

    async def prepare(self) -> None:
        self._PLAN = (
            FixturePlanBuilder()
            .with_task("ST-01", agent="document_reader", tools=["read_db"])
            .build()
        )

    async def run(self) -> ExperimentResult:
        logger = self._active_logger
        results_per_n = {}
        all_pass = True
        raw_outputs = []

        for n in FAIL_AFTER_VALUES:
            # fail_after=N: calls 1..N succeed, call N+1 raises
            client = MockLLMClient(
                responses=[self._PLAN] * (n + 2),
                fail_after=n,
            )

            successful_calls = 0
            error_on_call    = None

            for call_num in range(1, n + 3):
                try:
                    await client.complete(
                        system="test system prompt",
                        user="test user message",
                        schema={},
                    )
                    successful_calls += 1
                except LLMClientError:
                    error_on_call = call_num
                    break

            expected_successes = n
            expected_error_on  = n + 1
            passed = (
                successful_calls == expected_successes
                and error_on_call == expected_error_on
            )

            if not passed:
                all_pass = False

            logger.info(
                f"fail_after={n}: "
                f"successful={successful_calls} (expected {expected_successes}), "
                f"error_on_call={error_on_call} (expected {expected_error_on}) "
                f"→ {'PASS' if passed else 'FAIL'}"
            )

            results_per_n[n] = {
                "expected_successes": expected_successes,
                "actual_successes":   successful_calls,
                "expected_error_on":  expected_error_on,
                "actual_error_on":    error_on_call,
                "passed":             passed,
            }
            raw_outputs.append({"fail_after": n, **results_per_n[n]})

        metrics = {
            "values_tested":     len(FAIL_AFTER_VALUES),
            "values_passed":     sum(1 for r in results_per_n.values() if r["passed"]),
            "values_failed":     sum(1 for r in results_per_n.values() if not r["passed"]),
            "all_deterministic": all_pass,
        }
        for n, r in results_per_n.items():
            metrics[f"fail_after_{n}_passed"] = r["passed"]

        if all_pass:
            verdict = Verdict.PASS
            summary = (
                f"MockLLMClient fail_after is deterministic across all "
                f"{len(FAIL_AFTER_VALUES)} tested values — hypothesis supported."
            )
            hypothesis_supported = True
            observations = [
                f"Tested fail_after values: {FAIL_AFTER_VALUES}",
                "Each value produced exactly N successful calls before LLMClientError.",
                "DAF planning-stage failure injection is fully deterministic.",
            ]
        else:
            failed_ns = [n for n, r in results_per_n.items() if not r["passed"]]
            verdict = Verdict.FAIL
            summary = (
                f"Non-determinism detected for fail_after={failed_ns} — "
                f"hypothesis NOT supported."
            )
            hypothesis_supported = False
            observations = [
                f"Failed for fail_after values: {failed_ns}",
                "MockLLMClient call counting may be incorrect.",
            ]

        return ExperimentResult(
            verdict=verdict,
            summary=summary,
            hypothesis_supported=hypothesis_supported,
            metrics=metrics,
            observations=observations,
            raw_outputs=raw_outputs,
        )

    async def teardown(self) -> None:
        pass


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run REL-001")
    parser.add_argument("--findings-dir", default="findings")
    args = parser.parse_args()

    exp    = REL_001()
    result = exp.execute(findings_dir=args.findings_dir)

    print(f"\nVerdict  : {result.verdict.value.upper()}")
    print(f"Summary  : {result.summary}")
    print(f"Metrics  :")
    for k, v in result.metrics.items():
        print(f"  {k:<40} {v}")
