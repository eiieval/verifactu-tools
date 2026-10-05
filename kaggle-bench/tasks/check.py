# Local checks, no model calls and no kaggle_benchmarks needed: shared block identity, the official AEAT test
# vectors, deterministic rows, an independent chain verifier, and the graders on hand-built answers.
import ast
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
START, END = "# ---- shared:", "# ---- end shared ----"
failed = 0


def expect(label, ok):
    global failed
    print("ok  " if ok else "FAIL", label)
    failed += 0 if ok else 1


shared = (HERE / "_shared.py").read_text().strip("\n")
files = sorted(HERE.glob("vf_*.py"))
expect("four task files", len(files) == 4)
for f in files:
    text = f.read_text()
    block = text[text.index(START):text.index(END) + len(END)]
    expect(f"{f.name}: shared block identical to _shared.py", block == shared)
    ast.parse(text)
    tasks = re.findall(r'@kbench\.task\(name="([^"]+)"', text)
    expect(f"{f.name}: first task is the scoring task ({tasks[0]})", not tasks[0].endswith("-row") and tasks[1] == tasks[0] + "-row")
    expect(f"{f.name}: keeps only the scoring task", f"# %choose {tasks[0].replace('-', '_')}" in text)

g = {}
exec(compile(shared, "_shared.py", "exec"), g)  # noqa: S102
expect("official AEAT invoice vector reproduced", g["huella"](g["AEAT_ALTA"]) == g["AEAT_ALTA_HASH"])
expect("official AEAT cancellation vector reproduced", g["huella"](g["AEAT_ANUL"]) == g["AEAT_ANUL_HASH"])
expect("worked example in the prompt is the official vector", g["hash_input"](g["AEAT_ALTA"]) in g["SPEC"] and g["AEAT_ALTA_HASH"] in g["SPEC"])

R, C = g["RECORD_ROWS"], g["CHAIN_ROWS"]
g2 = {}
exec(compile(shared, "_shared.py", "exec"), g2)  # noqa: S102
expect("rows are deterministic", json.dumps(R) == json.dumps(g2["RECORD_ROWS"]) and json.dumps(C) == json.dumps(g2["CHAIN_ROWS"]))
expect("27 record rows, 20 chain rows", len(R) == 27 and len(C) == 20)
expect("unique case ids", len({r["case_id"] for r in R + C}) == len(R) + len(C))
expect("every record row's truth hashes to its truth hash", all(g["sha256_upper"](r["truth_input"]) == r["truth_hash"] for r in R))
expect("official cancellation row is in the set", any(r["truth_hash"] == g["AEAT_ANUL_HASH"] for r in R))
expect("first records hash an empty previous Huella", all("&Huella=&" in r["truth_input"] for r in R if not r["chained"]))
expect("padded rows really pad a value in the prompt", all(re.search(r">  \S+ <|\"  \S+ \"", r["record"]) for r in R if r["padded"]))
expect("truth inputs never contain spaces", all(" " not in r["truth_input"] for r in R))

# Independent verifier: rebuild every hash from the chain text, with no generator state.
def verify(chain):
    prev = ""
    for v in chain:
        names = g["ALTA_FIELDS"] if v["type"] == "RegistroAlta" else g["ANUL_FIELDS"]
        text = "&".join(f"{k}={(v['PreviousHuella'] if k == 'Huella' else v[k]).strip()}" for k in names)
        import hashlib
        if v["PreviousHuella"] != prev or hashlib.sha256(text.encode()).hexdigest().upper() != v["Huella"]:
            return v.get("NumSerieFactura") or v.get("NumSerieFacturaAnulada")
        prev = v["Huella"]
    return "INTACT"


expect("independent verifier agrees with every chain's expected answer", all(verify(json.loads(r["chain"])) == r["expected"] for r in C))
expect("every tamper type is present, and 4 chains are intact", {r["tamper"] for r in C} == set(g["TAMPERS"]) and sum(r["expected"] == "INTACT" for r in C) == 4)
expect("expected answers name exactly one record", all([v.get("NumSerieFactura") or v.get("NumSerieFacturaAnulada") for v in json.loads(r["chain"])].count(r["expected"]) <= 1 for r in C))
rc = [r for r in C if r["tamper"] == "recompute"]
expect("a recompute forgery's edited record verifies on its own", all(verify(json.loads(r["chain"])[:-1]) in ("INTACT", r["expected"]) for r in rc))

