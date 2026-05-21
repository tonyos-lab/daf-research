"""
SEC-003 — Budget Bypass Resistance
Tier: 1 | Depends on: none
"""
from __future__ import annotations
import sys, uuid
from pathlib import Path
_r = Path(__file__).resolve().parents[3]
if str(_r) not in sys.path: sys.path.insert(0, str(_r))

from daf.components.policy_engine import PolicyEngine
from daf.models.plan_proposal import PlanProposal, SubTask
from daf.models.policy_matrix import (
    PolicyMatrix, AgentRoleConfig, BudgetPolicyConfig,
    LoopPolicyConfig, RiskPolicyConfig,
)
from daf.research.base import BaseExperiment, ExperimentResult, Verdict, Domain, Tier

WORKFLOW_LIMIT = 0.50
STEP_LIMIT     = 0.10

def _matrix(workflow_limit=WORKFLOW_LIMIT, step_limit=STEP_LIMIT):
    return PolicyMatrix(
        version="1.0.0", tenant_id="test", effective="2026-01-01T00:00:00Z",
        agent_roles={"analyst": AgentRoleConfig(
            permitted_tools=["read_db"], permitted_data_sources=["internal"],
            permitted_task_types=["llm_extraction"],
        )},
        budget_policy=BudgetPolicyConfig(
            max_cost_per_step_usd=step_limit,
            max_cost_per_workflow_usd=workflow_limit,
        ),
        loop_policy=LoopPolicyConfig(max_replan_attempts=3),
        risk_policy=RiskPolicyConfig(irreversible_min_confidence=0.90),
        compliance_rules=[],
    )

def _engine(matrix):
    e = PolicyEngine.__new__(PolicyEngine)
    e._policy_matrix_path = None; e._cached_matrix = matrix
    return e

def _proposal(workflow_cost, step_cost=None, confidence=0.95):
    sc = step_cost if step_cost is not None else workflow_cost
    return PlanProposal(
        request_id=uuid.uuid4(), iteration=1,
        orchestrator="test", planning_rationale="test",
        sub_tasks=[SubTask(
            task_id="ST-01", task_type="llm_extraction",
            agent_required="analyst", tools_required=["read_db"],
            data_required=["internal"], estimated_cost=sc,
            reversible=True, rationale="test",
        )],
        total_estimated_cost=workflow_cost, confidence=confidence,
    )

class SEC_003(BaseExperiment):
    experiment_id = "SEC-003"
    domain = Domain.SECURITY
    tier = Tier.OFFLINE
    title = "Budget Bypass Resistance"
    research_question = "Can a malformed plan bypass the budget enforcement in the PolicyEngine?"
    hypothesis = "No plan with estimated_cost_usd exceeding the PolicyMatrix budget limit can be approved, regardless of field manipulation."
    depends_on = []
    estimated_cost_usd = 0.0
    estimated_minutes = 3

    async def prepare(self): pass

    async def run(self) -> ExperimentResult:
        logger = self._active_logger
        matrix = _matrix()
        engine = _engine(matrix)
        results = []
        all_correct = True

        # Cases: (description, workflow_cost, step_cost, expected_verdict)
        cases = [
            ("under_workflow_and_step",  0.05,  0.05,  "APPROVED"),
            ("over_workflow_only",       0.99,  0.05,  "REJECTED"),
            ("over_step_only",           0.05,  0.99,  "REJECTED"),
            ("over_both",                0.99,  0.99,  "REJECTED"),
            ("exact_workflow_limit",     0.50,  0.05,  "APPROVED"),
            ("epsilon_over_workflow",    0.501, 0.05,  "REJECTED"),
            ("exact_step_limit",         0.05,  0.10,  "APPROVED"),
            ("epsilon_over_step",        0.05,  0.101, "REJECTED"),
            ("high_conf_over_budget",    0.99,  0.05,  "REJECTED"),  # confidence=1.0
            ("zero_cost",                0.0,   0.0,   "APPROVED"),
        ]

        for name, wf_cost, st_cost, expected in cases:
            conf = 1.0 if "high_conf" in name else 0.95
            result = engine.evaluate(_proposal(wf_cost, step_cost=st_cost, confidence=conf), matrix)
            correct = result.verdict == expected
            if not correct: all_correct = False
            logger.info(f"  {name:<35} wf={wf_cost} step={st_cost} → {result.verdict} (expected {expected}) {'✓' if correct else '✗'}")
            results.append({"case": name, "wf_cost": wf_cost, "step_cost": st_cost,
                            "verdict": result.verdict, "expected": expected, "correct": correct})

        passed = sum(1 for r in results if r["correct"])
        metrics = {
            "cases_tested": len(cases),
            "cases_passed": passed,
            "cases_failed": len(cases) - passed,
            "all_bypass_attempts_blocked": all_correct,
            "exact_limit_approved": next(r["correct"] for r in results if r["case"] == "exact_workflow_limit"),
            "epsilon_over_rejected": next(r["correct"] for r in results if r["case"] == "epsilon_over_workflow"),
        }

        if all_correct:
            verdict, hyp = Verdict.PASS, True
            summary = f"All {len(cases)} budget boundary cases enforced correctly — no bypass possible."
            observations = [
                "Exact limits approved; epsilon-over limits rejected.",
                "High confidence (1.0) cannot override budget enforcement.",
                "Both per-step and per-workflow limits enforced independently.",
            ]
        else:
            failed = [r["case"] for r in results if not r["correct"]]
            verdict, hyp = Verdict.FAIL, False
            summary = f"Budget bypass detected in cases: {failed}"
            observations = [f"Failed cases: {failed}"]

        return ExperimentResult(verdict=verdict, summary=summary,
            hypothesis_supported=hyp, metrics=metrics,
            observations=observations, raw_outputs=results)

    async def teardown(self): pass

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--findings-dir", default="findings")
    args = p.parse_args()
    exp = SEC_003(); result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}\nSummary : {result.summary}")
    for k, v in result.metrics.items(): print(f"  {k:<45} {v}")
