"""Проверки данных/эталона и парные проверки (используются командой check и тестами)."""
from __future__ import annotations

from decimal import Decimal

from . import money
from .config import canonical_json, deep_merge
from .generator import ACC_AR, ACC_CASH, ACC_REV, ACC_SUSP, generate_episode
from .matcher import score
from .reference import audit, balance_check


def _lookup(public: dict):
    idx = {}
    for t in ("ledger",):
        for r in public[t]:
            idx[r["row_id"]] = ("row", r)
    for i in public["invoices"]:
        idx[i["doc_id"]] = ("inv", i)
    for p in public["payments"]:
        idx[p["doc_id"]] = ("pay", p)
    for f in public["fx"]:
        idx[f"fx:{f['date']}:{f['source_currency']}:{f['target_currency']}"] = ("fx", f)
    return idx


def evidence_sufficient(issue: dict, public: dict) -> tuple[bool, str]:
    """Пересчёт расхождения ТОЛЬКО по записям из первого набора доказательств."""
    m = public["manifest"]
    tz, base = m["timezone"], m["base_currency"]
    idx = _lookup(public)
    recs = []
    for e in issue["evidence_sets"][0]:
        if e not in idx:
            return False, f"evidence id not found: {e}"
        recs.append(idx[e])
    rows = [r for k, r in recs if k == "row"]
    invs = [r for k, r in recs if k == "inv"]
    pays = [r for k, r in recs if k == "pay"]
    fxs = [r for k, r in recs if k == "fx"]
    t, amt, tol = issue["type"], issue["expected_amount_minor"], issue["tolerance_minor"]
    ld = lambda ts: money.local_date(ts, tz).isoformat()
    if t == "duplicate_invoice":
        a, b = invs
        same = (a["entity_id"], a["currency"], ld(a["issued_at"]), canonical_json(a["line_items"])) == \
               (b["entity_id"], b["currency"], ld(b["issued_at"]), canonical_json(b["line_items"]))
        posted = rows and rows[0]["invoice_id"] in {a["invoice_id"], b["invoice_id"]} and \
            rows[0]["account"] in (ACC_AR, ACC_REV)
        return bool(same and posted and a["total_minor"] == amt), "duplicate"
    if t == "period_cutoff_error":
        doc = (invs or pays)[0]
        d = ld(doc.get("issued_at") or doc.get("timestamp"))
        outside = not (m["period_start"] <= d <= m["period_end"])
        r = rows[0]
        inside = m["period_start"] <= ld(r["timestamp"]) <= m["period_end"]
        ref = r["invoice_id"] if invs else r["payment_id"]
        bid = doc.get("invoice_id") or doc.get("payment_id")
        total = doc.get("total_minor", doc.get("amount_minor"))
        return bool(outside and inside and ref == bid and total == amt), "cutoff"
    if t == "fx_conversion_error":
        doc = (invs or pays)[0]
        f = fxs[0]
        d = ld(doc.get("issued_at") or doc.get("timestamp"))
        if f["date"] != d or f["source_currency"] != doc["currency"]:
            return False, "fx row date/currency"
        total = doc.get("total_minor", doc.get("amount_minor"))
        correct = money.convert_minor(total, doc["currency"], base, Decimal(f["rate"]))
        r = rows[0]
        booked = r["debit_minor"] or r["credit_minor"]
        return abs(abs(booked - correct) - amt) <= tol, "fx"
    if t == "missing_or_partial_allocation":
        p = pays[0]
        inv_ids = set(issue["affected_ids"]) - {p["payment_id"]}
        ref = [x for x in p["invoice_refs"] if x["invoice_id"] in inv_ids]
        susp = [r for r in rows if r["account"] == ACC_SUSP and r["payment_id"] == p["payment_id"]]
        if not ref or not susp:
            return False, "alloc refs/suspense"
        a = ref[0]["amount_minor"]
        ar = [r for r in rows if r["account"] == ACC_AR]
        if not ar:                           # не разнесено совсем
            return amt == a, "alloc missing"
        inv = invs[0]
        fxr = Decimal(1) if p["currency"] == base else None
        if fxr is None:
            key = (p["currency"], ld(inv["issued_at"]))
            fxr = {(x["source_currency"], x["date"]): Decimal(x["rate"]) for x in public["fx"]}[key]
        applied_base = ar[0]["credit_minor"]
        lo, hi = 0, a
        while lo < hi:
            mid = (lo + hi) // 2
            if money.convert_minor(mid, p["currency"], base, fxr) < applied_base:
                lo = mid + 1
            else:
                hi = mid
        return abs((a - lo) - amt) <= tol, "alloc partial"
    return False, "unknown type"


