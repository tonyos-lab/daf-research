"""HIL-005 — No Gateway Auto-Rejection | Tier 1 | Depends on: HIL-001"""
from __future__ import annotations
import sys
from pathlib import Path
_r = Path(__file__).resolve().parents[3]
if str(_r) not in sys.path: sys.path.insert(0, str(_r))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _helpers import POLICY_MATRIX, make_registries, gated_plan, safe_plan
from daf import GovernedAgenticLoop
from daf.testing import MockLLMClient
from daf.research.base import BaseExperiment, ExperimentResult, Verdict, Domain, Tier

TRIALS = 10

class HIL_005(BaseExperiment):
    experiment_id = "HIL-005"
    domain = Domain.HUMAN_IN_LOOP
    tier = Tier.OFFLINE
    title = "No Gateway Auto-Rejection"
    research_question = "What happens when a plan requires HITL but no gateway is configured?"
    hypothesis = "When no HITL gateway is configured, all gated tasks are auto-rejected and the loop escalates after max_replan_attempts."
    depends_on = ["HIL-001"]
    estimated_cost_usd = 0.0
    estimated_minutes = 5

    async def prepare(self): pass

    async def run(self) -> ExperimentResult:
        logger = self._active_logger
        results = []
        all_correct = True

        # Scenario A: gated plan + no gateway → escalates
        logger.info("Scenario A: gated plan + no gateway → escalates")
        for trial in range(TRIALS):
            ar, tr = make_registries()
            result = await GovernedAgenticLoop(
                llm_client=MockLLMClient(responses=[gated_plan()] * 10),
                policy_matrix=POLICY_MATRIX,
                agent_registry=ar, tool_registry=tr,
                hitl_gateway=None,  # no gateway
            ).run({"task": "HIL-005 no-gateway gated", "tenant_id": "t", "user_id": "u"})

            escalated = result.outcome == "escalated"
            if not escalated: all_correct = False
            logger.info(f"  trial {trial+1}: outcome={result.outcome} → {'✓' if escalated else '✗'}")
            results.append({"scenario": "A", "trial": trial+1,
                            "outcome": result.outcome, "correct": escalated})

        # Scenario B: safe plan + no gateway → completes (gateway not needed)
        logger.info("Scenario B: safe plan + no gateway → completes normally")
        for trial in range(TRIALS):
            ar, tr = make_registries()
            result = await GovernedAgenticLoop(
                llm_client=MockLLMClient(responses=[safe_plan()]),
                policy_matrix=POLICY_MATRIX,
                agent_registry=ar, tool_registry=tr,
                hitl_gateway=None,
            ).run({"task": "HIL-005 no-gateway safe", "tenant_id": "t", "user_id": "u"})

            completed = result.outcome == "completed"
            if not completed: all_correct = False
            logger.info(f"  trial {trial+1}: outcome={result.outcome} → {'✓' if completed else '✗'}")
            results.append({"scenario": "B", "trial": trial+1,
                            "outcome": result.outcome, "correct": completed})

        A_results = [r for r in results if r["scenario"] == "A"]
        B_results = [r for r in results if r["scenario"] == "B"]
        metrics = {
            "trials_per_scenario": TRIALS,
            "no_gateway_gated_escalates": round(sum(1 for r in A_results if r["correct"]) / TRIALS, 4),
            "no_gateway_safe_completes": round(sum(1 for r in B_results if r["correct"]) / TRIALS, 4),
            "all_correct": all_correct,
        }

        if all_correct:
            verdict, hyp = Verdict.PASS, True
            summary = "No gateway: gated plans escalate 100%, safe plans complete normally — auto-rejection behaviour confirmed."
            observations = [
                "Gated tasks are auto-rejected when no gateway is configured.",
                "Safe (non-gated) plans complete normally without a gateway.",
                "Auto-rejection triggers replan loop → eventually escalates.",
            ]
        else:
            verdict, hyp = Verdict.FAIL, False
            summary = "No-gateway auto-rejection behaviour incorrect."
            observations = [f"A_rate={sum(1 for r in A_results if r['correct'])/TRIALS}",
                            f"B_rate={sum(1 for r in B_results if r['correct'])/TRIALS}"]

        return ExperimentResult(verdict=verdict, summary=summary,
            hypothesis_supported=hyp, metrics=metrics,
            observations=observations, raw_outputs=results[:20])

    async def teardown(self): pass

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--findings-dir", default="findings")
    args = p.parse_args()
    exp = HIL_005(); result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}\nSummary : {result.summary}")
    for k, v in result.metrics.items(): print(f"  {k:<45} {v}")
