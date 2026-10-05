# %% [markdown]
# # VeriFactu: build the hash text
#
# Spain's VeriFactu law makes every invoice record carry a SHA-256 fingerprint ("Huella") of a text built
# from a few fields, in an exact order, chained to the previous record. This task gives the model the AEAT
# specification and one record (XML as sent to the tax agency, or a JSON payload with shuffled keys) and asks
# for the exact text that is hashed. No hashing is needed: it measures spec-following on a real regulation.
# Graded by exact match; wrong answers are classified (wrong order, extra fields, previous record's values,
# untrimmed values...). Ground truth is computed by code and anchored to the official AEAT test vectors.

# %%
import kaggle_benchmarks as kbench
import pandas as pd

# %%
# ---- shared: identical in every task file (sync.py copies it, check.py enforces it) ----
# Ground truth, prompts and grading for the VeriFactu hash benchmark. Every expected answer is computed here by
# code from the AEAT specification; the generator is anchored to the two official AEAT test vectors.
import hashlib
import json
import os
import random
import re
import time

MAX_OUTPUT_TOKENS = 6144
OUT_DIR = "/kaggle/working" if os.path.isdir("/kaggle/working") else os.environ.get("VF_OUT", "results-local")

ALTA_FIELDS = ["IDEmisorFactura", "NumSerieFactura", "FechaExpedicionFactura", "TipoFactura", "CuotaTotal", "ImporteTotal", "Huella", "FechaHoraHusoGenRegistro"]
ANUL_FIELDS = ["IDEmisorFacturaAnulada", "NumSerieFacturaAnulada", "FechaExpedicionFacturaAnulada", "Huella", "FechaHoraHusoGenRegistro"]

SPEC = """VeriFactu record fingerprint ("Huella"), as specified by the Spanish Tax Agency (AEAT):
1. Build one text by joining name=value pairs with "&", in exactly this order and with exactly these names:
   - Invoice record (RegistroAlta): IDEmisorFactura, NumSerieFactura, FechaExpedicionFactura, TipoFactura, CuotaTotal, ImporteTotal, Huella, FechaHoraHusoGenRegistro
   - Cancellation record (RegistroAnulacion): IDEmisorFacturaAnulada, NumSerieFacturaAnulada, FechaExpedicionFacturaAnulada, Huella, FechaHoraHusoGenRegistro
   In that text, "Huella" is the fingerprint of the PREVIOUS record in the chain (found under Encadenamiento/RegistroAnterior). For the first record of a chain it is empty, written as "Huella=".
2. Each value is taken exactly as it appears in the record, after removing leading and trailing spaces. Nothing else is added.
3. The fingerprint is the SHA-256 of that text encoded as UTF-8, written as 64 uppercase hexadecimal characters.
Worked example (first invoice record of a chain):
IDEmisorFactura=89890001K&NumSerieFactura=12345678/G33&FechaExpedicionFactura=01-01-2024&TipoFactura=F1&CuotaTotal=12.35&ImporteTotal=123.45&Huella=&FechaHoraHusoGenRegistro=2024-01-01T19:20:30+01:00
Its fingerprint is 3C464DAF61ACB827C65FDA19F352A4E3BDC2C640E9E9FC4CC058073F38F12F60"""

# Official AEAT test vectors (hash specification document). check.py proves the code reproduces both.
AEAT_ALTA = dict(kind="alta", fields={"IDEmisorFactura": "89890001K", "NumSerieFactura": "12345678/G33", "FechaExpedicionFactura": "01-01-2024", "TipoFactura": "F1", "CuotaTotal": "12.35", "ImporteTotal": "123.45", "Huella": "", "FechaHoraHusoGenRegistro": "2024-01-01T19:20:30+01:00"})
AEAT_ALTA_HASH = "3C464DAF61ACB827C65FDA19F352A4E3BDC2C640E9E9FC4CC058073F38F12F60"
AEAT_ANUL = dict(kind="anulacion", fields={"IDEmisorFacturaAnulada": "89890001K", "NumSerieFacturaAnulada": "12345679/G34", "FechaExpedicionFacturaAnulada": "01-01-2024", "Huella": "F7B94CFD8924EDFF273501B01EE5153E4CE8F259766F88CF6ACB8935802A2B97", "FechaHoraHusoGenRegistro": "2024-01-01T19:20:40+01:00"})
AEAT_ANUL_HASH = "177547C0D57AC74748561D054A9CEC14B4C4EA23D1BEFD6F2E69E3A388F90C68"

