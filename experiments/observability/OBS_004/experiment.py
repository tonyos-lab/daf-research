"""
OBS-004 — OTEL Trace Export Fidelity
Tier: 2 (requires Docker stack with OTEL collector)
Depends on: OBS-002

STATUS: Tier 2 scaffold — requires:
  - docker-compose up -d  (starts OTEL collector on localhost:4317)
  - opentelemetry-sdk, opentelemetry-exporter-otlp packages

This experiment cannot run offline. See EXPERIMENT.md for full setup.
Run with: python experiment.py --findings-dir findings
"""
from __future__ import annotations
import sys
from pathlib import Path
_r = Path(__file__).resolve().parents[3]
if str(_r) not in sys.path: sys.path.insert(0, str(_r))

from daf.research.base import BaseExperiment, ExperimentResult, Verdict, Domain, Tier


class OBS_004(BaseExperiment):
    experiment_id      = "OBS-004"
    domain             = Domain.OBSERVABILITY
    tier               = Tier.SERVICES
    title              = "OTEL Trace Export Fidelity"
    research_question  = ("Are all internal DAF spans exported correctly via "
                          "the OpenTelemetry collector?")
    hypothesis         = ("All loop stage spans — plan, evaluate, execute — "
                          "appear in the OTEL collector with correct "
                          "parent-child relationships.")
    depends_on         = ["OBS-002"]
    estimated_cost_usd = 0.0
    estimated_minutes  = 20

    async def prepare(self) -> None:
        """
        Tier 2 prep:
          1. docker-compose up -d
          2. pip install opentelemetry-sdk opentelemetry-exporter-otlp
          3. Verify collector at http://localhost:4317
        """
        try:
            import opentelemetry  # type: ignore
        except ImportError:
            raise RuntimeError(
                "OBS-004 requires opentelemetry-sdk. "
                "Run: pip install opentelemetry-sdk opentelemetry-exporter-otlp"
            )
        # TODO: verify OTEL collector is reachable
        raise NotImplementedError(
            "OBS-004 is a Tier 2 experiment requiring the Docker stack. "
            "Start with: docker-compose up -d\n"
            "Then implement: verify DAF emits spans and collector receives them."
        )

    async def run(self) -> ExperimentResult:
        """
        Implementation steps:
          1. Configure DAF with OTEL TracerProvider → OTLP exporter
          2. Run a 3-task workflow
          3. Query OTEL collector API for spans
          4. Verify: root span (workflow), child spans (plan, evaluate, execute)
          5. Verify: span names, attributes (tenant_id, request_id), timing
        """
        raise NotImplementedError("OBS-004 run() not yet implemented.")

    async def teardown(self) -> None:
        pass

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--findings-dir", default="findings")
    args = p.parse_args()
    exp = OBS_004(); result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}\nSummary : {result.summary}")
