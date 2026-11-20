"""Базовые политики для проверки и сравнения.

Интерфейс: policy.begin(observation, info); policy.act(observation) -> action (dict).
Политика видит только наблюдения. Oracle — исключение: его создаёт оценщик, передавая эталон.
"""
from __future__ import annotations

import json
import random
from collections import defaultdict
from decimal import Decimal

from . import money


def submit_action(episode_id: str, findings: list[dict]) -> dict:
    return {"name": "submit", "args": {"findings": {"episode_id": episode_id, "findings": findings}}}


class Policy:
    name = "base"

    def begin(self, obs: dict, info: dict):
        self.episode_id = obs["manifest"]["episode_id"]
        self.manifest = obs["manifest"]

    def act(self, obs: dict) -> dict:
        raise NotImplementedError


# ---------------------------------------------------------------------------- 1. случайный исследователь

class RandomExplorer(Policy):
    name = "random_explorer"
    TYPES = ["duplicate_invoice", "missing_or_partial_allocation", "fx_conversion_error", "period_cutoff_error"]

    def __init__(self, seed: int = 0):
        self.seed = seed

    def begin(self, obs, info):
        super().begin(obs, info)
        self.rng = random.Random(f"{self.seed}:{self.episode_id}")
        self.budget = self.rng.randint(3, 40)
        self.seen_ids: list[str] = []
        self.seen_docs: list[str] = []
        self.n = 0

    def _absorb(self, obs):
        res = (obs or {}).get("result") or {}
        recs = res.get("records") or ([res["record"]] if "record" in res else [])
        if "document" in res:
            recs.append(res["document"])
        for r in recs:
            for k in ("row_id", "invoice_id", "payment_id", "fx_id"):
                if r.get(k):
                    self.seen_ids.append(r[k])
            if r.get("doc_id"):
                self.seen_docs.append(r["doc_id"])

    def act(self, obs):
        self._absorb(obs)
        self.n += 1
        r = self.rng
        if self.n > self.budget:
            findings = []
            if r.random() < 0.5 and self.seen_ids:
                for _ in range(r.randint(1, 3)):
                    findings.append({"type": r.choice(self.TYPES), "affected_ids": [r.choice(self.seen_ids)],
                                     "claimed_amount_minor": r.randint(1, 100000),
                                     "currency": self.manifest["base_currency"],
                                     "evidence_ids": r.sample(self.seen_ids, k=min(3, len(self.seen_ids))),
                                     "explanation": "random guess"})
            return submit_action(self.episode_id, findings)
        roll = r.random()
        table = r.choice(["ledger", "invoices", "payments", "fx"])
        if roll < 0.5 or not self.seen_ids:
            total = self.manifest["counts"][table]
            return {"name": "list_records", "args": {"table": table, "cursor": f"{table}@{r.randint(0, max(0, total - 1))}",
                                                       "limit": r.randint(1, 50)}}
        if roll < 0.7:
            return {"name": "get_record", "args": {"table": table, "id": r.choice(self.seen_ids)}}
        if roll < 0.9 and self.seen_docs:
            return {"name": "get_document", "args": {"doc_id": r.choice(self.seen_docs)}}
        return {"name": "calculator", "args": {"expression": f"{r.randint(1, 999)} * {r.randint(1, 99)} / 7"}}


# ---------------------------------------------------------------------------- 2. простой алгоритм сверки

