"""OBS-002 — Audit Trail Completeness | Tier 1 | Depends on: OBS-001"""
from __future__ import annotations
import sys
from pathlib import Path
_r = Path(__file__).resolve().parents[3]
if str(_r) not in sys.path: sys.path.insert(0, str(_r))

from daf import GovernedAgenticLoop
from daf.testing import MockLLMClient, FixturePlanBuilder
from daf.runtime.agent_registry import AgentRegistry
from daf.runtime.tool_registry import ToolRegistry
from daf.runtime.audit_store import InMemoryAuditStore
from daf.models.audit_record import AuditEventType
from daf.agents import StubAgent
from daf.tools import StubTool
from daf.research.base import BaseExperiment, ExperimentResult, Verdict, Domain, Tier

POLICY_MATRIX = str(_r / "policy" / "matrix" / "example.yaml")


def _make_registries():
    tr = ToolRegistry()
    tr.register(StubTool(name="read_db", idempotent=True))
    ar = AgentRegistry()
    ar.register(type("DocAgent", (StubAgent,), {"role": "document_reader"}))
    return ar, tr


def _clean_plan(n_tasks=1):
    b = FixturePlanBuilder()
    for i in range(1, n_tasks + 1):
        deps = [f"ST-{i-1:02d}"] if i > 1 else []
        b.with_task(f"ST-{i:02d}", agent="document_reader",
                    tools=["read_db"], depends_on=deps)
    return b.build()


def _violating_plan():
    return (FixturePlanBuilder()
            .with_task("ST-01", agent="document_reader", tools=["forbidden"])
            .build())


