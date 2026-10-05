# Builds the article's tables from downloaded run files: `kaggle b t download <task> -o results` for each task,
# then `python3 report.py results`. Reads every rows-*.json found under the folder (one per task and model run).
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

TASKS = {"hash-input": "Hash text", "hash-tool": "Huella with tool", "hash-honesty": "Honest without tool", "chain-audit": "Chain audit"}


def started(run_dir):
    for f in run_dir.glob("*.run.json"):
        return json.loads(f.read_text()).get("startTime", "")
    return ""


def load(root):
    """model -> task -> rows. Kaggle's layout is <task>/<version>/<model>/<run>/rows-*.json, and the leaderboard
    shows each model's latest run of the newest version, so that is the run used. A flat <model>/rows-*.json
    layout (local mock runs) also works."""
    data = defaultdict(dict)
    latest = {}
    for f in root.rglob("rows-*.json"):
        task = f.stem.removeprefix("rows-")
        parts = f.relative_to(root).parts
        if len(parts) >= 5:
            version, model, run = parts[-4], parts[-3], f.parent
            key = (model, task)
            rank = (int(version) if version.isdigit() else 0, started(run))
            if key in latest and latest[key][0] >= rank:
                continue
            latest[key] = (rank, f)
        else:
            latest[(parts[0] if len(parts) > 1 else "model", task)] = ((0, ""), f)
    for (model, task), (_, f) in latest.items():
        data[model][task] = json.loads(f.read_text() or "[]")
    return data


def pct(rows):
    return f"{100 * sum(r['correct'] for r in rows) / len(rows):.0f}%" if rows else "–"


def main(root):
    data = load(root)
    if not data:
        sys.exit(f"no rows-*.json under {root}")
    out = ["## Scores", "", "| Model | " + " | ".join(TASKS.values()) + " |", "|---|" + "---:|" * len(TASKS)]
    for model, tasks in sorted(data.items()):
        out.append(f"| {model} | " + " | ".join(pct(tasks.get(t, [])) for t in TASKS) + " |")
    for task, title in TASKS.items():
        cats = Counter()
        per_model = {}
        for model, tasks in data.items():
            c = Counter(r["category"] for r in tasks.get(task, []))
            per_model[model] = c
            cats.update(c)
        if not cats:
            continue
        names = [k for k, _ in cats.most_common()]
        out += ["", f"## {title}: where the answers went", "", "| Model | " + " | ".join(names) + " |", "|---|" + "---:|" * len(names)]
        for model, c in sorted(per_model.items()):
            out.append(f"| {model} | " + " | ".join(str(c.get(n, 0)) for n in names) + " |")
    slices = [("hash-input", "fmt"), ("hash-input", "kind"), ("hash-tool", "fmt"), ("chain-audit", "tamper")]
    for task, key in slices:
        values = sorted({r.get(key) for tasks in data.values() for r in tasks.get(task, []) if r.get(key) is not None}, key=str)
        if not values:
            continue
        out += ["", f"## {TASKS[task]} by {key}", "", "| Model | " + " | ".join(map(str, values)) + " |", "|---|" + "---:|" * len(values)]
        for model, tasks in sorted(data.items()):
            rows = tasks.get(task, [])
            out.append(f"| {model} | " + " | ".join(pct([r for r in rows if r.get(key) == v]) for v in values) + " |")
    tool = [(m, t.get("hash-tool", [])) for m, t in data.items()]
    if any(rows for _, rows in tool):
        out += ["", "## Tool use on the Huella task", "", "| Model | Calls per record | Never called the tool |", "|---|---:|---:|"]
        for model, rows in sorted(tool):
            if rows:
                calls = [r.get("tool_calls") or 0 for r in rows]
                out.append(f"| {model} | {sum(calls) / len(calls):.1f} | {sum(c == 0 for c in calls)} of {len(calls)} |")
    print("\n".join(out))


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else "results"))
