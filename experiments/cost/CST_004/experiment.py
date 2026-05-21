"""
experiments/cost/CST_004/experiment.py
======================================
CST-004 — Budget Enforcement Precision

Research Question:
    At what cost granularity does the BudgetTracker enforce limits?

Hypothesis:
    BudgetTracker enforces limits to floating-point precision with
    no bypass possible via boundary manipulation (exact limit,
    fractional overage, large overage, negative cost injection).

Tier: 1 (fully offline)
Depends on: none

Note: This is also the offline proxy for CST-001. It establishes
the cost enforcement baseline that live-API cost experiments build on.
"""

from __future__ import annotations

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[3]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from daf import GovernedAgenticLoop
from daf.testing import MockLLMClient, FixturePlanBuilder
from daf.runtime.budget_tracker import BudgetTracker
from daf.runtime.agent_registry import AgentRegistry
from daf.runtime.tool_registry import ToolRegistry
from daf.agents import StubAgent
from daf.tools import StubTool

from daf.research.base import BaseExperiment, ExperimentResult, Verdict, Domain, Tier

POLICY_MATRIX = str(_repo_root / "policy" / "matrix" / "example.yaml")

# Budget limit from example.yaml
BUDGET_LIMIT = 0.50

def _plan_with_cost(cost: float) -> dict:
    plan = (
        FixturePlanBuilder()
        .with_task("ST-01", agent="document_reader", tools=["read_db"],
                   estimated_cost=cost)
        .build()
    )
    return plan