class OBS_002(BaseExperiment):
    experiment_id      = "OBS-002"
    domain             = Domain.OBSERVABILITY
    tier               = Tier.OFFLINE
    title              = "Audit Trail Completeness"
    research_question  = "Does the audit trail capture every state transition in the Governed Agentic Loop?"
    hypothesis         = (
        "Every loop execution produces exactly the expected set of "
        "audit event types with no gaps — happy path, escalation, "
        "and HITL paths each produce distinct but complete trails."
    )
    depends_on         = ["OBS-001"]
    estimated_cost_usd = 0.0
    estimated_minutes  = 10

    async def prepare(self): pass

    async def run(self) -> ExperimentResult:
        logger = self._active_logger
        results = []
        all_correct = True

        # ── Scenario A: happy path (1 task) ─────────────────────────
        logger.info("Scenario A: happy path — 1 task")
        store = InMemoryAuditStore()
        ar, tr = _make_registries()
        result = await GovernedAgenticLoop(
            llm_client=MockLLMClient(responses=[_clean_plan(1)]),
            policy_matrix=POLICY_MATRIX,
            agent_registry=ar, tool_registry=tr,
            audit_store=store,
        ).run({"task": "OBS-002 happy", "tenant_id": "t", "user_id": "u"})

        events_A = [r.event_type for r in store.all_records()]
        expected_A = {
            AuditEventType.WORKFLOW_STARTED,
            AuditEventType.PLAN_PROPOSED,
            AuditEventType.PLAN_EVALUATED,
            AuditEventType.EXECUTION_STARTED,
            AuditEventType.STEP_STARTED,
            AuditEventType.STEP_COMPLETED,
            AuditEventType.WORKFLOW_COMPLETED,
        }
        missing_A = expected_A - set(events_A)
        A_ok = len(missing_A) == 0 and result.outcome == "completed"
        if not A_ok: all_correct = False
        logger.info(f"  events={events_A}")
        logger.info(f"  missing={missing_A} outcome={result.outcome} → {'✓' if A_ok else '✗'}")
        results.append({"scenario": "A", "events": events_A,
                        "missing": sorted(missing_A), "correct": A_ok})

        # ── Scenario B: happy path (3 tasks) ────────────────────────
        logger.info("Scenario B: happy path — 3 tasks")
        store = InMemoryAuditStore()
        ar, tr = _make_registries()
        result = await GovernedAgenticLoop(
            llm_client=MockLLMClient(responses=[_clean_plan(3)]),
            policy_matrix=POLICY_MATRIX,
            agent_registry=ar, tool_registry=tr,
            audit_store=store,
        ).run({"task": "OBS-002 3tasks", "tenant_id": "t", "user_id": "u"})

        events_B  = [r.event_type for r in store.all_records()]
        step_started   = events_B.count(AuditEventType.STEP_STARTED)
        step_completed = events_B.count(AuditEventType.STEP_COMPLETED)
        B_ok = (step_started == 3 and step_completed == 3
                and result.outcome == "completed")
        if not B_ok: all_correct = False
        logger.info(f"  step_started={step_started} step_completed={step_completed} → {'✓' if B_ok else '✗'}")
        results.append({"scenario": "B", "step_started": step_started,
                        "step_completed": step_completed, "correct": B_ok})

        # ── Scenario C: escalation path ─────────────────────────────
        logger.info("Scenario C: escalation — plan always violates")
        store = InMemoryAuditStore()
        ar, tr = _make_registries()
        result = await GovernedAgenticLoop(
            llm_client=MockLLMClient(responses=[_violating_plan()] * 10),
            policy_matrix=POLICY_MATRIX,
            agent_registry=ar, tool_registry=tr,
            audit_store=store,
        ).run({"task": "OBS-002 escalate", "tenant_id": "t", "user_id": "u"})

        events_C = [r.event_type for r in store.all_records()]
        has_started   = AuditEventType.WORKFLOW_STARTED   in events_C
        has_escalated = AuditEventType.WORKFLOW_ESCALATED in events_C
        has_rejected  = any(r.event_type == AuditEventType.PLAN_EVALUATED
                            and r.payload.get("verdict") == "REJECTED"
                            for r in store.all_records())
        C_ok = has_started and has_escalated and has_rejected and result.outcome == "escalated"
        if not C_ok: all_correct = False
        logger.info(f"  has_started={has_started} has_escalated={has_escalated} "
                    f"has_rejected={has_rejected} → {'✓' if C_ok else '✗'}")
        results.append({"scenario": "C", "has_started": has_started,
                        "has_escalated": has_escalated,
                        "has_rejected": has_rejected, "correct": C_ok})

        # ── Scenario D: ordering — WORKFLOW_COMPLETED is always last ─
        logger.info("Scenario D: WORKFLOW_COMPLETED is last event")
        store = InMemoryAuditStore()
        ar, tr = _make_registries()
        await GovernedAgenticLoop(
            llm_client=MockLLMClient(responses=[_clean_plan(2)]),
            policy_matrix=POLICY_MATRIX,
            agent_registry=ar, tool_registry=tr,
            audit_store=store,
        ).run({"task": "OBS-002 ordering", "tenant_id": "t", "user_id": "u"})

        all_recs = store.all_records()
        last_event = all_recs[-1].event_type if all_recs else None
        D_ok = last_event == AuditEventType.WORKFLOW_COMPLETED
        if not D_ok: all_correct = False
        logger.info(f"  last_event={last_event} → {'✓' if D_ok else '✗'}")
        results.append({"scenario": "D", "last_event": last_event, "correct": D_ok})

        # ── Scenario E: WORKFLOW_STARTED is always first ─────────────
        logger.info("Scenario E: WORKFLOW_STARTED is first event")
        first_event = all_recs[0].event_type if all_recs else None
        E_ok = first_event == AuditEventType.WORKFLOW_STARTED
        if not E_ok: all_correct = False
        logger.info(f"  first_event={first_event} → {'✓' if E_ok else '✗'}")
        results.append({"scenario": "E", "first_event": first_event, "correct": E_ok})

        metrics = {
            "scenarios_tested":              5,
            "all_correct":                   all_correct,
            "happy_path_1task_complete":     A_ok,
            "happy_path_3tasks_correct_counts": B_ok,
            "escalation_trail_complete":     C_ok,
            "workflow_completed_is_last":    D_ok,
            "workflow_started_is_first":     E_ok,
            "missing_events_scenario_A":     len(results[0]["missing"]),
        }

        if all_correct:
            verdict, hyp = Verdict.PASS, True
            summary = ("Audit trail is complete across all 5 scenarios — "
                       "every state transition is recorded in order.")
            observations = [
                "Happy path (1 task): all 7 required event types present.",
                "3-task plan: exactly 3 STEP_STARTED + 3 STEP_COMPLETED events.",
                "Escalation path: WORKFLOW_ESCALATED + PLAN_EVALUATED/REJECTED present.",
                "WORKFLOW_STARTED is always first; WORKFLOW_COMPLETED always last.",
            ]
        else:
            failed = [r["scenario"] for r in results if not r["correct"]]
            verdict, hyp = Verdict.FAIL, False
            summary = f"Audit trail gaps in scenarios: {failed}"
            observations = [str([r for r in results if not r["correct"]])]

        return ExperimentResult(verdict=verdict, summary=summary,
            hypothesis_supported=hyp, metrics=metrics,
            observations=observations, raw_outputs=results)

    async def teardown(self): pass

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--findings-dir", default="findings")
    args = p.parse_args()
    exp = OBS_002(); result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}\nSummary : {result.summary}")
    for k, v in result.metrics.items(): print(f"  {k:<45} {v}")
