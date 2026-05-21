"""HIL-002 — HITL Approval Flow Correctness | Tier 1 | Depends on: HIL-001"""
from __future__ import annotations
import sys
from pathlib import Path
_r = Path(__file__).resolve().parents[3]
if str(_r) not in sys.path: sys.path.insert(0, str(_r))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _helpers import POLICY_MATRIX, make_registries, gated_plan, safe_plan
from daf import GovernedAgenticLoop
from daf.testing import MockLLMClient
from daf.runtime.human_review_gateway import StubHumanReviewGateway
from daf.research.base import BaseExperiment, ExperimentResult, Verdict, Domain, Tier

TRIALS = 10

class HIL_002(BaseExperiment):
    experiment_id = "HIL-002"
    domain = Domain.HUMAN_IN_LOOP
    tier = Tier.OFFLINE
    title = "HITL Approval Flow Correctness"
    research_question = "Does an approved HumanReviewResponse correctly unblock plan execution?"
    hypothesis = "A StubHumanReviewGateway returning approved causes the gated task to execute and the workflow to complete."
    depends_on = ["HIL-001"]
    estimated_cost_usd = 0.0
    estimated_minutes = 5

    async def prepare(self): pass

    async def run(self) -> ExperimentResult:
        logger = self._active_logger
        results = []
        all_correct = True

        for trial in range(TRIALS):
            gateway = StubHumanReviewGateway(approve_all=True)
            ar, tr = make_registries()

            result = await GovernedAgenticLoop(
                llm_client=MockLLMClient(responses=[gated_plan()]),
                policy_matrix=POLICY_MATRIX,
                agent_registry=ar, tool_registry=tr,
                hitl_gateway=gateway,
            ).run({"task": "HIL-002 approval test", "tenant_id": "t", "user_id": "u"})

            gateway_called   = len(gateway.requests) == 1
            completed        = result.outcome == "completed"
            one_iteration    = result.loop_iterations == 1
            all_ok = gateway_called and completed and one_iteration

            if not all_ok: all_correct = False
            logger.info(
                f"  trial {trial+1}: gateway_called={gateway_called} "
                f"outcome={result.outcome} iterations={result.loop_iterations} "
                f"→ {'✓' if all_ok else '✗'}"
            )
            results.append({
                "trial": trial+1, "gateway_called": gateway_called,
                "outcome": result.outcome, "iterations": result.loop_iterations,
                "correct": all_ok,
            })

        metrics = {
            "trials": TRIALS,
            "gateway_called_count": sum(1 for r in results if r["gateway_called"]),
            "completed_count": sum(1 for r in results if r["outcome"] == "completed"),
            "single_iteration_count": sum(1 for r in results if r["iterations"] == 1),
            "all_correct": all_correct,
            "approval_unblocks_execution": all_correct,
        }

        if all_correct:
            verdict, hyp = Verdict.PASS, True
            summary = f"Approved HITL response unblocks execution correctly — workflow completes in 1 iteration {TRIALS}/{TRIALS} trials."
            observations = [
                "Gateway called exactly once per gated plan.",
                "Approved response produces outcome=completed.",
                "Loop completes in exactly 1 iteration — no replanning needed.",
            ]
        else:
            verdict, hyp = Verdict.FAIL, False
            summary = "HITL approval flow incorrect."
            observations = [str([r for r in results if not r["correct"]])]

        return ExperimentResult(verdict=verdict, summary=summary,
            hypothesis_supported=hyp, metrics=metrics,
            observations=observations, raw_outputs=results)

    async def teardown(self): pass

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--findings-dir", default="findings")
    args = p.parse_args()
    exp = HIL_002(); result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}\nSummary : {result.summary}")
    for k, v in result.metrics.items(): print(f"  {k:<45} {v}")
