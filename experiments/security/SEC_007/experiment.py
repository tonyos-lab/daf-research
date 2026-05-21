"""
SEC-007 — Input Sanitisation Coverage
Tier: 1 | Depends on: none
"""
from __future__ import annotations
import sys
from pathlib import Path
_r = Path(__file__).resolve().parents[3]
if str(_r) not in sys.path: sys.path.insert(0, str(_r))

from daf.components.input_processor import InputProcessor, InputValidationError
from daf.research.base import BaseExperiment, ExperimentResult, Verdict, Domain, Tier

class SEC_007(BaseExperiment):
    experiment_id = "SEC-007"
    domain = Domain.SECURITY
    tier = Tier.OFFLINE
    title = "Input Sanitisation Coverage"
    research_question = "What categories of malicious input does the InputProcessor reject before reaching the LLM?"
    hypothesis = "All 8 adversarial input categories are rejected at the InputProcessor stage — none reach the LLM."
    depends_on = []
    estimated_cost_usd = 0.0
    estimated_minutes = 3

    async def prepare(self): pass

    async def run(self) -> ExperimentResult:
        logger = self._active_logger
        processor = InputProcessor()
        results = []
        all_correct = True

        # Each case: (category, raw_input, should_raise)
        cases = [
            # Category 1: empty task
            ("empty_task", {"task": ""}, True),
            # Category 2: whitespace-only task
            ("whitespace_task", {"task": "   \t\n  "}, True),
            # Category 3: task exceeding max length
            ("oversized_task", {"task": "x" * 10_001}, True),
            # Category 4: non-string task
            ("non_string_task_int", {"task": 12345}, True),
            ("non_string_task_list", {"task": ["do", "something"]}, True),
            ("non_string_task_none", {"task": None}, True),
            # Category 5: negative max_cost constraint
            ("negative_cost", {"task": "valid task", "constraints": {"max_cost_usd": -1.0}}, True),
            # Category 6: zero max_cost constraint
            ("zero_cost", {"task": "valid task", "constraints": {"max_cost_usd": 0.0}}, True),
            # Category 7: non-numeric max_cost
            ("string_cost", {"task": "valid task", "constraints": {"max_cost_usd": "free"}}, True),
            # Category 8: non-dict constraints
            ("list_constraints", {"task": "valid task", "constraints": ["cheap"]}, True),
            # Category 9: zero max_duration
            ("zero_duration", {"task": "valid task", "constraints": {"max_duration_s": 0}}, True),
            # Negative: valid input accepted
            ("valid_minimal", {"task": "Analyse contracts"}, False),
            ("valid_full", {
                "task": "Analyse quarterly contracts",
                "tenant_id": "acme", "user_id": "alice",
                "constraints": {"max_cost_usd": 1.0},
            }, False),
        ]

        for name, raw, should_raise in cases:
            raised = False
            try:
                processor.process(raw)
            except (InputValidationError, Exception):
                raised = True

            correct = raised == should_raise
            if not correct: all_correct = False
            expected_label = "REJECTED" if should_raise else "ACCEPTED"
            actual_label   = "REJECTED" if raised else "ACCEPTED"
            logger.info(
                f"  {name:<35} expected={expected_label} actual={actual_label} "
                f"→ {'✓' if correct else '✗'}"
            )
            results.append({"case": name, "should_raise": should_raise,
                            "raised": raised, "correct": correct})

        # Measure: valid input passes through correctly
        valid_cases  = [r for r in results if not r["should_raise"]]
        invalid_cases = [r for r in results if r["should_raise"]]
        rejection_rate = sum(1 for r in invalid_cases if r["raised"]) / len(invalid_cases)

        metrics = {
            "total_cases": len(cases),
            "invalid_cases_tested": len(invalid_cases),
            "valid_cases_tested": len(valid_cases),
            "invalid_cases_rejected": sum(1 for r in invalid_cases if r["raised"]),
            "valid_cases_accepted": sum(1 for r in valid_cases if not r["raised"]),
            "rejection_rate": round(rejection_rate, 4),
            "false_positives": sum(1 for r in valid_cases if r["raised"]),
            "false_negatives": sum(1 for r in invalid_cases if not r["raised"]),
            "all_sanitisation_correct": all_correct,
        }

        if all_correct:
            verdict, hyp = Verdict.PASS, True
            summary = f"InputProcessor correctly handles all {len(invalid_cases)} invalid input categories with 0 false positives."
            observations = [
                "Empty, whitespace, oversized, and non-string tasks all rejected.",
                "Invalid constraint values (negative, zero, non-numeric) rejected.",
                "Non-dict constraints rejected.",
                "Valid inputs pass through without false rejection.",
            ]
        else:
            false_neg = [r["case"] for r in invalid_cases if not r["raised"]]
            false_pos = [r["case"] for r in valid_cases if r["raised"]]
            verdict, hyp = Verdict.FAIL, False
            summary = f"Sanitisation gaps: false_negatives={false_neg} false_positives={false_pos}"
            observations = [f"Missed rejections: {false_neg}", f"False rejections: {false_pos}"]

        return ExperimentResult(verdict=verdict, summary=summary,
            hypothesis_supported=hyp, metrics=metrics,
            observations=observations, raw_outputs=results)

    async def teardown(self): pass

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(); p.add_argument("--findings-dir", default="findings")
    args = p.parse_args()
    exp = SEC_007(); result = exp.execute(findings_dir=args.findings_dir)
    print(f"\nVerdict : {result.verdict.value.upper()}\nSummary : {result.summary}")
    for k, v in result.metrics.items(): print(f"  {k:<45} {v}")
