"""OBS-003 — Audit Record Immutability | Tier 1 | Depends on: OBS-001"""
from __future__ import annotations
import sys, uuid
from pathlib import Path
_r = Path(__file__).resolve().parents[3]
if str(_r) not in sys.path: sys.path.insert(0, str(_r))

from daf.models.audit_record import AuditRecord, AuditEventType
from daf.runtime.audit_store import InMemoryAuditStore, AuditStoreError
from daf.research.base import BaseExperiment, ExperimentResult, Verdict, Domain, Tier


def _make_record(**kwargs):
    defaults = dict(
        request_id=uuid.uuid4(), tenant_id="acme",
        user_id="researcher", event_type=AuditEventType.WORKFLOW_STARTED,
        payload={"task": "test"},
    )
    defaults.update(kwargs)
    return AuditRecord.make(**defaults)


class OBS_003(BaseExperiment):
    experiment_id      = "OBS-003"
    domain             = Domain.OBSERVABILITY
    tier               = Tier.OFFLINE
    title              = "Audit Record Immutability"
    research_question  = "Can audit records be modified after they are written to the store?"
    hypothesis         = (
        "AuditRecord is frozen at creation — no field can be mutated, "
        "and the store rejects any attempt to overwrite an existing record."
    )
    depends_on         = ["OBS-001"]
    estimated_cost_usd = 0.0
    estimated_minutes  = 5

    async def prepare(self): pass

    async def run(self) -> ExperimentResult:
        logger = self._active_logger
        results = []
        all_correct = True

        # Test 1: cannot mutate event_type after creation
        logger.info("Test 1: event_type mutation blocked")
        rec = _make_record()
        blocked = False
        try:
            rec.event_type = "tampered"  # type: ignore
        except Exception:
            blocked = True
        correct = blocked and rec.event_type == AuditEventType.WORKFLOW_STARTED
        if not correct: all_correct = False
        logger.info(f"  blocked={blocked} value_unchanged={rec.event_type == AuditEventType.WORKFLOW_STARTED} → {'✓' if correct else '✗'}")
        results.append({"test": "event_type_frozen", "correct": correct})

        # Test 2: cannot mutate tenant_id
        logger.info("Test 2: tenant_id mutation blocked")
        rec2 = _make_record(tenant_id="legit-corp")
        blocked2 = False
        try:
            rec2.tenant_id = "attacker-corp"  # type: ignore
        except Exception:
            blocked2 = True
        correct2 = blocked2 and rec2.tenant_id == "legit-corp"
        if not correct2: all_correct = False
        logger.info(f"  blocked={blocked2} value_unchanged={rec2.tenant_id == 'legit-corp'} → {'✓' if correct2 else '✗'}")
        results.append({"test": "tenant_id_frozen", "correct": correct2})

        # Test 3: cannot mutate user_id
        logger.info("Test 3: user_id mutation blocked")
        rec3 = _make_record(user_id="alice")
        blocked3 = False
        try:
            rec3.user_id = "attacker"  # type: ignore
        except Exception:
            blocked3 = True
        correct3 = blocked3 and rec3.user_id == "alice"
        if not correct3: all_correct = False
        logger.info(f"  blocked={blocked3} → {'✓' if correct3 else '✗'}")
        results.append({"test": "user_id_frozen", "correct": correct3})

        # Test 4: cannot mutate created_at
        logger.info("Test 4: created_at mutation blocked")
        rec4 = _make_record()
        original_ts = rec4.created_at
        blocked4 = False
        try:
            from datetime import datetime, timezone
            rec4.created_at = datetime(2000, 1, 1, tzinfo=timezone.utc)  # type: ignore
        except Exception:
            blocked4 = True
        correct4 = blocked4 and rec4.created_at == original_ts
        if not correct4: all_correct = False
        logger.info(f"  blocked={blocked4} → {'✓' if correct4 else '✗'}")
        results.append({"test": "created_at_frozen", "correct": correct4})

        # Test 5: cannot mutate audit_id
        logger.info("Test 5: audit_id mutation blocked")
        rec5 = _make_record()
        original_id = rec5.audit_id
        blocked5 = False
        try:
            rec5.audit_id = uuid.uuid4()  # type: ignore
        except Exception:
            blocked5 = True
        correct5 = blocked5 and rec5.audit_id == original_id
        if not correct5: all_correct = False
        logger.info(f"  blocked={blocked5} → {'✓' if correct5 else '✗'}")
        results.append({"test": "audit_id_frozen", "correct": correct5})

        # Test 6: store rejects overwrite (duplicate audit_id)
        logger.info("Test 6: store rejects duplicate audit_id")
        store = InMemoryAuditStore()
        rec6 = _make_record()
        await store.write(rec6)
        dup_rejected = False
        try:
            await store.write(rec6)
        except (AuditStoreError, Exception):
            dup_rejected = True
        # Original intact
        stored = await store.query(request_id=rec6.request_id)
        original_intact = (len(stored) == 1 and stored[0].audit_id == rec6.audit_id)
        correct6 = dup_rejected and original_intact
        if not correct6: all_correct = False
        logger.info(f"  dup_rejected={dup_rejected} original_intact={original_intact} → {'✓' if correct6 else '✗'}")
        results.append({"test": "store_rejects_overwrite", "correct": correct6})

        # Test 7: store query returns records in write order
        logger.info("Test 7: store query returns records in write order")
        store2 = InMemoryAuditStore()
        req_id = uuid.uuid4()
        recs = [_make_record(request_id=req_id,
                             event_type=t) for t in [
            AuditEventType.WORKFLOW_STARTED,
            AuditEventType.PLAN_PROPOSED,
            AuditEventType.WORKFLOW_COMPLETED,
        ]]
        for r in recs:
            await store2.write(r)
        queried = await store2.query(request_id=req_id)
        order_ok = [r.event_type for r in queried] == [r.event_type for r in recs]
        if not order_ok: all_correct = False
        logger.info(f"  order_preserved={order_ok} → {'✓' if order_ok else '✗'}")
        results.append({"test": "write_order_preserved", "correct": order_ok})

        metrics = {
            "tests_run":                  len(results),
            "tests_passed":               sum(1 for r in results if r["correct"]),
            "all_fields_frozen":          all([r["correct"] for r in results[:5]]),
            "store_rejects_overwrite":    correct6,
            "write_order_preserved":      order_ok,
            "all_correct":                all_correct,
        }

        if all_correct:
            verdict, hyp = Verdict.PASS, True
            summary = ("AuditRecord is fully immutable — all 5 fields "
                       "frozen, store rejects overwrites, write order preserved.")
            observations = [
                "event_type, tenant_id, user_id, created_at, audit_id all frozen.",
                "InMemoryAuditStore rejects duplicate audit_id writes.",
                "Original record intact after failed overwrite attempt.",
                "Query returns records in insertion order.",
            ]
        else:
            failed = [r["test"] for r in results if not r["correct"]]
            verdict, hyp = Verdict.FAIL, False
            summary = f"Immutability failure in: {failed}"
            observations = [f"Failed: {failed}"]

        return ExperimentResult(verdict=verdict, summary=summary,
            hypothesis_supported=hyp, metrics=metrics,
            observations=observations, raw_outputs=results)

    async def teardown(self): pass

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--findings-dir", default="findings")
    args = p.parse_args()
    exp = OBS_003(); result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}\nSummary : {result.summary}")
    for k, v in result.metrics.items(): print(f"  {k:<45} {v}")