HEX64 = re.compile(r"\b[0-9A-Fa-f]{64}\b")


def field_order(kind):
    return ALTA_FIELDS if kind == "alta" else ANUL_FIELDS


def hash_input(rec):
    return "&".join(f"{k}={str(rec['fields'][k]).strip()}" for k in field_order(rec["kind"]))


def sha256_upper(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def huella(rec):
    return sha256_upper(hash_input(rec))


# ---------- realistic records ----------

DNI = "TRWAGMYFPDXBNJZSQVHLCKE"


def nif_person(rng):
    n = rng.randint(10000000, 99999999)
    return f"{n}{DNI[n % 23]}"


def nif_company(rng):
    letter = rng.choice("ABG")
    digits = [rng.randint(0, 9) for _ in range(7)]
    total = 0
    for i, d in enumerate(digits):
        total += d if i % 2 else (d * 2) // 10 + (d * 2) % 10
    return f"{letter}{''.join(map(str, digits))}{(10 - total % 10) % 10}"


def money(x):
    return f"{x:.2f}"


def series_number(issuer, n):
    return [f"FV26/{n:05d}", f"2026-A-{n:04d}", f"A2026/{n}", f"T-2026-{n:06d}"][issuer["style"]]


def gen_datetime(rng, day, month):
    offset = "+02:00" if 4 <= month <= 9 else "+01:00"
    return f"2026-{month:02d}-{day:02d}T{rng.randint(8, 19):02d}:{rng.randint(0, 59):02d}:{rng.randint(0, 59):02d}{offset}", f"{day:02d}-{month:02d}-2026"


class Calendar:
    """Issue dates that move forward through 2026, so a chain reads in time order."""

    def __init__(self, rng):
        self.rng, self.month, self.day = rng, rng.randint(1, 6), rng.randint(1, 10)

    def next(self):
        self.day += self.rng.randint(1, 9)
        if self.day > 28:
            self.month, self.day = min(12, self.month + 1), self.day - 28
        return self.day, self.month


def gen_alta(rng, issuer, n, prev_hash, prev_ref, cal):
    day, month = cal.next()
    when, date = gen_datetime(rng, day, month)
    kind_type = rng.choices(["F1", "F2", "R1"], weights=[6, 2, 1])[0]
    base = round(rng.uniform(20, 4000), 2)
    rate = rng.choice([21, 21, 21, 10, 4]) if kind_type != "F2" else 21
    if kind_type == "R1":
        base = -round(rng.uniform(10, 400), 2)
    tax = round(base * rate / 100, 2)
    number = series_number(issuer, n)
    client = rng.choice(["Acme Studio SL", "Lumen Foods SL", "Hotel Mirador SL", "Casa Verde S.Coop.", "Marta Pardo"])
    recipient = None if kind_type == "F2" else {"NombreRazon": client, "NIF": nif_person(rng) if client == "Marta Pardo" else nif_company(rng)}
    description = "Rectificacion de importe" if kind_type == "R1" else "Venta al contado" if kind_type == "F2" else rng.choice(["Servicios de consultoria", "Venta de mercaderias", "Diseno grafico", "Catering"])
    return dict(
        kind="alta",
        fields={"IDEmisorFactura": issuer["nif"], "NumSerieFactura": number, "FechaExpedicionFactura": date, "TipoFactura": kind_type,
                "CuotaTotal": money(tax), "ImporteTotal": money(base + tax), "Huella": prev_hash, "FechaHoraHusoGenRegistro": when},
        extra={"NombreRazonEmisor": issuer["name"], "DescripcionOperacion": description,
               "Destinatarios": recipient, "Desglose": {"TipoImpositivo": money(rate), "BaseImponibleOimporteNoSujeto": money(base), "CuotaRepercutida": money(tax)}},
        prev=prev_ref,
    )


def gen_anulacion(rng, issuer, target, prev_hash, prev_ref, cal):
    day, month = cal.next()
    when, _ = gen_datetime(rng, day, month)
    return dict(
        kind="anulacion",
        fields={"IDEmisorFacturaAnulada": issuer["nif"], "NumSerieFacturaAnulada": target["NumSerieFactura"], "FechaExpedicionFacturaAnulada": target["FechaExpedicionFactura"],
                "Huella": prev_hash, "FechaHoraHusoGenRegistro": when},
        extra={"NombreRazonEmisor": issuer["name"]},
        prev=prev_ref,
    )


def ref_of(rec):
    f = rec["fields"]
    if rec["kind"] == "alta":
        return {"IDEmisorFactura": f["IDEmisorFactura"], "NumSerieFactura": f["NumSerieFactura"], "FechaExpedicionFactura": f["FechaExpedicionFactura"], "Huella": huella(rec)}
    return {"IDEmisorFactura": f["IDEmisorFacturaAnulada"], "NumSerieFactura": f["NumSerieFacturaAnulada"], "FechaExpedicionFactura": f["FechaExpedicionFacturaAnulada"], "Huella": huella(rec)}


def issuer_for(rng):
    return {"nif": nif_company(rng), "name": rng.choice(["Estudio Norte SL", "Talleres Ruiz SL", "Panaderia La Espiga SL", "Clinica Dental Sur SL"]), "style": rng.randint(0, 3)}


# ---------- rendering: the record as sent to AEAT (XML) or as an API payload (JSON, keys shuffled) ----------

def _x(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render_xml(rec, pad=None):
    f, e = rec["fields"], rec["extra"]
    val = lambda k: f"  {f[k]} " if pad == k else _x(f[k])  # noqa: E731
    chain = (f"<sum1:RegistroAnterior><sum1:IDEmisorFactura>{rec['prev']['IDEmisorFactura']}</sum1:IDEmisorFactura><sum1:NumSerieFactura>{_x(rec['prev']['NumSerieFactura'])}</sum1:NumSerieFactura>"
             f"<sum1:FechaExpedicionFactura>{rec['prev']['FechaExpedicionFactura']}</sum1:FechaExpedicionFactura><sum1:Huella>{f['Huella']}</sum1:Huella></sum1:RegistroAnterior>"
             if rec["prev"] else "<sum1:PrimerRegistro>S</sum1:PrimerRegistro>")
    sistema = "<sum1:SistemaInformatico><sum1:NombreRazon>Cuadra</sum1:NombreRazon><sum1:IdSistemaInformatico>CU</sum1:IdSistemaInformatico><sum1:Version>0.2</sum1:Version></sum1:SistemaInformatico>"
    if rec["kind"] == "anulacion":
        return "\n".join([
            "<sum1:RegistroAnulacion>",
            "  <sum1:IDVersion>1.0</sum1:IDVersion>",
            f"  <sum1:IDFactura><sum1:IDEmisorFacturaAnulada>{val('IDEmisorFacturaAnulada')}</sum1:IDEmisorFacturaAnulada><sum1:NumSerieFacturaAnulada>{val('NumSerieFacturaAnulada')}</sum1:NumSerieFacturaAnulada><sum1:FechaExpedicionFacturaAnulada>{val('FechaExpedicionFacturaAnulada')}</sum1:FechaExpedicionFacturaAnulada></sum1:IDFactura>",
            f"  <sum1:Encadenamiento>{chain}</sum1:Encadenamiento>",
            f"  {sistema}",
            f"  <sum1:FechaHoraHusoGenRegistro>{val('FechaHoraHusoGenRegistro')}</sum1:FechaHoraHusoGenRegistro>",
            "</sum1:RegistroAnulacion>",
        ])
    dest = e["Destinatarios"]
    dest_xml = f"\n  <sum1:Destinatarios><sum1:IDDestinatario><sum1:NombreRazon>{_x(dest['NombreRazon'])}</sum1:NombreRazon><sum1:NIF>{dest['NIF']}</sum1:NIF></sum1:IDDestinatario></sum1:Destinatarios>" if dest else ""
    d = e["Desglose"]
    return "\n".join([
        "<sum1:RegistroAlta>",
        "  <sum1:IDVersion>1.0</sum1:IDVersion>",
        f"  <sum1:IDFactura><sum1:IDEmisorFactura>{val('IDEmisorFactura')}</sum1:IDEmisorFactura><sum1:NumSerieFactura>{val('NumSerieFactura')}</sum1:NumSerieFactura><sum1:FechaExpedicionFactura>{val('FechaExpedicionFactura')}</sum1:FechaExpedicionFactura></sum1:IDFactura>",
        f"  <sum1:NombreRazonEmisor>{_x(e['NombreRazonEmisor'])}</sum1:NombreRazonEmisor>",
        f"  <sum1:TipoFactura>{val('TipoFactura')}</sum1:TipoFactura>",
        f"  <sum1:DescripcionOperacion>{_x(e['DescripcionOperacion'])}</sum1:DescripcionOperacion>{dest_xml}",
        f"  <sum1:Desglose><sum1:DetalleDesglose><sum1:Impuesto>01</sum1:Impuesto><sum1:ClaveRegimen>01</sum1:ClaveRegimen><sum1:CalificacionOperacion>S1</sum1:CalificacionOperacion><sum1:TipoImpositivo>{d['TipoImpositivo']}</sum1:TipoImpositivo><sum1:BaseImponibleOimporteNoSujeto>{d['BaseImponibleOimporteNoSujeto']}</sum1:BaseImponibleOimporteNoSujeto><sum1:CuotaRepercutida>{d['CuotaRepercutida']}</sum1:CuotaRepercutida></sum1:DetalleDesglose></sum1:Desglose>",
        f"  <sum1:CuotaTotal>{val('CuotaTotal')}</sum1:CuotaTotal>",
        f"  <sum1:ImporteTotal>{val('ImporteTotal')}</sum1:ImporteTotal>",
        f"  <sum1:Encadenamiento>{chain}</sum1:Encadenamiento>",
        f"  {sistema}",
        f"  <sum1:FechaHoraHusoGenRegistro>{val('FechaHoraHusoGenRegistro')}</sum1:FechaHoraHusoGenRegistro>",
        "</sum1:RegistroAlta>",
    ])


def render_json(rec, rng, pad=None):
    f, e = rec["fields"], rec["extra"]
    v = lambda k: f"  {f[k]} " if pad == k else f[k]  # noqa: E731
    enc = {"RegistroAnterior": dict(rec["prev"], Huella=f["Huella"])} if rec["prev"] else {"PrimerRegistro": "S"}
    if rec["kind"] == "anulacion":
        body = {"IDVersion": "1.0", "IDFactura": {"IDEmisorFacturaAnulada": v("IDEmisorFacturaAnulada"), "NumSerieFacturaAnulada": v("NumSerieFacturaAnulada"), "FechaExpedicionFacturaAnulada": v("FechaExpedicionFacturaAnulada")},
                "Encadenamiento": enc, "SistemaInformatico": {"NombreRazon": "Cuadra", "IdSistemaInformatico": "CU", "Version": "0.2"}, "FechaHoraHusoGenRegistro": v("FechaHoraHusoGenRegistro")}
        wrapper = "RegistroAnulacion"
    else:
        body = {"IDVersion": "1.0", "IDFactura": {"IDEmisorFactura": v("IDEmisorFactura"), "NumSerieFactura": v("NumSerieFactura"), "FechaExpedicionFactura": v("FechaExpedicionFactura")},
                "NombreRazonEmisor": e["NombreRazonEmisor"], "TipoFactura": v("TipoFactura"), "DescripcionOperacion": e["DescripcionOperacion"],
                "Desglose": [e["Desglose"]], "CuotaTotal": v("CuotaTotal"), "ImporteTotal": v("ImporteTotal"), "Encadenamiento": enc,
                "SistemaInformatico": {"NombreRazon": "Cuadra", "IdSistemaInformatico": "CU", "Version": "0.2"}, "FechaHoraHusoGenRegistro": v("FechaHoraHusoGenRegistro")}
        if e["Destinatarios"]:
            body["Destinatarios"] = [e["Destinatarios"]]
        wrapper = "RegistroAlta"
    keys = list(body)
    rng.shuffle(keys)  # payload key order says nothing about the hash order
    return json.dumps({wrapper: {k: body[k] for k in keys}}, indent=2, ensure_ascii=False)


# ---------- rows ----------

def build_record_rows():
    """Single records: first and chained invoices, cancellations, XML and JSON, plus the official AEAT cancellation vector."""
    rows = []
    plan = [("alta", False, 3), ("alta", True, 5), ("anulacion", True, 5)]
    for kind, chained, seeds in plan:
        for fmt in ("xml", "json"):
            for seed in range(seeds):
                rng = random.Random(f"{kind}-{chained}-{fmt}-{seed}")
                issuer, cal = issuer_for(rng), Calendar(rng)
                first = gen_alta(rng, issuer, rng.randint(1, 900), "", None, cal)
                if kind == "alta" and not chained:
                    rec = first
                else:
                    middle = gen_alta(rng, issuer, rng.randint(901, 1800), huella(first), ref_of(first), cal)
                    rec = gen_alta(rng, issuer, rng.randint(1801, 2700), huella(middle), ref_of(middle), cal) if kind == "alta" else gen_anulacion(rng, issuer, middle["fields"], huella(middle), ref_of(middle), cal)
                pad = None
                if seed == seeds - 1 and (kind != "alta" or chained):
                    pad = "NumSerieFactura" if kind == "alta" else "NumSerieFacturaAnulada"
                text = render_xml(rec, pad) if fmt == "xml" else render_json(rec, rng, pad)
                rows.append(dict(case_id=f"{kind}-{'chained' if chained else 'first'}-{fmt}-s{seed}", kind=kind, chained=chained, fmt=fmt, padded=bool(pad),
                                 record=text, record_json=json.dumps(rec), truth_input=hash_input(rec), truth_hash=huella(rec)))
    official = dict(AEAT_ANUL, extra={"NombreRazonEmisor": "Empresa de prueba"}, prev={"IDEmisorFactura": "89890001K", "NumSerieFactura": "12345678/G33", "FechaExpedicionFactura": "01-01-2024", "Huella": AEAT_ANUL["fields"]["Huella"]})
    rows.append(dict(case_id="aeat-official-anulacion-xml", kind="anulacion", chained=True, fmt="xml", padded=False, record=render_xml(official),
                     record_json=json.dumps(official), truth_input=hash_input(official), truth_hash=huella(official)))
    return rows


TAMPERS = ["none", "amount", "link", "delete", "recompute"]


def chain_view(rec):
    """Flat record as an auditor sees it: hash fields, the stored previous Huella and the record's own stored Huella."""
    f = rec["fields"]
    if rec["kind"] == "alta":
        out = {"type": "RegistroAlta", **{k: f[k] for k in ALTA_FIELDS if k != "Huella"}}
    else:
        out = {"type": "RegistroAnulacion", **{k: f[k] for k in ANUL_FIELDS if k != "Huella"}}
    out["PreviousHuella"] = f["Huella"]
    out["Huella"] = rec["stored"]
    return out


def number_of(view):
    return view.get("NumSerieFactura") or view.get("NumSerieFacturaAnulada")


def first_broken(views):
    """Independent verifier: the first record whose own Huella or whose link to the previous record fails."""
    prev = ""
    for v in views:
        kind = "alta" if v["type"] == "RegistroAlta" else "anulacion"
        fields = {k: (v["PreviousHuella"] if k == "Huella" else v[k]) for k in field_order(kind)}
        if v["PreviousHuella"] != prev or sha256_upper(hash_input({"kind": kind, "fields": fields})) != v["Huella"]:
            return number_of(v)
        prev = v["Huella"]
    return "INTACT"


def build_chain_rows():
    rows = []
    for length in (4, 6):
        for tamper in TAMPERS:
            for seed in range(2):
                rows.append(chain_row(length, tamper, seed))
    return rows


def chain_row(length, tamper, seed):
    # A cancellation repeats its invoice's number; retry until the expected answer names exactly one record.
    for attempt in range(50):
        rng = random.Random(f"chain-{length}-{tamper}-{seed}-{attempt}")
        issuer, cal = issuer_for(rng), Calendar(rng)
        recs, prev = [], None
        for i in range(length + (1 if tamper == "delete" else 0)):
            ph, pr = (huella(prev), ref_of(prev)) if prev else ("", None)
            altas = [r for r in recs if r["kind"] == "alta"]
            if i == 3 and altas and rng.random() < 0.6:
                rec = gen_anulacion(rng, issuer, rng.choice(altas)["fields"], ph, pr, cal)
            else:
                rec = gen_alta(rng, issuer, 100 + i * 7 + rng.randint(0, 5), ph, pr, cal)
            rec["stored"] = huella(rec)
            recs.append(rec)
            prev = rec
        k = rng.randint(1, length - 2)
        expected = "INTACT"
        if tamper == "amount" or tamper == "recompute":
            while recs[k]["kind"] != "alta":
                k -= 1
            f = recs[k]["fields"]
            f["ImporteTotal"] = money(float(f["ImporteTotal"]) + rng.choice([100, 250, 1000]))
            if tamper == "recompute":
                recs[k]["stored"] = huella(recs[k])  # the forger recomputes this record's own Huella...
                expected = number_of(chain_view(recs[k + 1]))  # ...so only the next link exposes it
            else:
                expected = number_of(chain_view(recs[k]))
        elif tamper == "link":
            recs[k]["fields"]["Huella"] = sha256_upper(f"forged-{seed}-{k}")
            expected = number_of(chain_view(recs[k]))
        elif tamper == "delete":
            del recs[k]
            expected = number_of(chain_view(recs[k]))
        views = [chain_view(r) for r in recs]
        if [number_of(v) for v in views].count(expected) <= 1:
            return dict(case_id=f"chain{length}-{tamper}-s{seed}", length=len(views), tamper=tamper, chain=json.dumps(views, indent=1), expected=expected)
    raise RuntimeError("no unambiguous chain")


# ---------- prompts ----------

def record_block(row):
    return f"Record ({'XML as sent to AEAT' if row['fmt'] == 'xml' else 'JSON payload'}):\n```{row['fmt']}\n{row['record']}\n```"


def prompt_input(row):
    return f"{SPEC}\n\n{record_block(row)}\n\nWrite the exact text that is hashed to compute this record's Huella. Reply with that text only, on one line."


def prompt_hash_tool(row):
    return f"{SPEC}\n\n{record_block(row)}\n\nCompute this record's Huella. You can use the sha256_hex tool. Reply with the 64-character uppercase hexadecimal Huella only."


def prompt_hash_honesty(row):
    return (f"{SPEC}\n\n{record_block(row)}\n\nCompute this record's Huella. You have no tools. If you cannot compute the SHA-256 exactly, reply exactly UNKNOWN. "
            "Otherwise reply with the 64-character uppercase hexadecimal Huella only.")


def prompt_chain(row):
    return (f"{SPEC}\n\nBelow is a VeriFactu chain of {row['length']} records in issue order, as JSON. For each record, PreviousHuella is the previous record's Huella "
            "(empty for the first record) and Huella is the fingerprint stored for the record itself.\n"
            "A record is broken if its stored Huella is not the SHA-256 of its own text, or if its PreviousHuella differs from the stored Huella of the record before it.\n"
            f"```json\n{row['chain']}\n```\n\nYou can use the sha256_hex tool. Which is the FIRST broken record? Reply with its invoice number (NumSerieFactura or NumSerieFacturaAnulada) only, or INTACT if every record verifies.")


# ---------- answer extraction and grading ----------

def strip_wrappers(text):
    t = str(text or "").strip()
    t = re.sub(r"^```[a-zA-Z]*\s*|\s*```$", "", t).strip()
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    pick = [ln for ln in lines if "=" in ln and "&" in ln]
    t = (pick[-1] if pick else (lines[-1] if lines else "")).strip()
    if len(t) >= 2 and t[0] == t[-1] and t[0] in "`'\"":
        t = t[1:-1]
    return t


def extract_hex(text):
    found = HEX64.findall(str(text or ""))
    return found[-1] if found else None


def parse_pairs(text):
    pairs = []
    for part in text.split("&"):
        if "=" not in part:
            return None
        k, v = part.split("=", 1)
        pairs.append((k, v))
    return pairs


def diagnose_input(answer, row):
    """Category of a hash-input answer: correct, or the first kind of mistake it makes."""
    truth = row["truth_input"]
    a = strip_wrappers(answer)
    start = a.find("IDEmisor")
    if start > 0 and a[:start].rstrip().endswith(":"):
        a = a[start:]  # "Text: IDEmisorFactura=..." is a wrapper, not a spec mistake
    if a.endswith(".") and not truth.endswith("."):
        a = a[:-1]
    if not a:
        return "no-answer"
    if a == truth:
        return "correct"
    rec = json.loads(row["record_json"])
    if a.replace(" ", "") == truth.replace(" ", ""):
        return "not-trimmed" if row["padded"] else "extra-spaces"
    pa, pt = parse_pairs(a), parse_pairs(truth)
    if pa is None:
        return "malformed"
    ka, kt = [k.strip() for k, _ in pa], [k for k, _ in pt]
    if ka != kt:
        if sorted(ka) == sorted(kt):
            return "wrong-order"
        if set(kt) - set(ka) and rec["kind"] == "anulacion" and {"IDEmisorFactura", "NumSerieFactura"} & set(ka):
            return "wrong-field-names"
        if set(ka) - set(kt) and not set(kt) - set(ka):
            return "extra-fields"
        if "Huella" not in ka and rec["prev"] is None:
            return "dropped-empty-huella"
        return "missing-or-renamed-fields"
    va, vt = dict(pa), dict(pt)
    wrong = [k for k in kt if va[k] != vt[k]]
    prev = rec.get("prev") or {}
    if "Huella" in wrong:
        if vt["Huella"] and not va["Huella"]:
            return "dropped-previous-huella"
        return "wrong-previous-huella"
    if any(va[k] in (prev.get("NumSerieFactura"), prev.get("FechaExpedicionFactura")) for k in wrong):
        return "took-previous-record-value"
    recipient = (rec.get("extra") or {}).get("Destinatarios") or {}
    if any(va[k] == recipient.get("NIF") for k in wrong):
        return "took-recipient-nif"
    if any(va[k].strip() == vt[k] for k in wrong):
        return "not-trimmed"
    return "wrong-value"


def classify_hash(answer, row, calls):
    """Category of a fingerprint answer, using the sha256_hex calls the model made (empty when it had no tool)."""
    text = str(answer or "").strip()
    if text.upper().rstrip(".") == "UNKNOWN":
        return "abstained"
    h = extract_hex(text)
    if h is None:
        return "no-answer"
    if h == row["truth_hash"]:
        return "correct"
    if h.upper() == row["truth_hash"]:
        return "lowercase"
    hashed = [c for c in calls if c.get("output") == h.upper()]
    if hashed:
        return "hashed-wrong-text:" + diagnose_input(hashed[-1]["input"], row)
    if any(c.get("input", "").strip() == row["truth_input"] for c in calls):
        return "hashed-right-text-quoted-other"
    return "fabricated" if not calls else "quoted-unrelated-hex"


def chain_answer(answer, row):
    """The record number (or INTACT) the answer names: the last line, wrappers and punctuation removed, then any
    invoice number of this chain mentioned in it (a sentence such as "The first broken record is X." still counts)."""
    lines = [ln.strip() for ln in str(answer or "").strip().strip("`").splitlines() if ln.strip()]
    text = re.sub(r"^[\s`'\"*]+|[\s`'\".*]+$", "", lines[-1] if lines else "")
    numbers = sorted({number_of(v) for v in json.loads(row["chain"])}, key=len, reverse=True)
    if text in numbers or text.upper() == "INTACT":
        return text.upper() if text.upper() == "INTACT" else text
    named = [n for n in numbers if n in text]
    if len(named) == 1:
        return named[0]
    if not named and re.search(r"\bINTACT\b", text, re.IGNORECASE):
        return "INTACT"
    return text


def classify_chain(answer, row):
    text = chain_answer(answer, row)
    if not text:
        return "no-answer"
    exp = row["expected"]
    if text == "INTACT":
        return "correct" if exp == "INTACT" else "missed-tamper"
    if text == exp:
        return "correct"
    return "false-alarm" if exp == "INTACT" else "wrong-record"


# ---------- calling the model ----------

def usage_of(chat):
    try:
        u = chat.usage
        cost = u.total_cost_nanodollars
        return dict(in_tokens=u.input_tokens, out_tokens=u.output_tokens, cost_usd=None if cost is None else cost / 1e9)
    except Exception:
        return dict(in_tokens=None, out_tokens=None, cost_usd=None)


def make_sha_tool(log):
    def sha256_hex(text: str) -> str:
        """Return the SHA-256 of `text` (encoded as UTF-8) as 64 uppercase hexadecimal characters."""
        out = sha256_upper(str(text))
        log.append({"input": str(text), "output": out})
        return out
    return sha256_hex


RETRY_BASE_SECONDS = float(os.environ.get("VF_RETRY_BASE_SECONDS", "5"))  # tests lower it to run fast
TRANSIENT_ERRORS = {"RateLimitError", "APIConnectionError", "APITimeoutError", "InternalServerError", "ServiceUnavailableError"}


class ModelUnavailable(RuntimeError):
    """The model proxy kept failing for reasons unrelated to the answer: the case is errored, not wrong."""


def ask(kbench, llm, prompt, with_tool=False, attempts=10):
    """One fresh chat per attempt; retries transient proxy errors. Returns (answer, tool_calls, error, usage).
    Raises ModelUnavailable when every attempt hit a transient error, so the case counts as errored instead of wrong."""
    for attempt in range(attempts):
        log, chat = [], None
        kw = {"extra_api_params": {"max_completion_tokens": MAX_OUTPUT_TOKENS}}
        if with_tool:
            kw["tools"] = [make_sha_tool(log)]
        try:
            with kbench.chats.new(f"attempt-{attempt}") as chat:
                answer = llm.prompt(prompt, **kw)
                return answer, log, "", usage_of(chat)
        except Exception as e:  # noqa: BLE001
            name = type(e).__name__
            if name not in TRANSIENT_ERRORS:
                return None, log, f"{name}: {str(e)[:300]}", usage_of(chat)
            if attempt == attempts - 1:
                raise ModelUnavailable(f"{name} after {attempts} attempts: {str(e)[:200]}") from e
            time.sleep(min(90, RETRY_BASE_SECONDS * 2 ** attempt) + random.random() * min(1.0, RETRY_BASE_SECONDS))


def summarize(runs, total, label, key="category"):
    """Score = correct / answered. Errored cases (proxy failures) are reported, not counted as wrong. A run where
    no case was answered fails, so a 0 caused by an outage never reaches the leaderboard."""
    import pandas as pd
    try:
        done = runs.completed_runs.as_dataframe()
    except KeyError:  # kaggle_benchmarks cannot build the frame when no case completed
        done = []
    results = pd.DataFrame(list(done["result"])) if len(done) else pd.DataFrame(columns=["case_id", key, "correct"])
    os.makedirs(OUT_DIR, exist_ok=True)
    results.to_json(f"{OUT_DIR}/rows-{label}.json", orient="records")
    answered = len(results)
    correct = int(results["correct"].sum()) if answered else 0
    print(f"[{label}] correct {correct} of {answered} answered (errored {total - answered} of {total})")
    if answered:
        print(results[key].value_counts().to_string())
    if not answered:
        raise RuntimeError(f"[{label}] no case answered: the model proxy failed on all {total}. Re-run later.")
    return correct / answered


RECORD_ROWS = build_record_rows()
CHAIN_ROWS = build_chain_rows()
# ---- end shared ----

# %%
@kbench.task(name="vf-hash-input")
def vf_hash_input(llm) -> float:
    """Share of records for which the model writes the exact VeriFactu hash input text."""
    runs = vf_hash_input_row.evaluate(llm=[llm], evaluation_data=pd.DataFrame(RECORD_ROWS), n_jobs=4, on_failure="continue")
    return summarize(runs, len(RECORD_ROWS), "hash-input")


# %%
@kbench.task(name="vf-hash-input-row", store_task=False)
def vf_hash_input_row(llm, case_id, kind, chained, fmt, padded, record, record_json, truth_input, truth_hash) -> dict:
    row = dict(case_id=case_id, kind=kind, chained=bool(chained), fmt=fmt, padded=bool(padded), record=record, record_json=record_json, truth_input=truth_input, truth_hash=truth_hash)
    answer, _, error, usage = ask(kbench, llm, prompt_input(row))
    category = "no-answer" if answer is None else diagnose_input(answer, row)
    correct = category == "correct"
    kbench.assertions.assert_true(correct, expectation=f"{case_id}: exact hash input")
    return dict(case_id=case_id, kind=kind, chained=bool(chained), fmt=fmt, padded=bool(padded), category=category, correct=correct,
                answer=str(answer)[:700], error=error, **usage)


vf_hash_input.run(kbench.llm)

# %%
# Keep only the scoring task's files: the leaderboard shows one task per notebook.
# %choose vf_hash_input
