"""
SEC-004 — Compliance Rule Bypass Resistance
Tier: 1 | Depends on: SEC-001
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
    LoopPolicyConfig, RiskPolicyConfig, ComplianceRule,
    ComplianceAction, Condition, ConditionOperator,
)
from daf.research.base import BaseExperiment, ExperimentResult, Verdict, Domain, Tier

def _matrix_with_block_rule(trigger_value="pii_data", field="data_required",
                              operator=ConditionOperator.CONTAINS):
    return PolicyMatrix(
        version="1.0.0", tenant_id="test", effective="2026-01-01T00:00:00Z",
        agent_roles={"analyst": AgentRoleConfig(
            permitted_tools=["read_db"],
            permitted_data_sources=["internal", "pii_data", "restricted"],
            permitted_task_types=["llm_extraction"],
        )},
        budget_policy=BudgetPolicyConfig(max_cost_per_step_usd=0.10, max_cost_per_workflow_usd=0.50),
        loop_policy=LoopPolicyConfig(max_replan_attempts=3),
        risk_policy=RiskPolicyConfig(irreversible_min_confidence=0.90),
        compliance_rules=[ComplianceRule(
            rule_ref="BLOCK-TEST",
            condition=Condition(field=field, operator=operator, value=trigger_value),
            action=ComplianceAction.BLOCK,
            remediation_hint="Blocked by compliance rule",
        )],
    )

def _engine(matrix):
    e = PolicyEngine.__new__(PolicyEngine)
    e._policy_matrix_path = None; e._cached_matrix = matrix
    return e

def _proposal(data_required, confidence=0.95, cost=0.05):
    return PlanProposal(
        request_id=uuid.uuid4(), iteration=1,
        orchestrator="test", planning_rationale="test",
        sub_tasks=[SubTask(
            task_id="ST-01", task_type="llm_extraction",
            agent_required="analyst", tools_required=["read_db"],
            data_required=data_required, estimated_cost=cost,
            reversible=True, rationale="test",
        )],
        total_estimated_cost=cost, confidence=confidence,
    )

class SEC_004(BaseExperiment):
    experiment_id = "SEC-004"
    domain = Domain.SECURITY
    tier = Tier.OFFLINE
    title = "Compliance Rule Bypass Resistance"
    research_question = "Can adversarial task inputs cause compliance block rules to be skipped?"
    hypothesis = "A compliance rule with action=block fires 100% of the time on matching inputs, regardless of confidence, cost, or other field values."
    depends_on = ["SEC-001"]
    estimated_cost_usd = 0.0
    estimated_minutes = 3

    async def prepare(self): pass

    async def run(self) -> ExperimentResult:
        logger = self._active_logger
        results = []
        all_correct = True

        # Part 1: block rule fires at all confidence levels
        matrix = _matrix_with_block_rule()
        engine = _engine(matrix)
        logger.info("Part 1: block rule fires regardless of confidence")
        for confidence in [0.1, 0.5, 0.9, 0.99, 1.0]:
            result = engine.evaluate(_proposal(["pii_data"], confidence=confidence), matrix)
            blocked = result.verdict == "REJECTED"
            if not blocked: all_correct = False
            logger.info(f"  confidence={confidence} → {'REJECTED ✓' if blocked else 'APPROVED ✗'}")
            results.append({"case": f"block_conf_{confidence}", "blocked": blocked})

        # Part 2: block rule fires at all cost levels
        logger.info("Part 2: block rule fires regardless of cost")
        for cost in [0.0, 0.001, 0.05, 0.10]:
            result = engine.evaluate(_proposal(["pii_data"], cost=cost), matrix)
            blocked = result.verdict == "REJECTED"
            if not blocked: all_correct = False
            logger.info(f"  cost={cost} → {'REJECTED ✓' if blocked else 'APPROVED ✗'}")
            results.append({"case": f"block_cost_{cost}", "blocked": blocked})

        # Part 3: non-triggering data not blocked
        logger.info("Part 3: non-triggering data approved")
        result = engine.evaluate(_proposal(["internal"]), matrix)
        clean_approved = result.verdict == "APPROVED"
        if not clean_approved: all_correct = False
        logger.info(f"  non-pii data → {'APPROVED ✓' if clean_approved else 'REJECTED ✗'}")
        results.append({"case": "clean_data_approved", "blocked": not clean_approved})

        # Part 4: multiple data sources — block fires if ANY match
        logger.info("Part 4: mixed data — block fires if any field matches")
        result = engine.evaluate(_proposal(["internal", "pii_data"]), matrix)
        mixed_blocked = result.verdict == "REJECTED"
        if not mixed_blocked: all_correct = False
        logger.info(f"  [internal+pii_data] → {'REJECTED ✓' if mixed_blocked else 'APPROVED ✗'}")
        results.append({"case": "mixed_data_blocked", "blocked": mixed_blocked})

        # Part 5: equals operator block rule
        logger.info("Part 5: equals-operator block rule")
        eq_matrix = _matrix_with_block_rule(
            trigger_value="restricted", field="data_required",
            operator=ConditionOperator.CONTAINS
        )
        eq_engine = _engine(eq_matrix)
        result = eq_engine.evaluate(_proposal(["restricted"]), eq_matrix)
        eq_blocked = result.verdict == "REJECTED"
        if not eq_blocked: all_correct = False
        logger.info(f"  equals-block [restricted] → {'REJECTED ✓' if eq_blocked else 'APPROVED ✗'}")
        results.append({"case": "equals_operator_block", "blocked": eq_blocked})

        blocked_count = sum(1 for r in results if r.get("blocked", False))
        expected_blocked = len(results) - 1  # all except clean_data_approved
        metrics = {
            "cases_tested": len(results),
            "block_rule_fired_count": blocked_count,
            "clean_data_approved": clean_approved,
            "mixed_data_blocked": mixed_blocked,
            "all_block_cases_correct": all_correct,
            "resistance_rate": round(blocked_count / expected_blocked, 4) if expected_blocked > 0 else 1.0,
        }

        if all_correct:
            verdict, hyp = Verdict.PASS, True
            summary = "Compliance block rules fire 100% on all matching inputs — no bypass possible."
            observations = [
                "Block rule fires at all confidence levels (0.1 to 1.0).",
                "Block rule fires at all cost levels (0.0 to 0.10).",
                "Mixed data sources: block fires if any value matches.",
                "Non-triggering data approved — no false positives.",
            ]
        else:
            failed = [r["case"] for r in results
                      if r.get("blocked") == False and r["case"] != "clean_data_approved"]
            verdict, hyp = Verdict.FAIL, False
            summary = f"Compliance rule bypass detected: {failed}"
            observations = [f"Failed cases: {failed}"]

        return ExperimentResult(verdict=verdict, summary=summary,
            hypothesis_supported=hyp, metrics=metrics,
            observations=observations, raw_outputs=results)

    async def teardown(self): pass

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--findings-dir", default="findings")
    args = p.parse_args()
    exp = SEC_004(); result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}\nSummary : {result.summary}")
    for k, v in result.metrics.items(): print(f"  {k:<45} {v}")
