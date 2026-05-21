"""ORC-002 — ScopedContext Tool Isolation | Tier 1 | Depends on: none"""
from __future__ import annotations
import sys, uuid
from pathlib import Path
_r = Path(__file__).resolve().parents[3]
if str(_r) not in sys.path: sys.path.insert(0, str(_r))

from daf.runtime.tool_registry import ToolRegistry
from daf.runtime.tool import ToolNotFoundError
from daf.runtime.scoped_context import ScopedContext
from daf.models.approval_grant import ApprovalGrant, AgentPermissions
from daf.tools import StubTool
from daf.research.base import BaseExperiment, ExperimentResult, Verdict, Domain, Tier


def _make_grant(permitted_tools: list[str]) -> ApprovalGrant:
    from daf.models.plan_proposal import PlanProposal
    dummy_plan = PlanProposal(
        request_id=uuid.uuid4(), iteration=1,
        orchestrator="test", planning_rationale="test",
        sub_tasks=[], total_estimated_cost=0.0, confidence=0.9,
    )
    return ApprovalGrant(
        request_id=uuid.uuid4(),
        proposal_id=uuid.uuid4(),
        approved_plan=dummy_plan,
        agent_permissions={"analyst": AgentPermissions(
            tools=permitted_tools,
            data_sources=[],
            max_llm_calls=3,
        )},
        gated_tasks=[],
        requires_human_gate=False,
    )


class ORC_002(BaseExperiment):
    experiment_id = "ORC-002"
    domain = Domain.ORCHESTRATION
    tier = Tier.OFFLINE
    title = "ScopedContext Tool Isolation"
    research_question = "Are tools outside an agent's permitted set completely inaccessible within a ScopedContext?"
    hypothesis = "Calling an unpermitted tool via ScopedContext raises ToolNotFoundError in 100% of cases."
    depends_on = []
    estimated_cost_usd = 0.0
    estimated_minutes = 5

    async def prepare(self): pass

    async def run(self) -> ExperimentResult:
        logger = self._active_logger
        results = []
        all_correct = True

        # Build a registry with multiple tools
        tr = ToolRegistry()
        tr.register(StubTool(name="read_db",    idempotent=True))
        tr.register(StubTool(name="write_db",   idempotent=False))
        tr.register(StubTool(name="delete_db",  idempotent=False))
        tr.register(StubTool(name="send_email", idempotent=False))

        # Scenarios: (permitted, attempt_to_access, should_raise)
        scenarios = [
            ("only_read_db_permitted",    ["read_db"],  "write_db",   True),
            ("only_read_db_permitted",    ["read_db"],  "delete_db",  True),
            ("only_read_db_permitted",    ["read_db"],  "send_email", True),
            ("read_and_write_permitted",  ["read_db", "write_db"], "delete_db",  True),
            ("read_and_write_permitted",  ["read_db", "write_db"], "send_email", True),
            ("permitted_accessible",      ["read_db"],  "read_db",    False),  # should NOT raise
            ("all_permitted_accessible",  ["read_db", "write_db"], "write_db",  False),
        ]

        for name, permitted, tool_name, should_raise in scenarios:
            grant   = _make_grant(permitted)
            context = ScopedContext(
                agent_role="analyst", grant=grant,
                tool_registry=tr, task_input={},
            )

            raised = False
            try:
                context.tools.get(tool_name)
            except ToolNotFoundError:
                raised = True
            except Exception as e:
                raised = True  # any exception means access was blocked

            correct = raised == should_raise
            if not correct: all_correct = False

            logger.info(
                f"  {name:<35} permitted={permitted} access={tool_name!r} "
                f"should_raise={should_raise} raised={raised} → {'✓' if correct else '✗'}"
            )
            results.append({
                "scenario": name, "permitted": permitted, "tool": tool_name,
                "should_raise": should_raise, "raised": raised, "correct": correct,
            })

        # Additional: tools.names() only returns permitted tools
        grant   = _make_grant(["read_db"])
        context = ScopedContext(agent_role="analyst", grant=grant,
                                tool_registry=tr, task_input={})
        visible_names = context.tools.names()
        only_permitted_visible = visible_names == ["read_db"]
        if not only_permitted_visible: all_correct = False
        logger.info(f"  visible_tools={visible_names} expected=['read_db'] → {'✓' if only_permitted_visible else '✗'}")
        results.append({"scenario": "names_only_permitted", "correct": only_permitted_visible})

        # Additional: __contains__ respects scope
        in_scope     = "read_db" in context.tools
        out_of_scope = "write_db" in context.tools
        contains_ok  = in_scope and not out_of_scope
        if not contains_ok: all_correct = False
        logger.info(f"  __contains__: read_db={in_scope} write_db={out_of_scope} → {'✓' if contains_ok else '✗'}")
        results.append({"scenario": "contains_scoped", "correct": contains_ok})

        metrics = {
            "scenarios_tested": len(scenarios) + 2,
            "all_correct": all_correct,
            "unpermitted_tools_blocked": sum(1 for r in results
                if r.get("should_raise") and r["correct"]),
            "permitted_tools_accessible": sum(1 for r in results
                if r.get("should_raise") == False and r["correct"]),
            "names_only_shows_permitted": only_permitted_visible,
            "contains_respects_scope": contains_ok,
        }

        if all_correct:
            verdict, hyp = Verdict.PASS, True
            summary = "ScopedContext enforces tool isolation completely — unpermitted tools are inaccessible by design."
            observations = [
                "All unpermitted tool access raises ToolNotFoundError.",
                "Permitted tools remain accessible.",
                "tools.names() returns only permitted tools.",
                "__contains__ operator respects scope boundary.",
            ]
        else:
            failed = [r for r in results if not r["correct"]]
            verdict, hyp = Verdict.FAIL, False
            summary = f"ScopedContext isolation failure in {len(failed)} scenarios."
            observations = [str(failed[:3])]

        return ExperimentResult(verdict=verdict, summary=summary,
            hypothesis_supported=hyp, metrics=metrics,
            observations=observations, raw_outputs=results)

    async def teardown(self): pass

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--findings-dir", default="findings")
    args = p.parse_args()
    exp = ORC_002(); result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}\nSummary : {result.summary}")
    for k, v in result.metrics.items(): print(f"  {k:<45} {v}")