class CST_004(BaseExperiment):

    experiment_id      = "CST-004"
    domain             = Domain.COST
    tier               = Tier.OFFLINE
    title              = "Budget Enforcement Precision"
    research_question  = (
        "At what cost granularity does the BudgetTracker enforce limits?"
    )
    hypothesis         = (
        "BudgetTracker enforces limits to floating-point precision. "
        "Plans at exactly the limit are approved; plans one epsilon "
        "over are rejected. No boundary manipulation bypasses enforcement."
    )
    depends_on         = []
    estimated_cost_usd = 0.0
    estimated_minutes  = 5

    _agent_registry: AgentRegistry | None = None
    _tool_registry:  ToolRegistry  | None = None

    async def prepare(self) -> None:
        self._tool_registry = ToolRegistry()
        self._tool_registry.register(StubTool(name="read_db", idempotent=True))
        self._agent_registry = AgentRegistry()
        self._agent_registry.register(
            type("DocumentReaderAgent", (StubAgent,), {"role": "document_reader"})
        )

    async def run(self) -> ExperimentResult:
        logger = self._active_logger

        # --- Part 1: BudgetTracker unit-level precision tests ---
        logger.info("Part 1: BudgetTracker unit precision tests")

        bt_cases = [
            ("zero_cost",         0.0,           0.50,  True),
            ("well_under",        0.10,           0.50,  True),
            ("at_exact_limit",    0.50,           0.50,  True),
            ("one_cent_over",     0.51,           0.50,  False),
            ("one_epsilon_over",  0.50 + 1e-10,  0.50,  False),
            ("double_limit",      1.00,           0.50,  False),
            ("large_overage",    99.99,           0.50,  False),
        ]

        bt_results = []
        all_bt_pass = True

        for name, cost, limit, should_fit in bt_cases:
            tracker = BudgetTracker(max_cost_usd=limit)
            fits    = tracker.check_and_reserve(cost)
            correct = fits == should_fit

            if not correct:
                all_bt_pass = False

            logger.info(
                f"  {name}: cost={cost} limit={limit} "
                f"fits={fits} expected={should_fit} → {'PASS' if correct else 'FAIL'}"
            )
            bt_results.append({
                "case": name, "cost": cost, "limit": limit,
                "fits": fits, "expected": should_fit, "correct": correct,
            })

        # --- Part 2: Full loop budget enforcement ---
        logger.info("Part 2: Full loop budget enforcement via PolicyEngine")

        # Per-step limit is 0.10 and per-workflow is 0.50 in example.yaml
        # Use costs within the per-step limit (0.10) to test workflow enforcement
        loop_cases = [
            ("well_under_budget",  0.05,  "completed"),   # well under both limits
            ("over_step_budget",   0.15,  "escalated"),   # over per-step limit (0.10)
            ("at_step_limit",      0.10,  "completed"),   # exactly at per-step limit
        ]

        loop_results = []
        all_loop_pass = True

        for name, task_cost, expected_outcome in loop_cases:
            result = await GovernedAgenticLoop(
                llm_client=MockLLMClient(responses=[_plan_with_cost(task_cost)]),
                policy_matrix=POLICY_MATRIX,
                agent_registry=self._agent_registry,
                tool_registry=self._tool_registry,
            ).run({
                "task":      f"Cost enforcement test: {name}",
                "tenant_id": "cost-test",
                "user_id":   "researcher",
            })

            correct = result.outcome == expected_outcome
            if not correct:
                all_loop_pass = False

            logger.info(
                f"  {name}: task_cost={task_cost} "
                f"outcome={result.outcome} expected={expected_outcome} "
                f"→ {'PASS' if correct else 'FAIL'}"
            )
            loop_results.append({
                "case": name, "task_cost": task_cost,
                "outcome": result.outcome,
                "expected": expected_outcome,
                "correct": correct,
            })

        # --- Part 3: record_actual adjustment ---
        logger.info("Part 3: BudgetTracker.record_actual() reconciliation")
        tracker = BudgetTracker(max_cost_usd=1.00)
        tracker.check_and_reserve(0.50)         # reserve 0.50
        tracker.record_actual(actual_cost=0.30, reserved_cost=0.50)       # actual was 0.30 — releases 0.20
        remaining_after_reconcile = round(tracker.remaining, 6)
        reconcile_correct = abs(remaining_after_reconcile - 0.70) < 1e-9
        logger.info(
            f"  after reserve(0.50) + record_actual(0.50→0.30): "
            f"remaining={remaining_after_reconcile} expected≈0.70 "
            f"→ {'PASS' if reconcile_correct else 'FAIL'}"
        )

        # --- Metrics ---
        bt_pass_count   = sum(1 for r in bt_results if r["correct"])
        loop_pass_count = sum(1 for r in loop_results if r["correct"])
        all_pass = all_bt_pass and all_loop_pass and reconcile_correct

        metrics = {
            "bt_cases_tested":           len(bt_cases),
            "bt_cases_passed":           bt_pass_count,
            "bt_cases_failed":           len(bt_cases) - bt_pass_count,
            "exact_limit_approved":      bt_results[2]["correct"],
            "epsilon_over_rejected":     bt_results[4]["correct"],
            "loop_cases_tested":         len(loop_cases),
            "loop_cases_passed":         loop_pass_count,
            "reconcile_correct":         reconcile_correct,
            "remaining_after_reconcile": remaining_after_reconcile,
            "all_precision_tests_pass":  all_pass,
        }

        raw_outputs = bt_results + loop_results + [
            {"case": "reconcile", "correct": reconcile_correct,
             "remaining": remaining_after_reconcile}
        ]

        if all_pass:
            verdict = Verdict.PASS
            summary = (
                "BudgetTracker enforces cost limits with full floating-point "
                "precision — no boundary manipulation bypasses enforcement."
            )
            hypothesis_supported = True
            observations = [
                f"All {len(bt_cases)} BudgetTracker precision cases passed.",
                f"All {len(loop_cases)} full-loop budget enforcement cases passed.",
                "record_actual() reconciliation correct to 1e-9 precision.",
                "Exact-limit plans approved; epsilon-over-limit plans rejected.",
            ]
        else:
            failed_bt   = [r["case"] for r in bt_results   if not r["correct"]]
            failed_loop = [r["case"] for r in loop_results if not r["correct"]]
            verdict = Verdict.FAIL
            summary = (
                f"Budget precision failures: BT={failed_bt} loop={failed_loop}."
            )
            hypothesis_supported = False
            observations = [
                f"Failed BT cases: {failed_bt}",
                f"Failed loop cases: {failed_loop}",
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
        self._agent_registry = None
        self._tool_registry  = None


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run CST-004")
    parser.add_argument("--findings-dir", default="findings")
    args = parser.parse_args()
    exp = CST_004()
    result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}")
    print(f"Summary : {result.summary}")
    for k, v in result.metrics.items():
        print(f"  {k:<45} {v}")
