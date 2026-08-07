from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "03 Demo代码" / "backend"
sys.path.insert(0, str(BACKEND))

from app.agents.mock_provider import MockAnalysisProvider  # noqa: E402

CASES_PATH = Path(__file__).resolve().parent / "测试案例" / "deposit-v1-synthetic.jsonl"


def load_cases() -> list[dict]:
    return [json.loads(line) for line in CASES_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def score_ratio(correct: int, total: int) -> float | None:
    return round(correct / total, 4) if total else None


def main() -> int:
    provider = MockAnalysisProvider()
    output_path = Path(__file__).resolve().parent / "评测结果" / f"mock-baseline-{provider.prompt_version.removeprefix('mock-')}.json"
    counters = {
        "scope": [0, 0],
        "amount": [0, 0],
        "lease_status": [0, 0],
        "reason_presence": [0, 0],
        "completeness": [0, 0],
    }
    details: list[dict] = []

    for case in load_cases():
        intent = provider.identify_intent(case["description"], "DEPOSIT")
        expected_in_scope = bool(case["expected_in_scope"])
        scope_ok = intent.in_scope == expected_in_scope
        counters["scope"][1] += 1
        counters["scope"][0] += int(scope_ok)
        failures: list[str] = [] if scope_ok else ["scope"]
        actual: dict = {"in_scope": intent.in_scope, "case_type": intent.case_type}

        if expected_in_scope:
            raw_amount = case.get("form_amount")
            form_amount = Decimal(raw_amount) if raw_amount is not None else None
            extracted = provider.extract_information(case["description"], form_amount)
            completeness = provider.assess_completeness(extracted)
            checks = {
                "amount": extracted.amount == case.get("expected_amount"),
                "lease_status": extracted.lease_status == case["expected_lease_status"],
                "reason_presence": bool(extracted.deduction_reason) == bool(case["expected_reason_present"]),
                "completeness": completeness.is_complete == bool(case["expected_complete"]),
            }
            for metric, passed in checks.items():
                counters[metric][1] += 1
                counters[metric][0] += int(passed)
                if not passed:
                    failures.append(metric)
            actual.update(
                {
                    "amount": extracted.amount,
                    "lease_status": extracted.lease_status,
                    "deduction_reason": extracted.deduction_reason,
                    "completeness_score": completeness.score,
                    "is_complete": completeness.is_complete,
                }
            )

        details.append({"id": case["id"], "passed": not failures, "failures": failures, "actual": actual})

    metrics = {name: {"correct": value[0], "total": value[1], "score": score_ratio(*value)} for name, value in counters.items()}
    result = {
        "evaluation_id": f"mock-baseline-{provider.prompt_version.removeprefix('mock-')}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_notice": "全部为脱敏合成测试用例；结果仅代表规则基线在该集合上的表现。",
        "provider": provider.provider_name,
        "model": provider.model_name,
        "prompt_version": provider.prompt_version,
        "knowledge_version": provider.knowledge_version,
        "case_count": len(details),
        "metrics": metrics,
        "failed_case_count": sum(not item["passed"] for item in details),
        "details": details,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"Evaluated {len(details)} synthetic cases")
    for name, metric in metrics.items():
        print(f"{name}: {metric['correct']}/{metric['total']} = {metric['score']}")
    print(f"failed cases: {result['failed_case_count']}")
    print(f"result: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
