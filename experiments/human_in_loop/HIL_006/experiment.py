"""HIL-006 — Partial HITL Approval | Tier 1 | Depends on: HIL-002, HIL-003"""
from __future__ import annotations
import sys, uuid
from pathlib import Path
_r = Path(__file__).resolve().parents[3]
if str(_r) not in sys.path: sys.path.insert(0, str(_r))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from _helpers import POLICY_MATRIX, make_registries, GATED_DATA, SAFE_DATA
from daf import GovernedAgenticLoop
from daf.testing import MockLLMClient, FixturePlanBuilder
from daf.runtime.human_review_gateway import StubHumanReviewGateway
from daf.models.human_review import HumanReviewResponse, TaskDecision
from daf.research.base import BaseExperiment, ExperimentResult, Verdict, Domain, Tier

TRIALS = 10


def _two_gated_plan():
    """Plan with two gated tasks."""
    return (
        FixturePlanBuilder()
        .with_task("ST-01", agent="document_reader", tools=["read_db"],
                   data_sources=[GATED_DATA])
        .with_task("ST-02", agent="document_reader", tools=["read_db"],
                   data_sources=[GATED_DATA], depends_on=["ST-01"])
        .build()
    )


def _clean_one_gated_plan():
    """Plan where ST-01 is safe, ST-02 is gated."""
    return (
        FixturePlanBuilder()
        .with_task("ST-01", agent="document_reader", tools=["read_db"],
                   data_sources=[SAFE_DATA])
        .with_task("ST-02", agent="document_reader", tools=["read_db"],
                   data_sources=[GATED_DATA], depends_on=["ST-01"])
        .build()
    )


class HIL_006(BaseExperiment):
    experiment_id = "HIL-006"
    domain = Domain.HUMAN_IN_LOOP
    tier = Tier.OFFLINE
    title = "Partial HITL Approval"
    research_question = "Can a reviewer approve some gated tasks and reject others in a single review response?"
    hypothesis = "Mixed decisions in HumanReviewResponse: approved tasks execute, the loop replans for rejected tasks."
    depends_on = ["HIL-002", "HIL-003"]
    estimated_cost_usd = 0.0
    estimated_minutes = 5

    async def prepare(self): pass

    async def run(self) -> ExperimentResult:
        logger = self._active_logger
        results = []
        all_correct = True

        # Scenario A: all-approved multi-gated plan → completes
        logger.info("Scenario A: two gated tasks, both approved → completes")
        for trial in range(TRIALS):
            gateway = StubHumanReviewGateway(approve_all=True)
            ar, tr = make_registries()
            result = await GovernedAgenticLoop(
                llm_client=MockLLMClient(responses=[_two_gated_plan()]),
                policy_matrix=POLICY_MATRIX,
                agent_registry=ar, tool_registry=tr,
                hitl_gateway=gateway,
            ).run({"task": "HIL-006 all-approve", "tenant_id": "t", "user_id": "u"})

            ok = result.outcome == "completed"
            if not ok: all_correct = False
            results.append({"scenario": "A", "trial": trial+1,
                            "outcome": result.outcome, "correct": ok})
        rate_A = sum(1 for r in results if r["scenario"] == "A" and r["correct"]) / TRIALS
        logger.info(f"  all-approve rate: {rate_A:.4f}")

        # Scenario B: safe + one gated, gated approved → completes
        logger.info("Scenario B: safe + gated plan, gated approved → completes")
        for trial in range(TRIALS):
            gateway = StubHumanReviewGateway(approve_all=True)
            ar, tr = make_registries()
            result = await GovernedAgenticLoop(
                llm_client=MockLLMClient(responses=[_clean_one_gated_plan()]),
                policy_matrix=POLICY_MATRIX,
                agent_registry=ar, tool_registry=tr,
                hitl_gateway=gateway,
            ).run({"task": "HIL-006 mixed-plan", "tenant_id": "t", "user_id": "u"})

            ok = result.outcome == "completed"
            if not ok: all_correct = False
            results.append({"scenario": "B", "trial": trial+1,
                            "outcome": result.outcome, "correct": ok})
        rate_B = sum(1 for r in results if r["scenario"] == "B" and r["correct"]) / TRIALS
        logger.info(f"  safe+gated approved rate: {rate_B:.4f}")

        # Scenario C: all-rejected multi-gated plan → escalates
        logger.info("Scenario C: two gated tasks, all rejected → escalates")
        for trial in range(TRIALS):
            gateway = StubHumanReviewGateway(approve_all=False)
            ar, tr = make_registries()
            result = await GovernedAgenticLoop(
                llm_client=MockLLMClient(responses=[_two_gated_plan()] * 10),
                policy_matrix=POLICY_MATRIX,
                agent_registry=ar, tool_registry=tr,
                hitl_gateway=gateway,
            ).run({"task": "HIL-006 all-reject", "tenant_id": "t", "user_id": "u"})

            ok = result.outcome == "escalated"
            if not ok: all_correct = False
            results.append({"scenario": "C", "trial": trial+1,
                            "outcome": result.outcome, "correct": ok})
        rate_C = sum(1 for r in results if r["scenario"] == "C" and r["correct"]) / TRIALS
        logger.info(f"  all-reject escalates rate: {rate_C:.4f}")

        metrics = {
            "trials_per_scenario": TRIALS,
            "scenario_A_all_approve_completes": round(rate_A, 4),
            "scenario_B_mixed_plan_approved_completes": round(rate_B, 4),
            "scenario_C_all_reject_escalates": round(rate_C, 4),
            "all_correct": all_correct,
        }

        if all_correct:
            verdict, hyp = Verdict.PASS, True
            summary = "Multi-task HITL decisions handled correctly — approve completes, reject escalates, mixed plans work."
            observations = [
                "Two gated tasks, both approved → completed.",
                "Safe+gated plan with gated approved → completed.",
                "Two gated tasks, all rejected → escalated after max_replan_attempts.",
            ]
        else:
            verdict, hyp = Verdict.FAIL, False
            summary = "Partial HITL approval handling incorrect."
            observations = [f"A={rate_A} B={rate_B} C={rate_C}"]

        return ExperimentResult(verdict=verdict, summary=summary,
            hypothesis_supported=hyp, metrics=metrics,
            observations=observations, raw_outputs=results[:30])

    async def teardown(self): pass

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--findings-dir", default="findings")
    args = p.parse_args()
    exp = HIL_006(); result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}\nSummary : {result.summary}")
    for k, v in result.metrics.items(): print(f"  {k:<45} {v}")
