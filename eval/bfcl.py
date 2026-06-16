"""BFCL-style function-calling accuracy (domain-adapted).

Single-turn probes measuring tool_call_accuracy (right tool first) and
argument_accuracy (expected args present & correct). This adapts the Berkeley
Function-Calling Leaderboard methodology to this project's MCP tool set;
integrating the full external BFCL-v4 corpus is a documented stretch goal.

    python -m eval.bfcl
"""
from __future__ import annotations

import json
from pathlib import Path

from retailcare.data.seed import seed
from retailcare.graph.runtime import Conversation

DATASET = Path("eval/datasets/bfcl_style.jsonl")
REPORT = Path("reports/bfcl_report.md")


def load(path: Path = DATASET) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def tool_calls(conv: Conversation) -> list[tuple[str, dict]]:
    return [(e.name, e.payload.get("args", {})) for e in conv.trace.events if e.kind == "tool_call"]


def evaluate(case: dict) -> dict:
    """ReAct-appropriate: the expected tool must appear somewhere in the trajectory
    (the agent may legitimately fetch the order first), with correct args on that call."""
    conv = Conversation(user_id=case["user_id"], auto_confirm=True)
    try:
        conv.send(case["message"])
    except Exception as e:  # noqa: BLE001
        return {"id": case["id"], "tool_ok": False, "args_ok": False, "error": repr(e),
                "got_tools": []}
    calls = tool_calls(conv)
    names = [n for n, _ in calls]
    matched = [a for n, a in calls if n == case["expected_tool"]]
    tool_ok = bool(matched)
    args_ok = tool_ok and any(
        all(str(a.get(k)) == str(v) for k, v in case["expected_args"].items()) for a in matched)
    return {"id": case["id"], "tool_ok": tool_ok, "args_ok": args_ok, "got_tools": names}


def run() -> dict:
    seed(reset=True)
    cases = load()
    results = [evaluate(c) for c in cases]
    n = len(results)
    tool_acc = round(sum(r["tool_ok"] for r in results) / n, 4)
    arg_acc = round(sum(r["args_ok"] for r in results) / n, 4)
    _write_report(tool_acc, arg_acc, results)
    return {"n": n, "tool_call_accuracy": tool_acc, "argument_accuracy": arg_acc,
            "results": results}


def _write_report(tool_acc: float, arg_acc: float, results: list[dict]) -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# BFCL-style Function-Calling Report (M2)", "",
        f"- **tool_call_accuracy = {tool_acc}**  |  **argument_accuracy = {arg_acc}**  "
        f"(n={len(results)})", "",
        "| id | tool_ok | args_ok | trajectory |", "|---|---|---|---|",
    ]
    for r in results:
        lines.append(f"| {r['id']} | {'✅' if r['tool_ok'] else '❌'} | "
                     f"{'✅' if r['args_ok'] else '❌'} | {', '.join(r.get('got_tools', [])) or '—'} |")
    lines += ["", "> Trajectory-presence metric (ReAct may fetch the order first). "
              "Domain-adapted BFCL methodology over the project's MCP tools; "
              "full external BFCL-v4 corpus integration is a stretch goal.", ""]
    REPORT.write_text("\n".join(lines))


if __name__ == "__main__":
    out = run()
    print(json.dumps({k: v for k, v in out.items() if k != "results"}, indent=2))
    for r in out["results"]:
        print(f"  {'✅' if r['args_ok'] else '❌'} {r['id']} trajectory={r.get('got_tools')}")
    print(f"\n📄 report: {REPORT}")