class SimpleReconciler(Policy):
    """Читает все счета, платежи и журнал; сверяет «в лоб».

    Сознательно наивен: даты берёт из строки времени как есть (без перевода в пояс компании),
    курсы не проверяет, частичные иностранные разнесения не пересчитывает.
    """
    name = "simple_reconciler"
    ORDER = ("invoices", "payments", "ledger")

    def begin(self, obs, info):
        super().begin(obs, info)
        self.data = {t: [] for t in self.ORDER}
        self.queue = list(self.ORDER)
        self.cursor = None
        self.pending = None

    def act(self, obs):
        res = (obs or {}).get("result") or {}
        if self.pending and res.get("table") == self.pending:
            self.data[self.pending] += res["records"]
            self.cursor = res["next_cursor"]
            if self.cursor is None:
                self.queue.pop(0)
        if self.queue:
            self.pending = self.queue[0]
            return {"name": "list_records", "args": {"table": self.pending, "cursor": self.cursor, "limit": 50}}
        return submit_action(self.episode_id, self.reconcile())

    def reconcile(self) -> list[dict]:
        m = self.manifest
        ps, pe = m["period_start"], m["period_end"]
        invs = {i["invoice_id"]: i for i in self.data["invoices"]}
        pays = {p["payment_id"]: p for p in self.data["payments"]}
        inv_rows, pay_rows = defaultdict(list), defaultdict(list)
        for r in self.data["ledger"]:
            if r["payment_id"]:
                pay_rows[r["payment_id"]].append(r)
            elif r["invoice_id"]:
                inv_rows[r["invoice_id"]].append(r)
        out = []
        posted = {}
        for iid, rows in inv_rows.items():
            if any(r["account"].startswith("3000") for r in rows):
                continue
            ar = [r for r in rows if r["account"].startswith("1200")]
            if ar and iid in invs:
                posted[iid] = ar[0]
        seen = {}
        for iid in sorted(posted, key=lambda x: invs[x]["issued_at"]):
            i = invs[iid]
            key = (i["entity_id"], i["currency"], i["total_minor"], i["issued_at"][:10])
            if key in seen:
                o = invs[seen[key]]
                out.append({"type": "duplicate_invoice", "affected_ids": [o["invoice_id"], iid],
                            "claimed_amount_minor": i["total_minor"], "currency": i["currency"],
                            "evidence_ids": [o["doc_id"], i["doc_id"], posted[iid]["row_id"]],
                            "explanation": "same entity, amount and date"})
            else:
                seen[key] = iid
            d = i["issued_at"][:10]                     # наивно: без перевода в пояс компании
            if not ps <= d <= pe:
                out.append({"type": "period_cutoff_error", "affected_ids": [iid],
                            "claimed_amount_minor": i["total_minor"], "currency": i["currency"],
                            "evidence_ids": [i["doc_id"], posted[iid]["row_id"]],
                            "explanation": "issued outside period"})
        for pid, rows in pay_rows.items():
            p = pays.get(pid)
            if not p:
                continue
            cash = [r for r in rows if r["account"].startswith("1000")]
            d = p["timestamp"][:10]
            if cash and not ps <= d <= pe:
                out.append({"type": "period_cutoff_error", "affected_ids": [pid],
                            "claimed_amount_minor": p["amount_minor"], "currency": p["currency"],
                            "evidence_ids": [p["doc_id"], cash[0]["row_id"]], "explanation": "receipt outside period"})
            susp = [r for r in rows if r["account"].startswith("2900")]
            for ref in p["invoice_refs"]:
                credited = sum(r["credit_minor"] for r in rows
                               if r["account"].startswith("1200") and r["invoice_id"] == ref["invoice_id"])
                if credited == 0 and susp:
                    u = ref["amount_minor"]
                elif p["currency"] == m["base_currency"] and credited < ref["amount_minor"] and susp:
                    u = ref["amount_minor"] - credited
                else:
                    continue
                ev = [p["doc_id"], susp[0]["row_id"]]
                if credited:
                    inv = invs.get(ref["invoice_id"])
                    ar = [r for r in rows if r["account"].startswith("1200") and r["invoice_id"] == ref["invoice_id"]]
                    ev += ([inv["doc_id"]] if inv else []) + [ar[0]["row_id"]]
                out.append({"type": "missing_or_partial_allocation", "affected_ids": [pid, ref["invoice_id"]],
                            "claimed_amount_minor": u, "currency": p["currency"],
                            "evidence_ids": ev, "explanation": "refs not credited"})
        return out[:30]


# ---------------------------------------------------------------------------- 3. сверка по открытым правилам

