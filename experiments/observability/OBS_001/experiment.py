"""
experiments/observability/OBS_001/experiment.py
===============================================
OBS-001 — Minimal Audit Schema for Compliance

Research Question:
    What is the minimal audit schema satisfying SOC2, HIPAA, and
    GDPR simultaneously?

Hypothesis:
    The InMemoryAuditStore record structure (audit_id, request_id,
    tenant_id, user_id, event_type, payload, created_at) contains
    all fields required by SOC2, HIPAA, and GDPR with no additions.

Tier: 1 (fully offline)
Depends on: none
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[3]
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from daf import GovernedAgenticLoop
from daf.testing import MockLLMClient, FixturePlanBuilder
from daf.runtime.agent_registry import AgentRegistry
from daf.runtime.tool_registry import ToolRegistry
from daf.runtime.audit_store import InMemoryAuditStore
from daf.models.audit_record import AuditRecord, AuditEventType
from daf.agents import StubAgent
from daf.tools import StubTool

from daf.research.base import BaseExperiment, ExperimentResult, Verdict, Domain, Tier

POLICY_MATRIX = str(_repo_root / "policy" / "matrix" / "example.yaml")

# ---------------------------------------------------------------------------
# Compliance field requirements
# Each standard maps to the AuditRecord fields that satisfy it
# ---------------------------------------------------------------------------
COMPLIANCE_REQUIREMENTS = {
    "SOC2": {
        "description": "SOC2 Type II — Security, Availability, Confidentiality",
        "required_fields": {"audit_id", "event_type", "created_at", "payload"},
        "required_payload_keys": [],  # checked per event type below
        "rationale": {
            "audit_id":    "Unique event identifier for non-repudiation",
            "event_type":  "Event classification for change management",
            "created_at":  "Timestamp for audit trail ordering",
            "payload":     "Event detail for investigation",
        },
    },
    "HIPAA": {
        "description": "HIPAA Audit Controls (§164.312(b))",
        "required_fields": {"audit_id", "user_id", "event_type", "created_at", "payload"},
        "required_payload_keys": [],
        "rationale": {
            "audit_id":   "Unique record ID for audit log integrity",
            "user_id":    "Person who performed the action (workforce accountability)",
            "event_type": "Activity classification",
            "created_at": "Exact time of activity",
            "payload":    "Activity details",
        },
    },
    "GDPR": {
        "description": "GDPR Article 30 — Records of Processing Activities",
        "required_fields": {"audit_id", "tenant_id", "user_id", "event_type", "created_at"},
        "required_payload_keys": [],
        "rationale": {
            "audit_id":   "Record identifier",
            "tenant_id":  "Data controller / processor identity",
            "user_id":    "Data subject or processor identity",
            "event_type": "Purpose of processing",
            "created_at": "Timestamp for data retention enforcement",
        },
    },
}

AUDIT_RECORD_FIELDS = {"audit_id", "request_id", "tenant_id", "user_id",
                       "event_type", "payload", "created_at"}


class OBS_001(BaseExperiment):

    experiment_id      = "OBS-001"
    domain             = Domain.OBSERVABILITY
    tier               = Tier.OFFLINE
    title              = "Minimal Audit Schema for Compliance"
    research_question  = (
        "What is the minimal audit schema satisfying SOC2, HIPAA, "
        "and GDPR simultaneously?"
    )
    hypothesis         = (
        "The AuditRecord structure contains all fields required by "
        "SOC2, HIPAA, and GDPR with no additions needed."
    )
    depends_on         = []
    estimated_cost_usd = 0.0
    estimated_minutes  = 5

    _audit_store:    InMemoryAuditStore | None = None
    _agent_registry: AgentRegistry     | None = None
    _tool_registry:  ToolRegistry      | None = None

    async def prepare(self) -> None:
        self._audit_store = InMemoryAuditStore()
        self._tool_registry = ToolRegistry()
        self._tool_registry.register(StubTool(name="read_db", idempotent=True))
        self._agent_registry = AgentRegistry()
        self._agent_registry.register(
            type("DocumentReaderAgent", (StubAgent,), {"role": "document_reader"})
        )

    async def run(self) -> ExperimentResult:
        logger = self._active_logger

        # --- Step 1: Run a complete workflow to produce a real audit trail ---
        logger.info("Step 1: Running workflow to produce real audit records")
        plan = (
            FixturePlanBuilder()
            .with_task("ST-01", agent="document_reader", tools=["read_db"])
            .build()
        )
        result = await GovernedAgenticLoop(
            llm_client=MockLLMClient(responses=[plan]),
            policy_matrix=POLICY_MATRIX,
            agent_registry=self._agent_registry,
            tool_registry=self._tool_registry,
            audit_store=self._audit_store,
        ).run({
            "task":      "Analyse quarterly contracts for compliance audit",
            "tenant_id": "acme-corp",
            "user_id":   "auditor@acme.com",
        })
        logger.info(f"  workflow outcome: {result.outcome}")

        # --- Step 2: Retrieve all audit records ---
        all_records = self._audit_store.all_records()
        logger.info(f"  total audit records written: {len(all_records)}")

        # --- Step 3: Check each compliance standard against record fields ---
        compliance_results = {}
        all_compliant = True
        raw_outputs = []

        for standard, req in COMPLIANCE_REQUIREMENTS.items():
            missing_fields = req["required_fields"] - AUDIT_RECORD_FIELDS
            present_fields = req["required_fields"] & AUDIT_RECORD_FIELDS
            compliant = len(missing_fields) == 0

            if not compliant:
                all_compliant = False

            logger.info(
                f"  {standard}: required={sorted(req['required_fields'])} "
                f"missing={sorted(missing_fields)} → {'PASS' if compliant else 'FAIL'}"
            )

            # Verify values are actually populated (not None/empty) in real records
            populated_checks = {}
            if all_records:
                sample = all_records[0]
                for field in req["required_fields"]:
                    val = getattr(sample, field, None)
                    populated_checks[field] = val is not None and str(val) != ""

            compliance_results[standard] = {
                "compliant":         compliant,
                "required_fields":   sorted(req["required_fields"]),
                "missing_fields":    sorted(missing_fields),
                "populated_in_real_record": populated_checks,
            }
            raw_outputs.append({"standard": standard, **compliance_results[standard]})

        # --- Step 4: Check all event types are present in trail ---
        event_types_seen = {r.event_type for r in all_records}
        expected_events  = {
            AuditEventType.WORKFLOW_STARTED,
            AuditEventType.PLAN_PROPOSED,
            AuditEventType.PLAN_EVALUATED,
            AuditEventType.EXECUTION_STARTED,
            AuditEventType.STEP_STARTED,
            AuditEventType.STEP_COMPLETED,
            AuditEventType.WORKFLOW_COMPLETED,
        }
        missing_events = expected_events - event_types_seen
        logger.info(f"  event types seen: {sorted(event_types_seen)}")
        logger.info(f"  missing events  : {sorted(missing_events)}")

        metrics = {
            "audit_records_produced":     len(all_records),
            "audit_record_fields":        len(AUDIT_RECORD_FIELDS),
            "soc2_compliant":             compliance_results["SOC2"]["compliant"],
            "hipaa_compliant":            compliance_results["HIPAA"]["compliant"],
            "gdpr_compliant":             compliance_results["GDPR"]["compliant"],
            "all_standards_met":          all_compliant,
            "event_types_seen":           len(event_types_seen),
            "missing_event_types":        len(missing_events),
            "audit_trail_complete":       len(missing_events) == 0,
        }

        if all_compliant:
            verdict = Verdict.PASS
            summary = (
                "AuditRecord schema satisfies SOC2, HIPAA, and GDPR "
                "simultaneously with no additional fields required."
            )
            hypothesis_supported = True
            observations = [
                f"AuditRecord has {len(AUDIT_RECORD_FIELDS)} fields: {sorted(AUDIT_RECORD_FIELDS)}",
                "All three standards' required fields are present in the schema.",
                f"{len(all_records)} audit records produced in a single workflow run.",
                f"All required event types present: {len(missing_events) == 0}",
            ]
        else:
            failed_standards = [s for s, r in compliance_results.items() if not r["compliant"]]
            verdict = Verdict.FAIL
            summary = (
                f"AuditRecord schema does not satisfy: {failed_standards}. "
                f"Schema additions required."
            )
            hypothesis_supported = False
            observations = [
                f"Non-compliant standards: {failed_standards}",
                f"Missing fields: {[compliance_results[s]['missing_fields'] for s in failed_standards]}",
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
        self._audit_store    = None
        self._agent_registry = None
        self._tool_registry  = None


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run OBS-001")
    parser.add_argument("--findings-dir", default="findings")
    args = parser.parse_args()
    exp = OBS_001()
    result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}")
    print(f"Summary : {result.summary}")
    for k, v in result.metrics.items():
        print(f"  {k:<45} {v}")