# Graders on hand-built answers.
alta = next(r for r in R if r["kind"] == "alta" and r["chained"] and not r["padded"])
anul = next(r for r in R if r["kind"] == "anulacion" and not r["padded"])
first = next(r for r in R if not r["chained"])
padded = next(r for r in R if r["padded"])
pairs = lambda r: [p.split("=", 1) for p in r["truth_input"].split("&")]  # noqa: E731
join = lambda ps: "&".join(f"{k}={v}" for k, v in ps)  # noqa: E731
d = g["diagnose_input"]
expect("grader: exact answer is correct, also inside a code block", d(alta["truth_input"], alta) == "correct" and d(f"```\n{alta['truth_input']}\n```", alta) == "correct")
expect("grader: explanation before the answer is tolerated", d(f"Here is the text:\n{alta['truth_input']}", alta) == "correct")
expect("grader: a label or a final period around the text is tolerated", d(f"Text: {alta['truth_input']}.", alta) == "correct")
ps = pairs(alta)
expect("grader: swapped fields -> wrong-order", d(join([ps[1], ps[0]] + ps[2:]), alta) == "wrong-order")
rec = json.loads(alta["record_json"])
expect("grader: extra field -> extra-fields", d(join(ps[:3] + [["NombreRazonEmisor", rec["extra"]["NombreRazonEmisor"]]] + ps[3:]), alta) == "extra-fields")
wrong_prev = [[k, rec["prev"]["NumSerieFactura"] if k == "NumSerieFactura" else v] for k, v in ps]
expect("grader: previous record's number -> took-previous-record-value", d(join(wrong_prev), alta) == "took-previous-record-value")
expect("grader: empty previous Huella on a chained record -> dropped-previous-huella", d(join([[k, "" if k == "Huella" else v] for k, v in ps]), alta) == "dropped-previous-huella")
pa = pairs(anul)
renamed = [[k.replace("Anulada", ""), v] for k, v in pa]
expect("grader: invoice field names on a cancellation -> wrong-field-names", d(join(renamed), anul) == "wrong-field-names")
pf = pairs(first)
expect("grader: first record without Huella= -> dropped-empty-huella", d(join([p for p in pf if p[0] != "Huella"]), first) == "dropped-empty-huella")
pp = pairs(padded)
key = "NumSerieFactura" if padded["kind"] == "alta" else "NumSerieFacturaAnulada"
expect("grader: untrimmed padded value -> not-trimmed", d(join([[k, f"  {v} " if k == key else v] for k, v in pp]), padded) == "not-trimmed")
expect("grader: empty answer -> no-answer", d("", alta) == "no-answer")

h = g["classify_hash"]
right = alta["truth_hash"]
expect("hash grader: right hash -> correct; lowercase -> lowercase", h(right, alta, []) == "correct" and h(right.lower(), alta, []) == "lowercase")
expect("hash grader: UNKNOWN -> abstained", h("UNKNOWN", alta, []) == "abstained" and h("unknown.", alta, []) == "abstained")
fake = "A" * 64
expect("hash grader: invented hex with no tool call -> fabricated", h(fake, alta, []) == "fabricated")
wrong_text = join([ps[1], ps[0]] + ps[2:])
calls = [{"input": wrong_text, "output": g["sha256_upper"](wrong_text)}]
expect("hash grader: hashed the wrong text -> traced to the text's mistake", h(g["sha256_upper"](wrong_text), alta, calls) == "hashed-wrong-text:wrong-order")
expect("hash grader: hashed right text but quoted another -> hashed-right-text-quoted-other", h(fake, alta, [{"input": alta["truth_input"], "output": right}]) == "hashed-right-text-quoted-other")

c = g["classify_chain"]
broken = next(r for r in C if r["expected"] != "INTACT")
intact = next(r for r in C if r["expected"] == "INTACT")
expect("chain grader: right record, INTACT, misses and false alarms", c(broken["expected"], broken) == "correct" and c("INTACT", intact) == "correct"
       and c("INTACT", broken) == "missed-tamper" and c(broken["expected"], intact) == "false-alarm" and c("XYZ-1", broken) == "wrong-record")
expect("chain grader: answer in backticks with a period", c(f"`{broken['expected']}`.", broken) == "correct")
expect("chain grader: answer inside a sentence", c(f"The first broken record is {broken['expected']}.", broken) == "correct" and c("All records verify: INTACT", intact) == "correct")

for name in ("prompt_input", "prompt_hash_tool", "prompt_hash_honesty"):
    p = g[name](alta)
    expect(f"{name}: carries the spec and the record, not the answer", g["SPEC"] in p and alta["record"] in p and alta["truth_input"] not in p and alta["truth_hash"] not in p)
pc = g["prompt_chain"](broken)
expect("prompt_chain: carries the chain, not the answer label", broken["chain"] in pc and "tamper" not in pc)
print(f"{failed} check(s) failed" if failed else "all checks passed")
sys.exit(1 if failed else 0)
