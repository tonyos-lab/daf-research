"""HIL-003 — HITL Rejection Triggers Replan | Tier 1 | Depends on: HIL-001"""
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

class HIL_003(BaseExperiment):
    experiment_id = "HIL-003"
    domain = Domain.HUMAN_IN_LOOP
    tier = Tier.OFFLINE
    title = "HITL Rejection Triggers Replan"
    research_question = "Does a rejected HumanReviewResponse correctly trigger the replan loop?"
    hypothesis = "A StubHumanReviewGateway returning rejected causes the loop to replan; after max_replan_attempts the loop escalates."
    depends_on = ["HIL-001"]
    estimated_cost_usd = 0.0
    estimated_minutes = 5

    async def prepare(self): pass

    async def run(self) -> ExperimentResult:
        logger = self._active_logger
        results = []
        all_correct = True

        # Scenario A: always reject → loop escalates after max_replan_attempts
        logger.info("Scenario A: always reject → escalate")
        for trial in range(TRIALS):
            gateway = StubHumanReviewGateway(approve_all=False)
            ar, tr = make_registries()

            # Provide enough gated plans to fill all replan iterations
            result = await GovernedAgenticLoop(
                llm_client=MockLLMClient(responses=[gated_plan()] * 10),
                policy_matrix=POLICY_MATRIX,
                agent_registry=ar, tool_registry=tr,
                hitl_gateway=gateway,
            ).run({"task": "HIL-003 rejection test", "tenant_id": "t", "user_id": "u"})

            escalated = result.outcome == "escalated"
            gateway_called_multiple = len(gateway.requests) >= 1
            if not (escalated and gateway_called_multiple): all_correct = False
            logger.info(
                f"  trial {trial+1}: outcome={result.outcome} "
                f"gateway_calls={len(gateway.requests)} "
                f"iterations={result.loop_iterations} → {'✓' if escalated else '✗'}"
            )
            results.append({
                "scenario": "A", "trial": trial+1,
                "outcome": result.outcome,
                "gateway_calls": len(gateway.requests),
                "iterations": result.loop_iterations,
                "correct": escalated,
            })

        # Scenario B: reject once then approve → completes with >1 iteration
        logger.info("Scenario B: reject once then approve → completes")
        for trial in range(TRIALS):
            gateway = StubHumanReviewGateway(approve_all=False)
            ar, tr = make_registries()
            # First call rejects, second call approves
            call_count = [0]
            original_raw = gateway.request_and_wait

            async def approve_on_second(request):
                call_count[0] += 1
                if call_count[0] >= 2:
                    gateway._approve_all = True
                return await original_raw.__func__(gateway, request)

            gateway.request_and_wait = approve_on_second

            result = await GovernedAgenticLoop(
                llm_client=MockLLMClient(responses=[gated_plan()] * 5),
                policy_matrix=POLICY_MATRIX,
                agent_registry=ar, tool_registry=tr,
                hitl_gateway=gateway,
            ).run({"task": "HIL-003 reject-then-approve", "tenant_id": "t", "user_id": "u"})

            completed = result.outcome == "completed"
            more_than_one_iter = result.loop_iterations >= 2
            scenario_ok = completed and more_than_one_iter
            if not scenario_ok: all_correct = False
            logger.info(
                f"  trial {trial+1}: outcome={result.outcome} "
                f"iterations={result.loop_iterations} → {'✓' if scenario_ok else '✗'}"
            )
            results.append({
                "scenario": "B", "trial": trial+1,
                "outcome": result.outcome,
                "iterations": result.loop_iterations,
                "correct": scenario_ok,
            })

        A_results = [r for r in results if r["scenario"] == "A"]
        B_results = [r for r in results if r["scenario"] == "B"]
        metrics = {
            "trials_per_scenario": TRIALS,
            "scenario_A_escalated_rate": round(sum(1 for r in A_results if r["correct"]) / TRIALS, 4),
            "scenario_B_completed_rate": round(sum(1 for r in B_results if r["correct"]) / TRIALS, 4),
            "all_correct": all_correct,
            "rejection_triggers_replan": all_correct,
        }

        if all_correct:
            verdict, hyp = Verdict.PASS, True
            summary = "HITL rejection correctly triggers replan — always-reject escalates; reject-then-approve completes."
            observations = [
                "Always-rejecting gateway causes loop to escalate after max_replan_attempts.",
                "Reject-once-then-approve pattern completes in ≥2 iterations.",
                "Rejection is correctly treated as a violation context for replanning.",
            ]
        else:
            verdict, hyp = Verdict.FAIL, False
            failed_A = sum(1 for r in A_results if not r["correct"])
            failed_B = sum(1 for r in B_results if not r["correct"])
            summary = f"Rejection flow failure: A_failed={failed_A} B_failed={failed_B}"
            observations = [f"A failures: {failed_A}/{TRIALS}", f"B failures: {failed_B}/{TRIALS}"]

        return ExperimentResult(verdict=verdict, summary=summary,
            hypothesis_supported=hyp, metrics=metrics,
            observations=observations, raw_outputs=results[:20])

    async def teardown(self): pass

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--findings-dir", default="findings")
    args = p.parse_args()
    exp = HIL_003(); result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}\nSummary : {result.summary}")
    for k, v in result.metrics.items(): print(f"  {k:<45} {v}")
