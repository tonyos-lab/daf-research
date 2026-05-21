"""HIL-001 — HITL Gate Trigger Accuracy | Tier 1 | Depends on: none"""
from __future__ import annotations
import sys
from pathlib import Path
_r = Path(__file__).resolve().parents[3]
if str(_r) not in sys.path: sys.path.insert(0, str(_r))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _helpers import POLICY_MATRIX, make_registries, gated_plan, safe_plan, mixed_plan, GATED_DATA, SAFE_DATA
from daf import GovernedAgenticLoop
from daf.testing import MockLLMClient
from daf.runtime.human_review_gateway import StubHumanReviewGateway
from daf.research.base import BaseExperiment, ExperimentResult, Verdict, Domain, Tier

TRIALS = 10

class HIL_001(BaseExperiment):
    experiment_id = "HIL-001"
    domain = Domain.HUMAN_IN_LOOP
    tier = Tier.OFFLINE
    title = "HITL Gate Trigger Accuracy"
    research_question = "Does the EvaluateStage gate exactly the tasks that match always_gate_action_classes?"
    hypothesis = "Every irreversible task at low confidence is gated 100% of the time; reversible tasks at high confidence are never gated."
    depends_on = []
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

            # Gated plan — gateway should receive exactly 1 request
            result = await GovernedAgenticLoop(
                llm_client=MockLLMClient(responses=[gated_plan()]),
                policy_matrix=POLICY_MATRIX,
                agent_registry=ar, tool_registry=tr,
                hitl_gateway=gateway,
            ).run({"task": "HIL-001 gated", "tenant_id": "t", "user_id": "u"})

            gateway_called = len(gateway.requests) == 1
            gated_task_correct = (
                gateway_called and
                gateway.requests[0].gated_task_ids == ["ST-01"]
            )
            gated_outcome_ok = result.outcome == "completed"
            gated_ok = gated_task_correct and gated_outcome_ok

            # Safe plan — gateway should NOT be called
            gateway2 = StubHumanReviewGateway(approve_all=True)
            result2 = await GovernedAgenticLoop(
                llm_client=MockLLMClient(responses=[safe_plan()]),
                policy_matrix=POLICY_MATRIX,
                agent_registry=ar, tool_registry=tr,
                hitl_gateway=gateway2,
            ).run({"task": "HIL-001 safe", "tenant_id": "t", "user_id": "u"})

            safe_not_gated = len(gateway2.requests) == 0
            safe_outcome_ok = result2.outcome == "completed"
            safe_ok = safe_not_gated and safe_outcome_ok

            if not (gated_ok and safe_ok): all_correct = False
            logger.info(f"  trial {trial+1}: gated_ok={gated_ok} safe_ok={safe_ok}")
            results.append({"trial": trial+1, "gated_ok": gated_ok, "safe_ok": safe_ok})

        gated_pass = sum(1 for r in results if r["gated_ok"])
        safe_pass  = sum(1 for r in results if r["safe_ok"])
        metrics = {
            "trials": TRIALS,
            "gated_task_triggered_correctly": gated_pass,
            "safe_task_not_gated": safe_pass,
            "gated_trigger_rate": round(gated_pass / TRIALS, 4),
            "false_gate_rate": round((TRIALS - safe_pass) / TRIALS, 4),
            "all_correct": all_correct,
        }

        if all_correct:
            verdict, hyp = Verdict.PASS, True
            summary = f"HITL gate triggers exactly on always_gate tasks and never on safe tasks — 100% accuracy across {TRIALS} trials."
            observations = [
                f"Task with data_required={GATED_DATA!r} triggers gateway 100%.",
                f"Task with data_required={SAFE_DATA!r} never triggers gateway (0% false-gate rate).",
                "Approved gated plans complete successfully.",
            ]
        else:
            verdict, hyp = Verdict.FAIL, False
            summary = "HITL gate trigger accuracy failure."
            observations = [f"gated_pass={gated_pass}/{TRIALS} safe_pass={safe_pass}/{TRIALS}"]

        return ExperimentResult(verdict=verdict, summary=summary,
            hypothesis_supported=hyp, metrics=metrics,
            observations=observations, raw_outputs=results)

    async def teardown(self): pass

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--findings-dir", default="findings")
    args = p.parse_args()
    exp = HIL_001(); result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}\nSummary : {result.summary}")
    for k, v in result.metrics.items(): print(f"  {k:<45} {v}")
