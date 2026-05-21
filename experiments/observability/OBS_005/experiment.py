"""
OBS-005 — Grafana Dashboard Coverage
Tier: 2 (requires Docker stack with Grafana + OTEL)
Depends on: OBS-004

STATUS: Tier 2 scaffold — requires docker-compose stack.
"""
from __future__ import annotations
import sys
from pathlib import Path
_r = Path(__file__).resolve().parents[3]
if str(_r) not in sys.path: sys.path.insert(0, str(_r))

from daf.research.base import BaseExperiment, ExperimentResult, Verdict, Domain, Tier


class OBS_005(BaseExperiment):
    experiment_id      = "OBS-005"
    domain             = Domain.OBSERVABILITY
    tier               = Tier.SERVICES
    title              = "Grafana Dashboard Coverage"
    research_question  = ("Do the Grafana dashboards expose all metrics "
                          "required for operational monitoring?")
    hypothesis         = ("The default Grafana dashboard covers loop duration, "
                          "cost per workflow, violation rate, and escalation rate.")
    depends_on         = ["OBS-004"]
    estimated_cost_usd = 0.0
    estimated_minutes  = 30

    async def prepare(self) -> None:
        """
        Tier 2 prep:
          1. docker-compose up -d
          2. Verify Grafana at http://localhost:3000 (admin/admin)
          3. pip install requests
        """
        try:
            import requests  # type: ignore
        except ImportError:
            raise RuntimeError(
                "OBS-005 requires requests. Run: pip install requests"
            )
        raise NotImplementedError(
            "OBS-005 is a Tier 2 experiment requiring the Docker stack. "
            "Start with: docker-compose up -d\n"
            "Then implement: query Grafana API to verify dashboard panel coverage."
        )

    async def run(self) -> ExperimentResult:
        """
        Implementation steps:
          1. Query Grafana API: GET /api/dashboards/uid/daf-overview
          2. Extract panel titles and datasource queries
          3. Verify required panels exist:
             - Loop duration (p50, p95, p99)
             - Cost per workflow (sum, avg)
             - Violation rate (% of plans rejected)
             - Escalation rate (% of workflows escalated)
             - HITL gate rate (% requiring human review)
          4. Verify panels query the OTEL datasource correctly
        """
        raise NotImplementedError("OBS-005 run() not yet implemented.")

    async def teardown(self) -> None:
        pass

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--findings-dir", default="findings")
    args = p.parse_args()
    exp = OBS_005(); result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}\nSummary : {result.summary}")