def verify_episode(ep) -> dict:
    """Корректность эпизода: равенства до ошибки, объявленное расхождение после, достаточность доказательств."""
    pub, truth = ep.public, ep.truth
    problems = []
    if not ep.provenance["balance_before_injection"]["balanced"]:
        problems.append("ledger unbalanced before injection")
    if not balance_check(pub)["balanced"]:
        problems.append("ledger unbalanced after injection")
    ref = {(f["type"], tuple(f["affected_ids"])): f for f in audit(pub)}
    exp = {(i["type"], tuple(i["affected_ids"])): i for i in truth["issues"]}
    if set(ref) != set(exp):
        problems.append(f"reference audit mismatch: missing={sorted(set(exp) - set(ref))} extra={sorted(set(ref) - set(exp))}")
    for k in set(ref) & set(exp):
        if abs(ref[k]["claimed_amount_minor"] - exp[k]["expected_amount_minor"]) > exp[k]["tolerance_minor"]:
            problems.append(f"amount mismatch {k}")
    for i in truth["issues"]:
        ok, why = evidence_sufficient(i, pub)
        if not ok:
            problems.append(f"evidence insufficient {i['issue_id']} ({why})")
    if score({"episode_id": truth["episode_id"], "findings": audit(pub)}, truth, pub, 0)["f1"] != 1.0:
        problems.append("reference findings do not score F1=1")
    return {"ok": not problems, "problems": problems, "issues": len(truth["issues"]), "clean": truth["clean"]}


def paired_check(seed: int, cfg: dict) -> dict:
    """Повтор seed точен; смена ID и порядка сохраняет эталон (с новыми ID) и награду oracle."""
    from .policies import Oracle
    from .runner import run_inprocess
    a1 = generate_episode(seed, deep_merge(cfg, {"transform": {"id_salt": "A", "order": "time"}}))
    a2 = generate_episode(seed, deep_merge(cfg, {"transform": {"id_salt": "A", "order": "time"}}))
    b = generate_episode(seed, deep_merge(cfg, {"transform": {"id_salt": "B", "order": "shuffled"}}))
    problems = []
    if canonical_json([a1.public, a1.truth]) != canonical_json([a2.public, a2.truth]):
        problems.append("same seed/config not reproducible")
    inv_a = {v: k for k, v in a1.id_map.items()}

    def remap(issue):
        f = lambda x: x if x.startswith("fx:") else b.id_map[inv_a[x]]
        return (issue["type"], tuple(sorted(f(x) for x in issue["affected_ids"])), issue["expected_amount_minor"],
                issue["currency"], tuple(tuple(sorted(f(x) for x in es)) for es in issue["evidence_sets"]))
    ta = sorted(remap(i) for i in a1.truth["issues"])
    tb = sorted((i["type"], tuple(i["affected_ids"]), i["expected_amount_minor"], i["currency"],
                 tuple(tuple(es) for es in i["evidence_sets"])) for i in b.truth["issues"])
    if ta != tb:
        problems.append("truth not preserved under ID/order transform")
    if [r["row_id"] for r in a1.public["ledger"]][:5] == [r["row_id"] for r in b.public["ledger"]][:5]:
        problems.append("transform did not change IDs/order")
    # одинаковые действия -> одинаковые переходы и награды
    _, r1 = run_inprocess(Oracle(a1.truth), seed, None, episode=a1)
    _, r2 = run_inprocess(Oracle(a2.truth), seed, None, episode=a2)
    _, rb = run_inprocess(Oracle(b.truth), seed, None, episode=b)
    if not (r1["reward"] == r2["reward"] == rb["reward"]):
        problems.append("oracle reward differs")
    return {"ok": not problems, "problems": problems}
