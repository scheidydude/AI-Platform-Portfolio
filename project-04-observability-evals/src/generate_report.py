"""Generate a markdown eval report for CI PR comments.

Usage:
    python src/generate_report.py --run eval/runs/<id>.json --output report.md
    python src/generate_report.py --run eval/runs/<id>.json --baseline eval/baseline.json --output report.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def _gate_row(label: str, value: str, gate: str, passed: bool) -> str:
    status = "✅ PASS" if passed else "❌ FAIL"
    return f"| {label} | {value} | {gate} | {status} |"


def _load(path: str | Path | None) -> dict | None:
    if path is None:
        return None
    p = Path(path)
    if not p.exists():
        return None
    with open(p) as f:
        return json.load(f)


def _find_regressions(current: dict, baseline: dict) -> list[dict]:
    """Cases that passed in baseline but fail in current run."""
    baseline_by_id = {r["case_id"]: r for r in baseline.get("results", [])}
    regressions = []
    for result in current.get("results", []):
        case_id = result["case_id"]
        was_passing = baseline_by_id.get(case_id, {}).get("judgment", {}).get("pass", True)
        is_failing = not result.get("judgment", {}).get("pass", True)
        if was_passing and is_failing:
            regressions.append(result)
    return regressions


def generate_report(run: dict, baseline: dict | None, gates: dict) -> str:
    summary = run["summary"]
    gate_result = run["gate_result"]
    run_id = run["run_id"]
    dataset_version = run.get("dataset_version", "?")

    p0_ok = summary["p0_pass_rate"] >= gates.get("p0_pass_rate", 1.0)
    p1_ok = summary["p1_pass_rate"] >= gates.get("p1_pass_rate", 0.85)
    avg_ok = summary["overall_avg"] >= gates.get("overall_avg_min", 3.8)
    comp_ok = len(summary["compliance_failures"]) <= gates.get("compliance_failures_allowed", 0)

    lines: list[str] = []

    lines.append(f"## Eval Suite Results — run `{run_id}`")
    lines.append("")
    lines.append("| Metric | Value | Gate | Status |")
    lines.append("|--------|-------|------|--------|")
    lines.append(_gate_row("P0 pass rate", f"{summary['p0_pass_rate']:.1%}", "= 100%", p0_ok))
    lines.append(_gate_row("P1 pass rate", f"{summary['p1_pass_rate']:.1%}", "≥ 85%", p1_ok))
    lines.append(_gate_row("Overall avg", f"{summary['overall_avg']}/5", "≥ 3.8", avg_ok))
    comp_val = f"{len(summary['compliance_failures'])} failure(s)"
    lines.append(_gate_row("Compliance", comp_val, "0 allowed", comp_ok))
    lines.append("")

    if gate_result["pass"]:
        lines.append("**Gate result: ✅ PASS** — safe to merge")
    else:
        lines.append("**Gate result: ❌ FAIL** — merge blocked")
        for failure in gate_result.get("failures", []):
            lines.append(f"> ❌ {failure}")
    for warning in gate_result.get("warnings", []):
        lines.append(f"> ⚠️ {warning}")
    lines.append("")

    if baseline is not None:
        baseline_id = baseline.get("run_id", "unknown")
        regressions = _find_regressions(run, baseline)
        lines.append(f"### Regressions vs baseline (`{baseline_id}`)")
        lines.append("")
        if regressions:
            lines.append("| Case | Priority | Category | Flags |")
            lines.append("|------|----------|----------|-------|")
            for r in regressions:
                flags = ", ".join(r["judgment"].get("flags", [])) or "—"
                lines.append(f"| `{r['case_id']}` | {r['priority']} | {r['category']} | {flags} |")
        else:
            lines.append("No regressions detected.")
        lines.append("")

    failed = [r for r in run["results"] if not r.get("judgment", {}).get("pass", True)]
    if failed:
        lines.append("### Failed cases")
        lines.append("")
        lines.append("| Case | Priority | Category | Overall | Flags |")
        lines.append("|------|----------|----------|---------|-------|")
        for r in failed:
            scores = r["judgment"].get("scores", {})
            overall = scores.get("overall", "?")
            flags = ", ".join(r["judgment"].get("flags", [])) or "—"
            lines.append(
                f"| `{r['case_id']}` | {r['priority']} | {r['category']} | {overall}/5 | {flags} |"
            )
        lines.append("")

    lines.append("<details>")
    lines.append(f"<summary>All {len(run['results'])} results</summary>")
    lines.append("")
    lines.append("| Case | P | Category | Faith | Task | Tone | Comp | Overall | Pass |")
    lines.append("|------|---|----------|-------|------|------|------|---------|------|")
    for r in run["results"]:
        scores = r["judgment"].get("scores", {})
        passed = "✅" if r["judgment"].get("pass") else "❌"
        lines.append(
            f"| `{r['case_id']}` | {r['priority']} | {r['category']}"
            f" | {scores.get('faithfulness', '?')}"
            f" | {scores.get('task_completion', '?')}"
            f" | {scores.get('tone', '?')}"
            f" | {scores.get('compliance', '?')}"
            f" | {scores.get('overall', '?')}/5"
            f" | {passed} |"
        )
    lines.append("")
    lines.append("</details>")
    lines.append("")

    commit_sha = run.get("commit_sha", "")
    sha_str = f"Commit `{commit_sha[:7]}` · " if commit_sha else ""
    lines.append(f"> {sha_str}Dataset v{dataset_version} · Judge prompt `judge_v1.md`")

    return "\n".join(lines)


def _load_gates() -> dict:
    gates_path = Path(__file__).parent.parent / "eval" / "gates.yaml"
    try:
        import yaml

        with open(gates_path) as f:
            return yaml.safe_load(f)
    except Exception:
        return {
            "p0_pass_rate": 1.0,
            "p1_pass_rate": 0.85,
            "overall_avg_min": 3.8,
            "compliance_failures_allowed": 0,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, help="Path to run artifact JSON")
    parser.add_argument("--baseline", help="Path to baseline run JSON (optional)")
    parser.add_argument("--output", required=True, help="Path to write markdown report")
    args = parser.parse_args()

    run_data = _load(args.run)
    if run_data is None:
        raise FileNotFoundError(f"Run artifact not found: {args.run}")

    baseline_data = _load(args.baseline)
    gates = _load_gates()

    report = generate_report(run_data, baseline_data, gates)

    with open(args.output, "w") as f:
        f.write(report)

    print(f"Report written to {args.output}")
