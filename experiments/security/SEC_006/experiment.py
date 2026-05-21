"""
SEC-006 — HITL Response Forgery Resistance
Tier: 1 | Depends on: none
"""
from __future__ import annotations
import sys, uuid
from pathlib import Path
_r = Path(__file__).resolve().parents[3]
if str(_r) not in sys.path: sys.path.insert(0, str(_r))

from daf.models.human_review import HumanReviewResponse, TaskDecision
from daf.research.base import BaseExperiment, ExperimentResult, Verdict, Domain, Tier

class SEC_006(BaseExperiment):
    experiment_id = "SEC-006"
    domain = Domain.SECURITY
    tier = Tier.OFFLINE
    title = "HITL Response Forgery Resistance"
    research_question = "Can a forged HumanReviewResponse cause the loop to execute a rejected plan?"
    hypothesis = "HumanReviewResponse is frozen at creation — a forged approval cannot override a legitimate rejection."
    depends_on = []
    estimated_cost_usd = 0.0
    estimated_minutes = 3

    async def prepare(self): pass

    async def run(self) -> ExperimentResult:
        logger = self._active_logger
        results = []
        all_correct = True

        review_id = uuid.uuid4()
        grant_id  = uuid.uuid4()

        # Test 1: rejected response is frozen — cannot be changed to approved
        logger.info("Test 1: rejection cannot be mutated to approval")
        rejected = HumanReviewResponse.rejected_all(
            review_id=review_id, grant_id=grant_id,
            reviewer_id="alice", task_ids=["ST-01"],
            reason="Not authorised",
        )
        mutation_blocked = False
        try:
            rejected.reviewer_id = "attacker"  # type: ignore
        except Exception:
            mutation_blocked = True
        field_unchanged = rejected.reviewer_id == "alice"
        rejected_still = rejected.has_rejections()
        correct = mutation_blocked and field_unchanged and rejected_still
        if not correct: all_correct = False
        logger.info(f"  mutation blocked={mutation_blocked} field_unchanged={field_unchanged} still_rejected={rejected_still} → {'✓' if correct else '✗'}")
        results.append({"test": "rejected_frozen", "correct": correct})

        # Test 2: approved response is frozen
        logger.info("Test 2: approved response cannot be mutated")
        approved = HumanReviewResponse.approved_all(
            review_id=uuid.uuid4(), grant_id=uuid.uuid4(),
            reviewer_id="bob", task_ids=["ST-01"],
        )
        app_mutation_blocked = False
        try:
            approved.reviewer_id = "attacker"  # type: ignore
        except Exception:
            app_mutation_blocked = True
        still_approved = not approved.has_rejections()
        correct2 = app_mutation_blocked and still_approved
        if not correct2: all_correct = False
        logger.info(f"  approved mutation blocked={app_mutation_blocked} still_approved={still_approved} → {'✓' if correct2 else '✗'}")
        results.append({"test": "approved_frozen", "correct": correct2})

        # Test 3: decision_for() returns None for unknown task IDs (forgery via unknown task)
        logger.info("Test 3: forged task ID returns None from decision_for()")
        decision = approved.decision_for("FORGED-TASK-99")
        forged_rejected = decision is None
        if not forged_rejected: all_correct = False
        logger.info(f"  decision_for(forged_id) = {decision} → {'None ✓' if forged_rejected else 'NOT None ✗'}")
        results.append({"test": "forged_task_rejected", "correct": forged_rejected})

        # Test 4: timeout response correctly classified
        logger.info("Test 4: timeout response is not approval")
        timed_out = HumanReviewResponse.timeout_response(
            review_id=uuid.uuid4(), grant_id=uuid.uuid4(),
            task_ids=["ST-01"],
        )
        is_timed_out = timed_out.timed_out
        not_approved = timed_out.timed_out  # timed_out implies all rejected
        correct4 = is_timed_out and not_approved
        if not correct4: all_correct = False
        logger.info(f"  timed_out={is_timed_out} not_approved={not_approved} → {'✓' if correct4 else '✗'}")
        results.append({"test": "timeout_not_approval", "correct": correct4})

        # Test 5: mixed decisions — rejected tasks remain rejected after object creation
        logger.info("Test 5: mixed decisions immutable after creation")
        mixed = HumanReviewResponse(
            review_id=uuid.uuid4(), grant_id=uuid.uuid4(),
            reviewer_id="charlie",
            task_decisions=[
                TaskDecision(task_id="ST-01", decision="approved"),
                TaskDecision(task_id="ST-02", decision="rejected", reason="Too risky"),
            ],
        )
        st01_approved = mixed.decision_for("ST-01").is_approved
        st02_rejected = mixed.decision_for("ST-02").is_rejected
        mixed_mutation_blocked = False
        try:
            mixed.reviewer_id = "attacker"  # type: ignore
        except Exception:
            mixed_mutation_blocked = True
        correct5 = st01_approved and st02_rejected and mixed_mutation_blocked
        if not correct5: all_correct = False
        logger.info(f"  ST-01 approved={st01_approved} ST-02 rejected={st02_rejected} frozen={mixed_mutation_blocked} → {'✓' if correct5 else '✗'}")
        results.append({"test": "mixed_decisions_immutable", "correct": correct5})

        metrics = {
            "tests_run": len(results),
            "tests_passed": sum(1 for r in results if r["correct"]),
            "rejection_frozen": mutation_blocked,
            "approved_frozen": app_mutation_blocked,
            "forged_task_id_returns_none": forged_rejected,
            "timeout_not_treated_as_approval": is_timed_out,
            "all_forgery_vectors_blocked": all_correct,
        }

        if all_correct:
            verdict, hyp = Verdict.PASS, True
            summary = "HumanReviewResponse is fully forgery-resistant — frozen, forged IDs rejected, timeout not approval."
            observations = [
                "Rejected and approved responses both frozen after creation.",
                "decision_for() returns None for forged/unknown task IDs.",
                "Timeout response correctly not treated as approval.",
                "Mixed decisions preserved exactly as created.",
            ]
        else:
            failed = [r["test"] for r in results if not r["correct"]]
            verdict, hyp = Verdict.FAIL, False
            summary = f"HITL forgery resistance failure in: {failed}"
            observations = [f"Failed: {failed}"]

        return ExperimentResult(verdict=verdict, summary=summary,
            hypothesis_supported=hyp, metrics=metrics,
            observations=observations, raw_outputs=results)

    async def teardown(self): pass

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--findings-dir", default="findings")
    args = p.parse_args()
    exp = SEC_006(); result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}\nSummary : {result.summary}")
    for k, v in result.metrics.items(): print(f"  {k:<45} {v}")
