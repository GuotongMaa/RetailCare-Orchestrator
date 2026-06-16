"""Minimal action-level eval runner (M1 baseline).

Each task declares expected_actions (tools that MUST be called) and
forbidden_actions (tools that must NOT be called) — the tau3 `evaluation_criteria.
actions` philosophy. A task passes iff all expected tools fired and no forbidden
tool fired. Produces pass@1 over a single run.

M3 extends this with multi-seed / pass^k / confidence intervals / LLM-judge /
error taxonomy / cost. Run:  python -m eval.runner
"""
from __future__ import annotations

import json
from pathlib import Path

from retailcare.config import settings, usage
from retailcare.data.seed import seed
from retailcare.graph.runtime import Conversation

DATASET = Path("eval/datasets/refund_tasks.jsonl")
REPORT = Path("reports/baseline_report.md")


def load_tasks(path: Path = DATASET) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def tools_called(conv: Conversation) -> list[str]:
    return [e.name for e in conv.trace.events if e.kind == "tool_call"]


def evaluate_task(task: dict) -> dict:
    conv = Conversation(user_id=task["user_id"], auto_confirm=True)
    error = None
    try:
        reply = conv.send(task["message"]).reply
    except Exception as e:  # noqa: BLE001
        reply, error = "", repr(e)
    called = set(tools_called(conv))
    expected = set(task.get("expected_actions", []))
    forbidden = set(task.get("forbidden_actions", []))
    missing = expected - called
    violated = forbidden & called
    passed = not error and not missing and not violated
    return {
        "id": task["id"], "intent": task["intent"], "passed": passed,
        "missing": sorted(missing), "violated": sorted(violated),
        "called": sorted(called), "error": error, "reply": reply,
    }


def run(seed_db: bool = True) -> dict:
    if seed_db:
        seed(reset=True)
    usage.reset()
    tasks = load_tasks()
    results = [evaluate_task(t) for t in tasks]
    passed = sum(r["passed"] for r in results)
    summary = {
        "model": settings.model, "n": len(tasks), "passed": passed,
        "pass@1": round(passed / len(tasks), 4) if tasks else 0.0,
        "usage": usage.snapshot(),
    }
    _write_report(summary, results)
    return {"summary": summary, "results": results}


def _write_report(summary: dict, results: list[dict]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Baseline Report (M1 · L0 single agent)", "",
        f"- model: `{summary['model']}`",
        f"- tasks: {summary['n']}  |  passed: {summary['passed']}  |  "
        f"**pass@1 = {summary['pass@1']}**",
        f"- usage: {summary['usage']}", "",
        "| id | intent | pass | called | missing | violated |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        lines.append(
            f"| {r['id']} | {r['intent']} | {'✅' if r['passed'] else '❌'} | "
            f"{', '.join(r['called']) or '—'} | {', '.join(r['missing']) or '—'} | "
            f"{', '.join(r['violated']) or '—'} |"
        )
    lines += ["", "> pass@1 is a single-run baseline. M3 reports multi-seed pass^k + CIs.", ""]
    REPORT.write_text("\n".join(lines))


if __name__ == "__main__":
    out = run()
    print(json.dumps(out["summary"], indent=2))
    for r in out["results"]:
        flag = "✅" if r["passed"] else "❌"
        extra = "" if r["passed"] else f"  missing={r['missing']} violated={r['violated']} err={r['error']}"
        print(f"  {flag} {r['id']} {r['intent']}{extra}")
    print(f"\n📄 report: {REPORT}")