class EvidenceReconciler(Policy):
    """Сверяет открытые документы, проводки и курсы с опубликованной политикой."""

    name = "evidence_reconciler"
    ORDER = ("invoices", "payments", "ledger", "fx")

    def begin(self, obs, info):
        super().begin(obs, info)
        self.data = {table: [] for table in self.ORDER}
        self.queue = list(self.ORDER)
        self.cursor = None
        self.pending = None
        self.rules = obs["policy"]

    def act(self, obs):
        res = (obs or {}).get("result") or {}
        if self.pending and res.get("table") == self.pending:
            self.data[self.pending].extend(res["records"])
            self.cursor = res["next_cursor"]
            if self.cursor is None:
                self.queue.pop(0)
                self.pending = None
        if self.queue:
            self.pending = self.queue[0]
            return {"name": "list_records", "args": {
                "table": self.pending, "cursor": self.cursor, "limit": 50}}
        return submit_action(self.episode_id, self.reconcile())

    @staticmethod
    def _account(row, code):
        return row["account"].split(" ", 1)[0] == code

    def reconcile(self):
        manifest = self.manifest
        timezone = manifest["timezone"]
        base = manifest["base_currency"]
        period_start, period_end = manifest["period_start"], manifest["period_end"]
        invoices = {row["invoice_id"]: row for row in self.data["invoices"]}
        payments = {row["payment_id"]: row for row in self.data["payments"]}
        fx = {(row["source_currency"], row["date"]): Decimal(row["rate"])
              for row in self.data["fx"]}
        by_invoice, by_payment = defaultdict(list), defaultdict(list)
        for row in self.data["ledger"]:
            if row["payment_id"]:
                by_payment[row["payment_id"]].append(row)
            elif row["invoice_id"]:
                by_invoice[row["invoice_id"]].append(row)

        def local_date(timestamp):
            return money.local_date(timestamp, timezone).isoformat()

        def rate_for(currency, date):
            return Decimal(1) if currency == base else fx[(currency, date)]

        findings = []
        posted = {}
        for invoice_id, rows in by_invoice.items():
            if any(self._account(row, "3000") for row in rows):
                continue
            ar = next((row for row in rows
                       if self._account(row, "1200") and row["debit_minor"] > 0), None)
            if ar:
                posted[invoice_id] = ar

        groups = defaultdict(list)
        for invoice_id in posted:
            invoice = invoices[invoice_id]
            key = (invoice["entity_id"], invoice["currency"], local_date(invoice["issued_at"]),
                   json.dumps(invoice["line_items"], sort_keys=True))
            groups[key].append(invoice)
        for items in groups.values():
            if len(items) < 2:
                continue
            items.sort(key=lambda row: (money.parse_iso(row["issued_at"]).timestamp(), row["invoice_id"]))
            original = items[0]
            for duplicate in items[1:]:
                row = posted[duplicate["invoice_id"]]
                findings.append({
                    "type": "duplicate_invoice",
                    "affected_ids": sorted([original["invoice_id"], duplicate["invoice_id"]]),
                    "claimed_amount_minor": duplicate["total_minor"],
                    "currency": duplicate["currency"],
                    "evidence_ids": [original["doc_id"], duplicate["doc_id"], row["row_id"]],
                    "explanation": "identical invoice posted twice on the same local date",
                })

        for invoice_id, row in posted.items():
            invoice = invoices[invoice_id]
            date = local_date(invoice["issued_at"])
            if not period_start <= date <= period_end:
                findings.append({
                    "type": "period_cutoff_error", "affected_ids": [invoice_id],
                    "claimed_amount_minor": invoice["total_minor"], "currency": invoice["currency"],
                    "evidence_ids": [invoice["doc_id"], row["row_id"]],
                    "explanation": f"invoice local date {date} outside period but posted",
                })
            if invoice["currency"] != base:
                correct = money.convert_minor(
                    invoice["total_minor"], invoice["currency"], base,
                    rate_for(invoice["currency"], date))
                difference = abs(row["debit_minor"] - correct)
                tolerance = self.rules["issue_types"]["fx_conversion_error"]["tolerance_minor"]
                if difference > tolerance:
                    findings.append({
                        "type": "fx_conversion_error", "affected_ids": [invoice_id],
                        "claimed_amount_minor": difference, "currency": base,
                        "evidence_ids": [invoice["doc_id"], row["row_id"],
                                         f"fx:{date}:{invoice['currency']}:{base}"],
                        "explanation": "posted base amount differs from policy-rate conversion",
                    })

        for payment_id, rows in by_payment.items():
            payment = payments[payment_id]
            date = local_date(payment["timestamp"])
            cash = next((row for row in rows if self._account(row, "1000")), None)
            if not cash:
                continue
            if not period_start <= date <= period_end:
                findings.append({
                    "type": "period_cutoff_error", "affected_ids": [payment_id],
                    "claimed_amount_minor": payment["amount_minor"], "currency": payment["currency"],
                    "evidence_ids": [payment["doc_id"], cash["row_id"]],
                    "explanation": f"receipt local date {date} outside period but posted",
                })
            if payment["currency"] != base:
                correct = money.convert_minor(
                    payment["amount_minor"], payment["currency"], base,
                    rate_for(payment["currency"], date))
                booked = cash["debit_minor"] - cash["credit_minor"]
                difference = abs(booked - correct)
                tolerance = self.rules["issue_types"]["fx_conversion_error"]["tolerance_minor"]
                if difference > tolerance:
                    findings.append({
                        "type": "fx_conversion_error", "affected_ids": [payment_id],
                        "claimed_amount_minor": difference, "currency": base,
                        "evidence_ids": [payment["doc_id"], cash["row_id"],
                                         f"fx:{date}:{payment['currency']}:{base}"],
                        "explanation": "cash posted with a non-policy rate",
                    })

            suspense = [row for row in rows if self._account(row, "2900")]
            for ref in payment["invoice_refs"]:
                invoice = invoices.get(ref["invoice_id"])
                amount = ref["amount_minor"]
                if invoice is None or amount <= 0:
                    continue
                invoice_date = local_date(invoice["issued_at"])
                rate = rate_for(payment["currency"], invoice_date)
                expected = money.convert_minor(amount, payment["currency"], base, rate)
                actual = sum(row["credit_minor"] - row["debit_minor"] for row in rows
                             if self._account(row, "1200") and row["invoice_id"] == ref["invoice_id"])
                if actual >= expected - 1:
                    continue
                low, high = 0, amount
                while low < high:
                    middle = (low + high) // 2
                    if money.convert_minor(middle, payment["currency"], base, rate) < actual:
                        low = middle + 1
                    else:
                        high = middle
                unapplied = amount - low
                if unapplied <= 0:
                    continue
                evidence = [payment["doc_id"]]
                if suspense:
                    evidence.append(suspense[0]["row_id"])
                if unapplied < amount:
                    evidence.append(invoice["doc_id"])
                    ar = next((row for row in rows if self._account(row, "1200")
                               and row["invoice_id"] == ref["invoice_id"]), None)
                    if ar:
                        evidence.append(ar["row_id"])
                findings.append({
                    "type": "missing_or_partial_allocation",
                    "affected_ids": sorted([payment_id, ref["invoice_id"]]),
                    "claimed_amount_minor": unapplied, "currency": payment["currency"],
                    "evidence_ids": evidence,
                    "explanation": "invoice_refs amount not fully credited to receivables",
                })
        findings.sort(key=lambda finding: (finding["type"], finding["affected_ids"]))
        return findings[:30]


