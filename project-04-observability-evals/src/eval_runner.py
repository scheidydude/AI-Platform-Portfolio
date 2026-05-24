"""Eval runner — orchestrates a complete eval suite run.

Usage:
    python src/eval_runner.py                  # full run (30 cases)
    python src/eval_runner.py --limit 5        # first 5 cases only
    python src/eval_runner.py --dry-run        # skip API calls, all scores = 5
    python src/eval_runner.py --dataset path   # custom dataset path

Exit codes: 0 = gates pass, 1 = one or more blocking gates failed.
Run artifact written to eval/runs/<run_id>.json.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from judge_pipeline import judge_case
from sut import run_sut

_DATASET_PATH = Path(__file__).parent.parent / "eval" / "dataset.json"
_GATES_PATH = Path(__file__).parent.parent / "eval" / "gates.yaml"
_RUNS_DIR = Path(__file__).parent.parent / "eval" / "runs"

_DEFAULT_GATES = {
    "p0_pass_rate": 1.0,
    "p1_pass_rate": 0.85,
    "overall_avg_min": 3.8,
    "compliance_failures_allowed": 0,
}


def _load_gates() -> dict:
    try:
        import yaml

        with open(_GATES_PATH) as f:
            return yaml.safe_load(f)
    except Exception:
        return _DEFAULT_GATES


def case_passes(judgment: dict, case: dict) -> bool:
    """Per-case pass determination per judge-pipeline-design.md §5."""
    scores = judgment.get("scores", {})
    if scores.get("compliance") == "fail":
        return False
    overall = scores.get("overall", 0)
    task = scores.get("task_completion", 0)
    if case["priority"] == "P0":
        return overall >= 3 and task >= 3
    return overall >= 3


def _compute_summary(results: list) -> dict:
    p0 = [r for r in results if r["priority"] == "P0"]
    p1 = [r for r in results if r["priority"] == "P1"]

    def _pass_rate(cases: list) -> float:
        if not cases:
            return 1.0
        return sum(1 for c in cases if c["judgment"].get("pass", False)) / len(cases)

    overall_scores = [
        r["judgment"]["scores"]["overall"]
        for r in results
        if isinstance(r["judgment"].get("scores", {}).get("overall"), int)
    ]
    avg_overall = round(sum(overall_scores) / len(overall_scores), 2) if overall_scores else 0.0

    compliance_failures = [
        r["case_id"]
        for r in results
        if r["judgment"].get("scores", {}).get("compliance") == "fail"
    ]

    return {
        "total_cases": len(results),
        "p0_pass_rate": round(_pass_rate(p0), 4),
        "p1_pass_rate": round(_pass_rate(p1), 4),
        "overall_avg": avg_overall,
        "compliance_failures": compliance_failures,
    }


def _check_gates(summary: dict, gates: dict) -> tuple[bool, list[str], list[str]]:
    """Returns (blocking_ok, blocking_failures, warnings)."""
    blocking = []
    warnings = []

    if summary["p0_pass_rate"] < gates["p0_pass_rate"]:
        blocking.append(
            f"P0 pass rate {summary['p0_pass_rate']:.1%} < required {gates['p0_pass_rate']:.1%}"
        )
    if summary["overall_avg"] < gates["overall_avg_min"]:
        blocking.append(
            f"Overall avg {summary['overall_avg']} < required {gates['overall_avg_min']}"
        )
    if len(summary["compliance_failures"]) > gates.get("compliance_failures_allowed", 0):
        blocking.append(
            f"Compliance failures: {summary['compliance_failures']}"
        )
    if summary["p1_pass_rate"] < gates["p1_pass_rate"]:
        warnings.append(
            f"P1 pass rate {summary['p1_pass_rate']:.1%} < target {gates['p1_pass_rate']:.1%} (warning only)"
        )

    return len(blocking) == 0, blocking, warnings


def _dry_run_judgment(case_id: str) -> dict:
    return {
        "case_id": case_id,
        "scores": {
            "faithfulness": 5,
            "task_completion": 5,
            "tone": 5,
            "compliance": "pass",
            "overall": 5,
        },
        "reasoning": "Dry run — no API calls made.",
        "flags": [],
        "pass": True,
    }


def run_eval(
    dataset_path: Path | None = None,
    limit: int | None = None,
    dry_run: bool = False,
) -> dict:
    path = dataset_path or _DATASET_PATH
    with open(path) as f:
        dataset = json.load(f)

    cases = dataset["cases"]
    if limit:
        cases = cases[:limit]

    run_id = uuid.uuid4().hex[:8]
    results = []

    print(f"Run {run_id} | {len(cases)} cases | {'DRY RUN' if dry_run else 'live'}")
    print()

    for i, case in enumerate(cases, 1):
        label = f"{case['id']} ({case['priority']}, {case['category']})"
        print(f"  [{i:2d}/{len(cases)}] {label}...", end=" ", flush=True)

        if dry_run:
            sut_output = {"dry_run": True}
            judgment = _dry_run_judgment(case["id"])
        else:
            sut_output = run_sut(case)
            judgment = judge_case(case, sut_output)

        passed = case_passes(judgment, case)
        judgment["pass"] = passed

        results.append(
            {
                "case_id": case["id"],
                "priority": case["priority"],
                "category": case["category"],
                "sut_output": sut_output,
                "judgment": judgment,
            }
        )

        status = "PASS" if passed else "FAIL"
        flags = judgment.get("flags", [])
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        print(f"{status}{flag_str}")

    summary = _compute_summary(results)
    gates = _load_gates()
    gates_ok, blocking_failures, warnings = _check_gates(summary, gates)

    run_artifact = {
        "run_id": run_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_version": dataset.get("version", "unknown"),
        "total_cases": len(results),
        "summary": summary,
        "gate_result": {
            "pass": gates_ok,
            "failures": blocking_failures,
            "warnings": warnings,
        },
        "results": results,
    }

    _RUNS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = _RUNS_DIR / f"{run_id}.json"
    with open(out_path, "w") as f:
        json.dump(run_artifact, f, indent=2)

    print()
    print("Results:")
    print(f"  P0 pass rate : {summary['p0_pass_rate']:.1%}")
    print(f"  P1 pass rate : {summary['p1_pass_rate']:.1%}")
    print(f"  Overall avg  : {summary['overall_avg']}/5")
    print(f"  Compliance   : {len(summary['compliance_failures'])} failure(s)")
    if summary["compliance_failures"]:
        for f in summary["compliance_failures"]:
            print(f"    - {f}")
    print(f"  Gate         : {'PASS' if gates_ok else 'FAIL'}")
    if blocking_failures:
        for f in blocking_failures:
            print(f"    BLOCKING: {f}")
    if warnings:
        for w in warnings:
            print(f"    WARNING:  {w}")
    print(f"  Artifact     : {out_path}")

    return run_artifact


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the eval suite.")
    parser.add_argument("--limit", type=int, help="Run only first N cases")
    parser.add_argument("--dry-run", action="store_true", help="Skip API calls; all scores = 5")
    parser.add_argument("--dataset", type=Path, help="Path to dataset JSON (default: eval/dataset.json)")
    args = parser.parse_args()

    artifact = run_eval(
        dataset_path=args.dataset,
        limit=args.limit,
        dry_run=args.dry_run,
    )

    sys.exit(0 if artifact["gate_result"]["pass"] else 1)
