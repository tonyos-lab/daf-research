"""HIL-004 — HITL Timeout Behaviour | Tier 1 | Depends on: HIL-003"""
from __future__ import annotations
import sys, uuid
from pathlib import Path
_r = Path(__file__).resolve().parents[3]
if str(_r) not in sys.path: sys.path.insert(0, str(_r))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _helpers import POLICY_MATRIX, make_registries, gated_plan
from daf import GovernedAgenticLoop
from daf.testing import MockLLMClient
from daf.runtime.human_review_gateway import StubHumanReviewGateway
from daf.models.human_review import HumanReviewRequest
from daf.research.base import BaseExperiment, ExperimentResult, Verdict, Domain, Tier

TRIALS = 10

class HIL_004(BaseExperiment):
    experiment_id = "HIL-004"
    domain = Domain.HUMAN_IN_LOOP
    tier = Tier.OFFLINE
    title = "HITL Timeout Behaviour"
    research_question = "How does the loop handle a HITL gateway that times out?"
    hypothesis = "A timed-out HumanReviewResponse is treated identically to a rejection — always-timeout escalates after max_replan_attempts."
    depends_on = ["HIL-003"]
    estimated_cost_usd = 0.0
    estimated_minutes = 5

    async def prepare(self): pass

    async def run(self) -> ExperimentResult:
        logger = self._active_logger
        results = []
        all_correct = True

        # Scenario A: always timeout → escalates (same as always-reject)
        logger.info("Scenario A: always timeout → escalate")
        for trial in range(TRIALS):
            gateway = StubHumanReviewGateway(simulate_timeout=True)
            ar, tr = make_registries()
            result = await GovernedAgenticLoop(
                llm_client=MockLLMClient(responses=[gated_plan()] * 10),
                policy_matrix=POLICY_MATRIX,
                agent_registry=ar, tool_registry=tr,
                hitl_gateway=gateway,
            ).run({"task": "HIL-004 timeout test", "tenant_id": "t", "user_id": "u"})

            escalated = result.outcome == "escalated"
            gateway_called = len(gateway.requests) >= 1
            correct = escalated and gateway_called
            if not correct: all_correct = False
            logger.info(
                f"  trial {trial+1}: outcome={result.outcome} "
                f"gateway_calls={len(gateway.requests)} → {'✓' if correct else '✗'}"
            )
            results.append({"scenario": "A", "trial": trial+1,
                            "outcome": result.outcome,
                            "gateway_calls": len(gateway.requests),
                            "correct": correct})

        # Scenario B: verify timed_out flag is True on timeout response
        logger.info("Scenario B: verify timed_out=True on response object")
        gateway_b = StubHumanReviewGateway(simulate_timeout=True)
        mock_req = HumanReviewRequest.create(
            grant_id=uuid.uuid4(),
            request_id=uuid.uuid4(),
            tenant_id="t",
            user_id="u",
            gated_tasks=[],
            workflow_task="test",
        )
        timeout_resp = await gateway_b.request_and_wait(mock_req)
        timed_out_flag = timeout_resp.timed_out   # must be True
        correct_B = timed_out_flag
        if not correct_B: all_correct = False
        logger.info(f"  timed_out flag = {timed_out_flag} → {'✓' if correct_B else '✗'}")
        results.append({"scenario": "B", "timed_out": timed_out_flag, "correct": correct_B})

        # Scenario C: compare timeout behaviour with explicit rejection behaviour
        logger.info("Scenario C: timeout produces same loop outcome as rejection")
        timeout_outcomes = []
        reject_outcomes  = []
        for _ in range(3):
            ar, tr = make_registries()
            r_timeout = await GovernedAgenticLoop(
                llm_client=MockLLMClient(responses=[gated_plan()] * 10),
                policy_matrix=POLICY_MATRIX,
                agent_registry=ar, tool_registry=tr,
                hitl_gateway=StubHumanReviewGateway(simulate_timeout=True),
            ).run({"task": "timeout", "tenant_id": "t", "user_id": "u"})
            timeout_outcomes.append(r_timeout.outcome)

            ar2, tr2 = make_registries()
            r_reject = await GovernedAgenticLoop(
                llm_client=MockLLMClient(responses=[gated_plan()] * 10),
                policy_matrix=POLICY_MATRIX,
                agent_registry=ar2, tool_registry=tr2,
                hitl_gateway=StubHumanReviewGateway(approve_all=False),
            ).run({"task": "reject", "tenant_id": "t", "user_id": "u"})
            reject_outcomes.append(r_reject.outcome)

        outcomes_match = timeout_outcomes == reject_outcomes
        if not outcomes_match: all_correct = False
        logger.info(f"  timeout={timeout_outcomes} reject={reject_outcomes} match={outcomes_match}")
        results.append({"scenario": "C", "timeout_outcomes": timeout_outcomes,
                        "reject_outcomes": reject_outcomes, "correct": outcomes_match})

        A_results = [r for r in results if r["scenario"] == "A"]
        escalated_rate = sum(1 for r in A_results if r["correct"]) / TRIALS
        metrics = {
            "trials": TRIALS,
            "timeout_escalates_rate": round(escalated_rate, 4),
            "timed_out_flag_set": timed_out_flag,
            "timeout_identical_to_rejection": outcomes_match,
            "all_correct": all_correct,
        }

        if all_correct:
            verdict, hyp = Verdict.PASS, True
            summary = "HITL timeout treated identically to rejection — escalates 100%, timed_out flag set, same loop outcome as reject."
            observations = [
                "Always-timeout gateway causes escalation identical to always-reject.",
                "timed_out=True is correctly set on timeout response objects.",
                "Timeout and rejection produce identical loop outcomes.",
            ]
        else:
            verdict, hyp = Verdict.FAIL, False
            summary = f"HITL timeout incorrect: escalated_rate={escalated_rate} timed_out_flag={timed_out_flag} outcomes_match={outcomes_match}"
            observations = [f"escalated_rate={escalated_rate}", f"flag={timed_out_flag}", f"match={outcomes_match}"]

        return ExperimentResult(verdict=verdict, summary=summary,
            hypothesis_supported=hyp, metrics=metrics,
            observations=observations, raw_outputs=results[:12])

    async def teardown(self): pass

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--findings-dir", default="findings")
    args = p.parse_args()
    exp = HIL_004(); result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}\nSummary : {result.summary}")
    for k, v in result.metrics.items(): print(f"  {k:<45} {v}")
