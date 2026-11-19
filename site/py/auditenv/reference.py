"""Независимая сверка по ОТКРЫТЫМ записям (без truth/provenance/seed).

Используется закрытой проверкой: эталон должен совпадать с тем, что реально следует из записей
по правилам policy.json. Это доказывает, что ошибки разрешимы и что в книгах нет случайных
(незаявленных) расхождений.
"""
from __future__ import annotations

import json
from collections import defaultdict
from decimal import Decimal

from . import money
from .generator import ACC_AR, ACC_CASH, ACC_OPEN, ACC_REV, ACC_SUSP


def _index(public: dict):
    m = public["manifest"]
    tz = m["timezone"]
    base = m["base_currency"]
    fx = {(r["source_currency"], r["date"]): Decimal(r["rate"]) for r in public["fx"]}
    invs = {i["invoice_id"]: i for i in public["invoices"]}
    pays = {p["payment_id"]: p for p in public["payments"]}
    return m, tz, base, fx, invs, pays


def _rate(fx, base, cur, d):
    return Decimal(1) if cur == base else fx[(cur, d)]


def fx_id(d: str, cur: str, base: str) -> str:
    return f"fx:{d}:{cur}:{base}"


def audit(public: dict) -> list[dict]:
    m, tz, base, fx, invs, pays = _index(public)
    p_start, p_end = m["period_start"], m["period_end"]
    ledger = public["ledger"]
    by_inv = defaultdict(list)    # строки без payment_id
    by_pay = defaultdict(list)
    for r in ledger:
        if r["payment_id"]:
            by_pay[r["payment_id"]].append(r)
        elif r["invoice_id"]:
            by_inv[r["invoice_id"]].append(r)
    findings: list[dict] = []

    def ldate(ts):
        return money.local_date(ts, tz).isoformat()

    # ------------------------------------------------ счета, проведённые в периоде
    posted = {}
    for inv_id, rows in by_inv.items():
        accs = {r["account"] for r in rows}
        if ACC_OPEN in accs:
            continue
        ar = [r for r in rows if r["account"] == ACC_AR and r["debit_minor"] > 0]
        rev = [r for r in rows if r["account"] == ACC_REV]
        if ar:
            posted[inv_id] = (ar[0], rev[0] if rev else None)

    # duplicate_invoice
    groups = defaultdict(list)
    for inv_id in posted:
        inv = invs[inv_id]
        key = (inv["entity_id"], inv["currency"], ldate(inv["issued_at"]),
               json.dumps(inv["line_items"], sort_keys=True))
        groups[key].append(inv)
    for key, items in groups.items():
        if len(items) < 2:
            continue
        items.sort(key=lambda i: (money.parse_iso(i["issued_at"]).timestamp(), i["invoice_id"]))
        orig = items[0]
        for dup in items[1:]:
            ar, rev = posted[dup["invoice_id"]]
            findings.append({"type": "duplicate_invoice",
                             "affected_ids": sorted([orig["invoice_id"], dup["invoice_id"]]),
                             "claimed_amount_minor": dup["total_minor"], "currency": dup["currency"],
                             "evidence_ids": [orig["doc_id"], dup["doc_id"], ar["row_id"]],
                             "explanation": "identical invoice posted twice on the same local date"})

    # period_cutoff_error + fx_conversion_error (счета)
    for inv_id, (ar, rev) in posted.items():
        inv = invs[inv_id]
        d = ldate(inv["issued_at"])
        if not (p_start <= d <= p_end):
            findings.append({"type": "period_cutoff_error", "affected_ids": [inv_id],
                             "claimed_amount_minor": inv["total_minor"], "currency": inv["currency"],
                             "evidence_ids": [inv["doc_id"], ar["row_id"]],
                             "explanation": f"invoice local date {d} outside period but posted"})
        if inv["currency"] != base:
            correct = money.convert_minor(inv["total_minor"], inv["currency"], base, _rate(fx, base, inv["currency"], d))
            if abs(ar["debit_minor"] - correct) > 1:
                findings.append({"type": "fx_conversion_error", "affected_ids": [inv_id],
                                 "claimed_amount_minor": abs(ar["debit_minor"] - correct), "currency": base,
                                 "evidence_ids": [inv["doc_id"], ar["row_id"], fx_id(d, inv["currency"], base)],
                                 "explanation": "posted base amount differs from policy-rate conversion"})

    # платежи
    for pay_id, rows in by_pay.items():
        p = pays[pay_id]
        d = ldate(p["timestamp"])
        cash = [r for r in rows if r["account"] == ACC_CASH]
        if not cash:
            continue
        cash = cash[0]
        if not (p_start <= d <= p_end):
            findings.append({"type": "period_cutoff_error", "affected_ids": [pay_id],
                             "claimed_amount_minor": p["amount_minor"], "currency": p["currency"],
                             "evidence_ids": [p["doc_id"], cash["row_id"]],
                             "explanation": f"receipt local date {d} outside period but posted"})
        if p["currency"] != base:
            correct = money.convert_minor(p["amount_minor"], p["currency"], base, _rate(fx, base, p["currency"], d))
            booked = cash["debit_minor"] - cash["credit_minor"]
            if abs(booked - correct) > 1:
                findings.append({"type": "fx_conversion_error", "affected_ids": [pay_id],
                                 "claimed_amount_minor": abs(booked - correct), "currency": base,
                                 "evidence_ids": [p["doc_id"], cash["row_id"], fx_id(d, p["currency"], base)],
                                 "explanation": "cash posted with a non-policy rate"})
        susp = [r for r in rows if r["account"] == ACC_SUSP]
        for ref in p["invoice_refs"]:
            inv = invs.get(ref["invoice_id"])
            if inv is None:
                continue
            a = ref["amount_minor"]
            rate = _rate(fx, base, p["currency"], ldate(inv["issued_at"]))
            expected = money.convert_minor(a, p["currency"], base, rate)
            actual = sum(r["credit_minor"] - r["debit_minor"] for r in rows
                         if r["account"] == ACC_AR and r["invoice_id"] == ref["invoice_id"])
            if actual >= expected - 1:
                continue
            # восстановить применённую сумму в валюте платежа (монотонный бинарный поиск)
            lo, hi = 0, a
            while lo < hi:
                mid = (lo + hi) // 2
                if money.convert_minor(mid, p["currency"], base, rate) < actual:
                    lo = mid + 1
                else:
                    hi = mid
            u = a - lo
            ev = [p["doc_id"]] + ([susp[0]["row_id"]] if susp else [])
            if u < a:
                ev += [inv["doc_id"]] + [r["row_id"] for r in rows
                                          if r["account"] == ACC_AR and r["invoice_id"] == ref["invoice_id"]][:1]
            findings.append({"type": "missing_or_partial_allocation", "affected_ids": sorted([pay_id, ref["invoice_id"]]),
                             "claimed_amount_minor": u, "currency": p["currency"], "evidence_ids": ev,
                             "explanation": "invoice_refs amount not fully credited to receivables"})
    findings.sort(key=lambda f: (f["type"], f["affected_ids"]))
    return findings


def balance_check(public: dict) -> dict:
    """Равенства по открытому журналу: всего и по каждому документу/платежу."""
    groups = defaultdict(lambda: [0, 0])
    td = tc = 0
    for r in public["ledger"]:
        td += r["debit_minor"]
        tc += r["credit_minor"]
        g = ("p:" + r["payment_id"]) if r["payment_id"] else ("i:" + r["invoice_id"]) if r["invoice_id"] else \
            f"e:{r['timestamp']}:{r['entity_id']}"
        groups[g][0] += r["debit_minor"]
        groups[g][1] += r["credit_minor"]
    bad = [g for g, (d, c) in groups.items() if d != c]
    return {"balanced": td == tc and not bad, "unbalanced": bad[:10], "total_debit": td, "total_credit": tc}
