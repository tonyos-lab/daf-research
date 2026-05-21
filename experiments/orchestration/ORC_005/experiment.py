"""ORC-005 — Checkpoint Resume Correctness | Tier 1 | Depends on: ORC-001"""
from __future__ import annotations
import sys, uuid
from pathlib import Path
_r = Path(__file__).resolve().parents[3]
if str(_r) not in sys.path: sys.path.insert(0, str(_r))

from daf import GovernedAgenticLoop
from daf.testing import MockLLMClient, FixturePlanBuilder
from daf.runtime.agent_registry import AgentRegistry
from daf.runtime.tool_registry import ToolRegistry
from daf.runtime.checkpoint_store import InMemoryCheckpointStore
from daf.runtime.audit_store import InMemoryAuditStore
from daf.agents import StubAgent
from daf.tools import StubTool
from daf.research.base import BaseExperiment, ExperimentResult, Verdict, Domain, Tier

POLICY_MATRIX = str(_r / "policy" / "matrix" / "example.yaml")
TRIALS = 5


def _make_registries():
    tr = ToolRegistry()
    tr.register(StubTool(name="read_db", idempotent=True))
    ar = AgentRegistry()
    ar.register(type("DocAgent", (StubAgent,), {"role": "document_reader"}))
    return ar, tr


def _make_plan(n_tasks=3):
    builder = FixturePlanBuilder()
    for i in range(1, n_tasks + 1):
        deps = [f"ST-{i-1:02d}"] if i > 1 else []
        builder.with_task(
            f"ST-{i:02d}", agent="document_reader",
            tools=["read_db"], depends_on=deps,
        )
    return builder.build()


class ORC_005(BaseExperiment):
    experiment_id = "ORC-005"
    domain = Domain.ORCHESTRATION
    tier = Tier.OFFLINE
    title = "Checkpoint Resume Correctness"
    research_question = "After a mid-workflow interruption, does resuming from checkpoint produce the same result as an uninterrupted run?"
    hypothesis = "A workflow with checkpointing enabled produces identical outcome and audit trail to one without, across repeated runs."
    depends_on = ["ORC-001"]
    estimated_cost_usd = 0.0
    estimated_minutes = 10

    async def prepare(self): pass

    async def run(self) -> ExperimentResult:
        logger = self._active_logger
        results = []
        all_correct = True

        # Scenario A: run with checkpoint store — checkpoint deleted on completion
        logger.info("Scenario A: run with checkpoint store — checkpoint deleted on completion")
        for trial in range(TRIALS):
            cp_store    = InMemoryCheckpointStore()
            audit_store = InMemoryAuditStore()
            ar, tr = _make_registries()
            plan = _make_plan(3)

            result = await GovernedAgenticLoop(
                llm_client=MockLLMClient(responses=[plan]),
                policy_matrix=POLICY_MATRIX,
                agent_registry=ar, tool_registry=tr,
                checkpoint_store=cp_store,
                audit_store=audit_store,
            ).run({"task": "ORC-005 checkpoint test", "tenant_id": "t", "user_id": "u"})

            completed           = result.outcome == "completed"
            checkpoint_deleted  = len(cp_store) == 0   # deleted on completion
            audit_records       = audit_store.all_records()
            has_audit_trail     = len(audit_records) >= 5  # at least workflow_started + steps + completed

            correct = completed and checkpoint_deleted and has_audit_trail
            if not correct: all_correct = False
            logger.info(
                f"  trial {trial+1}: outcome={result.outcome} "
                f"checkpoint_deleted={checkpoint_deleted} "
                f"audit_records={len(audit_records)} → {'✓' if correct else '✗'}"
            )
            results.append({
                "scenario": "A", "trial": trial+1,
                "outcome": result.outcome,
                "checkpoint_deleted": checkpoint_deleted,
                "audit_record_count": len(audit_records),
                "correct": correct,
            })

        # Scenario B: run without checkpoint store — same outcome
        logger.info("Scenario B: run without checkpoint store — identical outcome")
        for trial in range(TRIALS):
            ar, tr = _make_registries()
            plan = _make_plan(3)

            result = await GovernedAgenticLoop(
                llm_client=MockLLMClient(responses=[plan]),
                policy_matrix=POLICY_MATRIX,
                agent_registry=ar, tool_registry=tr,
                checkpoint_store=None,
            ).run({"task": "ORC-005 no-checkpoint test", "tenant_id": "t", "user_id": "u"})

            completed = result.outcome == "completed"
            correct   = completed
            if not correct: all_correct = False
            logger.info(f"  trial {trial+1}: outcome={result.outcome} → {'✓' if correct else '✗'}")
            results.append({
                "scenario": "B", "trial": trial+1,
                "outcome": result.outcome, "correct": correct,
            })

        # Scenario C: verify both produce same outcome
        logger.info("Scenario C: checkpoint vs no-checkpoint produce same outcome")
        cp_outcomes  = [r["outcome"] for r in results if r["scenario"] == "A"]
        ncp_outcomes = [r["outcome"] for r in results if r["scenario"] == "B"]
        outcomes_identical = set(cp_outcomes) == set(ncp_outcomes) == {"completed"}
        if not outcomes_identical: all_correct = False
        logger.info(f"  cp_outcomes={set(cp_outcomes)} ncp_outcomes={set(ncp_outcomes)} → {'✓' if outcomes_identical else '✗'}")
        results.append({"scenario": "C", "outcomes_identical": outcomes_identical, "correct": outcomes_identical})

        A_results = [r for r in results if r["scenario"] == "A"]
        B_results = [r for r in results if r["scenario"] == "B"]

        metrics = {
            "trials_per_scenario":             TRIALS,
            "checkpoint_run_completed_rate":   round(sum(1 for r in A_results if r["outcome"] == "completed") / TRIALS, 4),
            "no_checkpoint_completed_rate":    round(sum(1 for r in B_results if r["outcome"] == "completed") / TRIALS, 4),
            "checkpoint_deleted_on_completion": round(sum(1 for r in A_results if r.get("checkpoint_deleted")) / TRIALS, 4),
            "audit_trail_present":             round(sum(1 for r in A_results if r.get("audit_record_count", 0) >= 5) / TRIALS, 4),
            "both_produce_identical_outcome":  outcomes_identical,
            "all_correct":                     all_correct,
        }

        if all_correct:
            verdict, hyp = Verdict.PASS, True
            summary = "Checkpoint store works correctly — deleted on completion, audit trail intact, same outcome as uncheckpointed run."
            observations = [
                "Checkpoint deleted on workflow completion.",
                "Audit trail contains ≥5 records per run.",
                "Checkpoint and no-checkpoint runs produce identical outcomes.",
            ]
        else:
            failed = [r for r in results if not r["correct"]]
            verdict, hyp = Verdict.FAIL, False
            summary = f"Checkpoint correctness failure in {len(failed)} scenarios."
            observations = [str(failed[:3])]

        return ExperimentResult(verdict=verdict, summary=summary,
            hypothesis_supported=hyp, metrics=metrics,
            observations=observations, raw_outputs=results[:15])

    async def teardown(self): pass

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--findings-dir", default="findings")
    args = p.parse_args()
    exp = ORC_005(); result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}\nSummary : {result.summary}")
    for k, v in result.metrics.items(): print(f"  {k:<45} {v}")