# ---------------------------------------------------------------------------- 4. атака «пометить всё»

class FlagAll(Policy):
    name = "flag_all"
    TYPES = RandomExplorer.TYPES

    def begin(self, obs, info):
        super().begin(obs, info)
        self.step_n = 0
        self.docs = []

    def act(self, obs):
        res = (obs or {}).get("result") or {}
        for r in res.get("records") or []:
            self.docs.append(r)
        self.step_n += 1
        if self.step_n == 1:
            return {"name": "list_records", "args": {"table": "invoices", "limit": 50}}
        if self.step_n == 2:
            return {"name": "list_records", "args": {"table": "payments", "limit": 50}}
        findings = []
        for d in self.docs:
            bid = d.get("invoice_id") if "total_minor" in d else d.get("payment_id")
            amt = d.get("total_minor", d.get("amount_minor", 0))
            for t in self.TYPES:
                findings.append({"type": t, "affected_ids": [bid], "claimed_amount_minor": abs(amt),
                                 "currency": d["currency"], "evidence_ids": [d["doc_id"]],
                                 "explanation": "flag everything"})
        return submit_action(self.episode_id, findings[:30])


# ---------------------------------------------------------------------------- 5. oracle (только у оценщика)

class Oracle(Policy):
    name = "oracle"

    def __init__(self, truth: dict):
        self.truth = truth

    def act(self, obs):
        findings = [{"type": i["type"], "affected_ids": list(i["affected_ids"]),
                     "claimed_amount_minor": i["expected_amount_minor"], "currency": i["currency"],
                     "evidence_ids": list(i["evidence_sets"][0]), "explanation": "oracle"}
                    for i in self.truth["issues"]]
        return submit_action(self.episode_id, findings)


BASELINES = ("random_explorer", "simple_reconciler", "evidence_reconciler", "flag_all", "oracle")


def make_policy(name: str, truth: dict | None = None, seed: int = 0) -> Policy:
    if name == "random_explorer":
        return RandomExplorer(seed)
    if name == "simple_reconciler":
        return SimpleReconciler()
    if name == "evidence_reconciler":
        return EvidenceReconciler()
    if name == "flag_all":
        return FlagAll()
    if name == "oracle":
        if truth is None:
            raise ValueError("oracle needs truth (grader side only)")
        return Oracle(truth)
    raise ValueError(name)
