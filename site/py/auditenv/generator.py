"""Генератор вымышленных компаний.

Порядок работы:
1. Скрытая согласованная история (клиенты, счета, платежи, расходы, курсы) — чистые книги.
2. Проводки по правилам policy.json; проверка бухгалтерских равенств ДО ошибок.
3. Внесение ошибок с записью причинного изменения (provenance) и эталона (truth).
4. Отрисовка: случайные публичные ID и порядок (зависят только от transform),
   поэтому смена ID/порядка не меняет историю компании.

Все данные вымышлены. Никаких реальных компаний, людей, счетов.
"""
from __future__ import annotations

import calendar
import copy
import math
import random
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from decimal import Decimal

from . import money
from .config import (
    ERROR_TYPES, GENERATOR_VERSION, INTERACTIONS, SCHEMA_VERSION,
    canonical_json, config_hash, resolve_config, sha, story_key,
)

ACC_CASH = "1000 Cash"
ACC_AR = "1200 Accounts receivable"
ACC_ADV = "2100 Customer advances"
ACC_SUSP = "2900 Suspense - unapplied cash"
ACC_OPEN = "3000 Opening balance equity"
ACC_REV = "4000 Revenue"
ACC_FX = "7000 FX gain/loss"
EXPENSE_ACCOUNTS = ["6100 Rent", "6200 Software", "6300 Travel", "6400 Office supplies", "6500 Contractors"]

CATALOG = [
    ("CONS-H", "Consulting hours", 80, 260),
    ("IMPL", "Implementation package", 900, 6000),
    ("TRN", "Training session", 300, 1500),
    ("SUP-P", "Priority support", 150, 900),
    ("LIC-A", "Analytics licence", 200, 2400),
    ("HW-K", "Hardware kit", 120, 1800),
    ("AUD-R", "Data review", 250, 2200),
]
PLANS = [("SUB-STD", "Subscription Standard", 90, 400), ("SUB-PRO", "Subscription Pro", 400, 1500)]

ID_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


@dataclass
class Episode:
    seed: int
    config: dict
    episode_id: str
    public: dict          # manifest, policy, ledger, invoices, payments, fx
    truth: dict           # закрыто
    provenance: dict      # закрыто
    id_map: dict = field(default_factory=dict)  # внутренний ключ -> публичный ID (закрыто)


# ======================================================================= история

class Story:
    def __init__(self, seed: int, cfg: dict):
        self.cfg = cfg
        self.key = story_key(seed, cfg)
        self.rng = random.Random(int(self.key[:16], 16))
        r = self.rng
        self.base = r.choice(cfg["currencies"]["base_pool"])
        pool = [c for c in cfg["currencies"]["foreign_pool"] if c != self.base]
        lo, hi = cfg["currencies"]["n_foreign"]
        self.foreign = sorted(r.sample(pool, k=min(len(pool), r.randint(lo, hi))))
        self.tz = r.choice(cfg["timezones"])
        self.tzinfo = money.parse_tz(self.tz)
        year = r.choice(cfg["years"])
        month = r.randint(1, 12)
        self.period_start = date(year, month, 1)
        self.period_end = date(year, month, calendar.monthrange(year, month)[1])
        self.offset_hours = self.tzinfo.utcoffset(None).total_seconds() / 3600
        self.fx: dict[tuple[str, date], Decimal] = {}
        self.fx_start = self.period_start - timedelta(days=45)
        self.fx_end = self.period_end + timedelta(days=7)
        self.customers: list[dict] = []
        self.vendors: list[str] = []
        self.invoices: dict[str, dict] = {}
        self.payments: dict[str, dict] = {}
        self.ledger: list[dict] = []
        self.all_rows: dict[int, dict] = {}
        self._n = {"i": 0, "p": 0, "o": 0, "r": 0, "c": 0, "v": 0}

    # ---------------------------------------------------------------- utils
    def nk(self, prefix: str) -> str:
        self._n[prefix] += 1
        return f"{prefix}{self._n[prefix]}"

    def local_dt(self, d: date, hh: int, mm: int, ss: int = 0) -> datetime:
        return datetime.combine(d, time(hh, mm, ss), tzinfo=self.tzinfo)

    def business_dt(self, d: date) -> datetime:
        r = self.rng
        return self.local_dt(d, r.randint(8, 18), r.randint(0, 59), r.randint(0, 59))

    def rand_date(self, a: date, b: date) -> date:
        if b < a:
            b = a
        return a + timedelta(days=self.rng.randint(0, (b - a).days))

    def in_period(self, d: date) -> bool:
        return self.period_start <= d <= self.period_end

    def rate(self, cur: str, d: date) -> Decimal:
        if cur == self.base:
            return Decimal(1)
        return self.fx[(cur, d)]

    def to_base(self, amount: int, cur: str, d: date, rate: Decimal | None = None) -> int:
        if cur == self.base:
            return amount
        return money.convert_minor(amount, cur, self.base, rate if rate is not None else self.rate(cur, d))

    def money_in(self, cur: str, usd_lo: float, usd_hi: float) -> int:
        usd = Decimal(str(round(self.rng.uniform(usd_lo, usd_hi), 2)))
        major = usd / money.USD_VALUE[cur]
        exp = money.exponent(cur)
        # «красивые» цены: до целых (или до 10/100 для дешёвых валют)
        step = Decimal(1)
        if major > 10000:
            step = Decimal(100)
        elif major > 1000:
            step = Decimal(10)
        major = (major / step).to_integral_value() * step
        if major <= 0:
            major = Decimal(1)
        return int(major.scaleb(exp))

    def inv_date(self, inv: dict) -> date:
        return inv["issued"].astimezone(self.tzinfo).date()

    def pay_date(self, p: dict) -> date:
        return p["ts"].astimezone(self.tzinfo).date()

    # ---------------------------------------------------------------- построение
    def build(self):
        self._fx()
        self._parties()
        self._invoices()
        self._payments()
        self._expenses()
        self._post_all()

    def _fx(self):
        r = self.rng
        for cur in self.foreign:
            level = money.USD_VALUE[cur] / money.USD_VALUE[self.base]
            level *= Decimal(str(round(r.uniform(0.93, 1.07), 4)))
            drift = r.uniform(-0.0015, 0.0015)
            d = self.fx_start
            x = 0.0
            while d <= self.fx_end:
                x += drift + r.gauss(0, 0.006)
                rate = Decimal(money.fmt_rate(level * Decimal(str(round(math.exp(x), 8)))))
                self.fx[(cur, d)] = rate
                d += timedelta(days=1)

    def _parties(self):
        r, s = self.rng, self.cfg["size"]
        n = r.randint(*s["customers"])
        for i in range(n):
            if i < len(self.foreign):
                cur = self.foreign[i]          # хотя бы один клиент на каждую валюту
            else:
                cur = self.base if r.random() < 0.55 else r.choice(self.foreign)
            plan = r.choice(PLANS)
            self.customers.append({
                "k": self.nk("c"), "cur": cur,
                "recurring": self.cfg["distractors"]["recurring"] and r.random() < 0.25,
                "plan": plan, "sub_price": self.money_in(cur, plan[2], plan[3]),
            })
        self.vendors = [self.nk("v") for _ in range(r.randint(*s["vendors"]))]

    def new_invoice(self, cust: dict, issued: datetime, kind: str, recurring_week: int | None = None,
                    render_utc: bool | None = None) -> dict:
        r = self.rng
        k = self.nk("i")
        cur = cust["cur"]
        order = None
        if recurring_week is not None:
            start = self.inv_local(issued)
            end = start + timedelta(days=6)
            sku, desc = cust["plan"][0], cust["plan"][1]
            lines = [{"sku": sku, "description": desc, "service_period": f"{start.isoformat()}/{end.isoformat()}",
                      "qty": 1, "unit_price_minor": cust["sub_price"], "amount_minor": cust["sub_price"]}]
        else:
            order = self.nk("o")
            lines = []
            for item in r.sample(CATALOG, k=r.randint(1, 3)):
                qty = r.randint(1, 12) if item[0] in ("CONS-H", "TRN") else r.randint(1, 3)
                unit = self.money_in(cur, item[2], item[3])
                lines.append({"sku": item[0], "description": item[1], "service_period": None,
                              "qty": qty, "unit_price_minor": unit, "amount_minor": unit * qty})
        inv = {
            "k": k, "doc": "d" + k, "entity": cust["k"], "cur": cur, "issued": issued,
            "due": issued + timedelta(days=r.choice([14, 30, 30, 45])),
            "lines": lines, "order": order, "total": sum(l["amount_minor"] for l in lines),
            "kind": kind, "render_utc": (r.random() < 0.3) if render_utc is None else render_utc,
            "remaining": 0, "paid_by": [],
        }
        inv["remaining"] = inv["total"]
        self.invoices[k] = inv
        return inv

    def inv_local(self, dt: datetime) -> date:
        return dt.astimezone(self.tzinfo).date()

    def _invoices(self):
        r, s, dis = self.rng, self.cfg["size"], self.cfg["distractors"]
        prev_start = self.period_start - timedelta(days=30)
        for _ in range(r.randint(*s["prior_invoices"])):
            self.new_invoice(r.choice(self.customers), self.business_dt(
                self.rand_date(prev_start, self.period_start - timedelta(days=1))), "prior")
        target = r.randint(*s["period_invoices"])
        count = 0
        for cust in self.customers:
            if cust["recurring"]:
                first = self.period_start + timedelta(days=r.randint(0, 3))
                d = first
                while d <= self.period_end:
                    self.new_invoice(cust, self.business_dt(d), "period", recurring_week=1)
                    count += 1
                    d += timedelta(days=7)
        while count < target:
            d = self.rand_date(self.period_start, self.period_end)
            self.new_invoice(r.choice(self.customers), self.business_dt(d), "period")
            count += 1
        if dis["boundary_timestamps"]:
            # законный счёт в последний день периода поздно вечером
            if self.offset_hours < 0:
                hh = 24 + int(self.offset_hours) + r.randint(0, -int(self.offset_hours) - 1)
                self.new_invoice(r.choice(self.customers), self.local_dt(self.period_end, min(hh, 23), r.randint(0, 59)),
                                 "period", render_utc=True)       # в UTC выглядит как следующий месяц
            else:
                self.new_invoice(r.choice(self.customers), self.local_dt(self.period_end, 23, r.randint(10, 59)),
                                 "period", render_utc=False)
            # законный счёт в первый день периода сразу после полуночи
            if self.offset_hours > 0:
                hh = r.randint(0, max(0, int(self.offset_hours) - 1))
                self.new_invoice(r.choice(self.customers), self.local_dt(self.period_start, hh, r.randint(0, 59)),
                                 "period", render_utc=True)       # в UTC выглядит как прошлый месяц
        for i in range(r.randint(*s["next_invoices"])):
            d = self.period_end + timedelta(days=r.randint(1, 3))
            if i == 0 and dis["boundary_timestamps"] and self.offset_hours > 0:
                hh = r.randint(0, max(0, int(self.offset_hours) - 1))
                self.new_invoice(r.choice(self.customers), self.local_dt(self.period_end + timedelta(days=1), hh,
                                 r.randint(0, 59)), "next", render_utc=True)  # в UTC попадает в период
            else:
                self.new_invoice(r.choice(self.customers), self.business_dt(d), "next")

    def new_payment(self, entity: str | None, cur: str, ts: datetime, amount: int, refs: list, kind: str) -> dict:
        k = self.nk("p")
        p = {"k": k, "doc": "d" + k, "entity": entity, "cur": cur, "ts": ts, "amount": amount,
             "refs": refs, "kind": kind, "excess": 0}
        self.payments[k] = p
        for inv_k, a in refs:
            self.invoices[inv_k]["remaining"] -= a
            self.invoices[inv_k]["paid_by"].append(k)
        return p

    def pay_ts(self, d: date) -> datetime:
        r = self.rng
        if self.cfg["distractors"]["boundary_timestamps"] and r.random() < 0.5:
            if d == self.period_end and self.offset_hours < 0:
                return self.local_dt(d, 23, r.randint(0, 59))   # в UTC — следующий день
            if d == self.period_start and self.offset_hours > 0:
                return self.local_dt(d, 0, r.randint(1, 59))     # в UTC — предыдущий день
        return self.business_dt(d)

    def _payments(self):
        r, dis = self.rng, self.cfg["distractors"]
        open_invs = [i for i in self.invoices.values() if i["kind"] in ("prior", "period")]
        open_invs.sort(key=lambda i: (i["issued"], i["k"]))
        for inv in open_invs:
            d0 = max(self.inv_date(inv), self.period_start)
            if d0 >= self.period_end:
                continue
            p_pay = 0.75 if inv["kind"] == "prior" else 0.45
            if r.random() > p_pay:
                continue
            roll = r.random()
            cust_cur = inv["cur"]
            if dis["split_payments"] and roll < 0.15:
                a1 = max(1, int(inv["total"] * r.uniform(0.3, 0.7)))
                d1 = self.rand_date(d0, self.period_end)
                self.new_payment(inv["entity"], cust_cur, self.pay_ts(d1), a1, [(inv["k"], a1)], "split")
                d2 = self.rand_date(d1, self.period_end)
                a2 = inv["total"] - a1
                self.new_payment(inv["entity"], cust_cur, self.pay_ts(d2), a2, [(inv["k"], a2)], "split")
            elif roll < 0.25:
                a = max(1, int(inv["total"] * r.uniform(0.3, 0.8)))
                self.new_payment(inv["entity"], cust_cur, self.pay_ts(self.rand_date(d0, self.period_end)), a,
                                 [(inv["k"], a)], "partial_legit")
            elif dis["refunds"] and roll < 0.33 and cust_cur == self.base:
                e = max(1, int(inv["total"] * r.uniform(0.02, 0.2)))
                d1 = self.rand_date(d0, self.period_end)
                p = self.new_payment(inv["entity"], cust_cur, self.pay_ts(d1), inv["total"] + e,
                                     [(inv["k"], inv["total"])], "overpay")
                p["excess"] = e
                d2 = self.rand_date(d1, self.period_end)
                self.new_payment(inv["entity"], cust_cur, self.pay_ts(d2), -e, [], "refund")
            else:
                self.new_payment(inv["entity"], cust_cur, self.pay_ts(self.rand_date(d0, self.period_end)),
                                 inv["remaining"], [(inv["k"], inv["remaining"])], "full")
        if dis["multi_invoice_payments"]:
            by_cust: dict[str, list] = {}
            for inv in open_invs:
                if inv["remaining"] == inv["total"] and self.inv_date(inv) < self.period_end:
                    by_cust.setdefault(inv["entity"], []).append(inv)
            for ent in sorted(by_cust):
                invs = by_cust[ent]
                if len(invs) >= 2 and r.random() < 0.5:
                    pair = invs[:2]
                    d0 = max(max(self.inv_date(i) for i in pair), self.period_start)
                    refs = [(i["k"], i["total"]) for i in pair]
                    self.new_payment(ent, pair[0]["cur"], self.pay_ts(self.rand_date(d0, self.period_end)),
                                     sum(a for _, a in refs), refs, "multi")
        if dis["unidentified_receipts"]:
            for _ in range(r.randint(1, 3)):
                cur = self.base if r.random() < 0.6 else r.choice(self.foreign)
                self.new_payment(None, cur, self.pay_ts(self.rand_date(self.period_start, self.period_end)),
                                 self.money_in(cur, 40, 900), [], "unidentified")

    def _expenses(self):
        r = self.rng
        self.expenses = []
        recurring = {v: (r.choice(EXPENSE_ACCOUNTS), self.money_in(self.base, 50, 3000)) for v in self.vendors}
        for _ in range(r.randint(*self.cfg["size"]["expenses"])):
            v = r.choice(self.vendors)
            if r.random() < 0.35:
                acc, amt = recurring[v]                      # законные повторяющиеся суммы
            else:
                acc, amt = r.choice(EXPENSE_ACCOUNTS), self.money_in(self.base, 10, 4000)
            self.expenses.append({"vendor": v, "account": acc, "amount": amt,
                                  "ts": self.business_dt(self.rand_date(self.period_start, self.period_end))})

    # ---------------------------------------------------------------- проводки
    def row(self, ts, account, debit, credit, entity=None, inv=None, pay=None) -> dict:
        if debit < 0 or credit < 0:
            debit, credit = max(0, -credit), max(0, -debit)
        rid = self._n["r"] = self._n["r"] + 1
        row = {"k": rid, "ts": ts.astimezone(self.tzinfo), "account": account, "debit": int(debit),
               "credit": int(credit), "entity": entity, "inv": inv, "pay": pay}
        self.all_rows[rid] = row
        return row

    def post_invoice(self, inv: dict, ts: datetime | None = None, rate: Decimal | None = None) -> list[dict]:
        amt = self.to_base(inv["total"], inv["cur"], self.inv_date(inv), rate)
        ts = ts or inv["issued"]
        return [self.row(ts, ACC_AR, amt, 0, inv["entity"], inv["k"]),
                self.row(ts, ACC_REV, 0, amt, inv["entity"], inv["k"])]

    def post_opening(self, inv: dict) -> list[dict]:
        amt = self.to_base(inv["total"], inv["cur"], self.inv_date(inv))
        ts = self.local_dt(self.period_start, 0, 0)
        return [self.row(ts, ACC_AR, amt, 0, inv["entity"], inv["k"]),
                self.row(ts, ACC_OPEN, 0, amt, inv["entity"], inv["k"])]

    def post_payment(self, p: dict, applied: dict | None = None, cash_rate: Decimal | None = None,
                     ts: datetime | None = None) -> list[dict]:
        """Платёж: Dr cash; Cr AR по курсу счёта; излишек -> 2100; неразнесённое -> 2900; разница -> 7000."""
        d = self.pay_date(p)
        ts = ts or p["ts"]
        ent = p["entity"]
        rows = []
        if p["kind"] == "refund":
            amt = self.to_base(-p["amount"], p["cur"], d, cash_rate)
            return [self.row(ts, ACC_ADV, amt, 0, ent, None, p["k"]),
                    self.row(ts, ACC_CASH, 0, amt, ent, None, p["k"])]
        cash = self.to_base(p["amount"], p["cur"], d, cash_rate)
        rows.append(self.row(ts, ACC_CASH, cash, 0, ent, None, p["k"]))
        credits = 0
        applied_total = 0
        for inv_k, a in p["refs"]:
            a_app = applied.get(inv_k, a) if applied is not None else a
            applied_total += a_app
            if a_app > 0:
                inv = self.invoices[inv_k]
                ar = self.to_base(a_app, p["cur"], self.inv_date(inv))
                rows.append(self.row(ts, ACC_AR, 0, ar, ent, inv_k, p["k"]))
                credits += ar
        if p["excess"]:
            adv = self.to_base(p["excess"], p["cur"], d, cash_rate)
            rows.append(self.row(ts, ACC_ADV, 0, adv, ent, None, p["k"]))
            credits += adv
            applied_total += p["excess"]
        unapplied = p["amount"] - applied_total
        if unapplied > 0:
            susp = self.to_base(unapplied, p["cur"], d, cash_rate)
            rows.append(self.row(ts, ACC_SUSP, 0, susp, ent, None, p["k"]))
            credits += susp
        diff = cash - credits
        if diff > 0:
            rows.append(self.row(ts, ACC_FX, 0, diff, ent, None, p["k"]))
        elif diff < 0:
            rows.append(self.row(ts, ACC_FX, -diff, 0, ent, None, p["k"]))
        return rows

    def _post_all(self):
        self.ledger = []
        for inv in sorted(self.invoices.values(), key=lambda i: i["k"]):
            if inv["kind"] == "prior":
                self.ledger += self.post_opening(inv)
            elif inv["kind"] == "period":
                self.ledger += self.post_invoice(inv)
        for p in self.payments.values():
            self.ledger += self.post_payment(p)
        for e in self.expenses:
            self.ledger.append(self.row(e["ts"], e["account"], e["amount"], 0, e["vendor"]))
            self.ledger.append(self.row(e["ts"], ACC_CASH, 0, e["amount"], e["vendor"]))

    def rows_of(self, inv=None, pay=None, account=None) -> list[dict]:
        out = []
        for r_ in self.ledger:
            if inv is not None and r_["inv"] != inv:
                continue
            if pay is not None and r_["pay"] != pay:
                continue
            if account is not None and r_["account"] != account:
                continue
            out.append(r_)
        return out

    def replace_rows(self, old: list[dict], new: list[dict]):
        ids = {r_["k"] for r_ in old}
        self.ledger = [r_ for r_ in self.ledger if r_["k"] not in ids] + new


# ======================================================================= равенства

def balance_report(rows: list[dict]) -> dict:
    """Бухгалтерские равенства: всего Dr=Cr, по каждому счёту-документу, по каждому платежу."""
    groups: dict[str, list[int]] = {}
    tot_d = tot_c = 0
    for r_ in rows:
        tot_d += r_["debit"]
        tot_c += r_["credit"]
        if r_["pay"]:
            g = "pay:" + r_["pay"]
        elif r_["inv"]:
            g = "inv:" + r_["inv"]
        else:
            g = f"exp:{r_['ts'].isoformat()}:{r_['entity']}"
        acc = groups.setdefault(g, [0, 0])
        acc[0] += r_["debit"]
        acc[1] += r_["credit"]
    bad = sorted(g for g, (d, c) in groups.items() if d != c)
    return {"total_debit": tot_d, "total_credit": tot_c, "balanced": tot_d == tot_c and not bad,
            "unbalanced_groups": bad[:20], "groups": len(groups)}


# ======================================================================= ошибки

class Injector:
    def __init__(self, story: Story):
        self.s = story
        self.r = random.Random(int(sha(story.key + ":inject")[:16], 16))
        self.used: set[str] = set()
        self.issues: list[dict] = []
        self.log: list[dict] = []

    # ---------------------------------------------------------------- helpers
    def wrong_rate(self, cur: str, d: date, amount: int) -> tuple[Decimal, str, dict] | None:
        s = self.s
        correct = s.to_base(amount, cur, d)
        thr = max(5, int(abs(correct) * 0.002))
        cands = []
        for k in range(1, 11):
            for dd in (d - timedelta(days=k), d + timedelta(days=k)):
                if (cur, dd) in s.fx:
                    booked = s.to_base(amount, cur, d, s.fx[(cur, dd)])
                    if abs(booked - correct) >= thr:
                        cands.append((dd, s.fx[(cur, dd)]))
        if cands and self.r.random() < 0.75:
            dd, rate = self.r.choice(cands)
            return rate, "rate_of_wrong_date", {"used_rate_date": dd.isoformat()}
        # опечатка в курсе: перестановка двух соседних цифр
        txt = format(s.rate(cur, d), "f")
        digits = [i for i, ch in enumerate(txt) if ch.isdigit()]
        for _ in range(20):
            i = self.r.randrange(len(digits) - 1)
            a, b = digits[i], digits[i + 1]
            if txt[a] == txt[b] or b != a + 1:
                continue
            t = list(txt)
            t[a], t[b] = t[b], t[a]
            cand = Decimal("".join(t))
            if cand > 0 and abs(s.to_base(amount, cur, d, cand) - correct) >= thr:
                return cand, "rate_digit_transposition", {"typed_rate": "".join(t)}
        cand = Decimal(money.fmt_rate(s.rate(cur, d) * Decimal("1.013")))
        return cand, "rate_typo", {"typed_rate": str(cand)}

    def ev(self, kind: str, *a) -> tuple:
        return (kind,) + a

    def add_issue(self, typ: str, affected: list[str], amount: int, cur: str, tol: int,
                  evidence_sets: list[list[tuple]], scenario: str | None, cause: str, detail: dict):
        self.issues.append({"type": typ, "affected": affected, "amount": int(amount), "currency": cur,
                            "tolerance_minor": int(tol), "evidence_sets": evidence_sets,
                            "scenario": scenario, "cause": cause, "detail": detail})

    def snapshot(self, rows):
        return [dict(r_) for r_ in rows]

    def open_period_invoices(self, foreign: bool | None = None, unpaid: bool = False) -> list[dict]:
        s = self.s
        out = []
        for inv in sorted(s.invoices.values(), key=lambda i: int(i["k"][1:])):
            if inv["kind"] != "period" or inv["k"] in self.used:
                continue
            if foreign is True and inv["cur"] == s.base:
                continue
            if unpaid and inv["paid_by"]:
                continue
            if s.inv_date(inv) >= s.period_end - timedelta(days=1):
                continue
            out.append(inv)
        return out

    def next_day_trap_ts(self) -> datetime:
        """Момент в первые часы следующего периода; при положительном смещении в UTC это ещё период."""
        s = self.s
        d = s.period_end + timedelta(days=1)
        if s.offset_hours > 0:
            return s.local_dt(d, self.r.randint(0, max(0, int(s.offset_hours) - 1)), self.r.randint(0, 59))
        return s.local_dt(d + timedelta(days=self.r.randint(0, 1)), self.r.randint(8, 16), self.r.randint(0, 59))

    def early_posting_ts(self) -> datetime:
        return self.s.local_dt(self.s.period_end, self.r.randint(17, 22), self.r.randint(0, 59))

    # ---------------------------------------------------------------- типы ошибок
    def duplicate_invoice(self, scenario=None) -> bool:
        s = self.s
        cands = self.open_period_invoices()
        if not cands:
            return False
        x = self.r.choice(cands)
        dk = s.nk("i")
        d = copy.deepcopy({k: v for k, v in x.items() if k not in ("paid_by",)})
        d.update({"k": dk, "doc": "d" + dk, "paid_by": [], "remaining": x["total"]})
        shift = timedelta(minutes=self.r.randint(3, 240))
        issued = x["issued"] + shift
        if s.inv_local(issued) != s.inv_date(x):
            issued = x["issued"] - shift
        d["issued"] = issued
        d["due"] = x["due"] + (issued - x["issued"])
        s.invoices[dk] = d
        rows = s.post_invoice(d, rate=s.rate(x["cur"], s.inv_date(x)))
        s.ledger += rows
        self.used |= {x["k"], dk}
        self.add_issue("duplicate_invoice", [x["k"], dk], x["total"], x["cur"], 0,
                       [[("doc", x["k"]), ("doc", dk), ("row", rows[0]["k"])],
                        [("doc", x["k"]), ("doc", dk), ("row", rows[1]["k"])]],
                       scenario, "invoice re-entered and posted twice",
                       {"original": x["k"], "duplicate": dk, "minutes_apart": int(abs((issued - x["issued"]).total_seconds()) // 60),
                        "added_rows": [rows[0]["k"], rows[1]["k"]]})
        return True

    def _misallocate(self, p: dict, inv_k: str, a: int, missing: bool, cash_rate=None, ts=None,
                     scenario=None) -> tuple[list, int]:
        s = self.s
        inv = s.invoices[inv_k]
        res = money.conversion_resolution(p["cur"], s.base, s.rate(p["cur"], s.inv_date(inv)))
        if missing:
            u = a
        else:
            u = int(a * self.r.uniform(0.2, 0.7))
            u = max(u, 3 * res + 3)
            if u >= a:
                u = a
        old = s.rows_of(pay=p["k"])
        new = s.post_payment(p, applied={inv_k: a - u}, cash_rate=cash_rate, ts=ts)
        s.replace_rows(old, new)
        susp = [r_ for r_ in new if r_["account"] == ACC_SUSP]
        if u == a:      # ничего не разнесено: документ + строка 2900 (сумма = весь ref)
            ev = [("doc", p["k"]), ("row", susp[0]["k"])]
        else:           # частично: + документ счёта (курс) + строка Cr 1200 (сколько разнесено)
            ar = [r_ for r_ in new if r_["account"] == ACC_AR and r_["inv"] == inv_k]
            ev = [("doc", p["k"]), ("doc", inv_k), ("row", ar[0]["k"]), ("row", susp[0]["k"])]
        self.add_issue("missing_or_partial_allocation", [p["k"], inv_k], u, p["cur"], res,
                       [ev], scenario,
                       "payment allocation missing" if u == a else "payment allocation partial",
                       {"payment": p["k"], "invoice": inv_k, "referenced_minor": a, "applied_minor": a - u,
                        "removed_rows": [r_["k"] for r_ in old], "added_rows": [r_["k"] for r_ in new]})
        return new, u

    def missing_or_partial_allocation(self, scenario=None) -> bool:
        s = self.s
        cands = []
        for p in s.payments.values():
            if p["k"] in self.used or p["kind"] not in ("full", "split", "partial_legit", "multi"):
                continue
            for inv_k, a in p["refs"]:
                inv = s.invoices[inv_k]
                res = money.conversion_resolution(p["cur"], s.base, s.rate(p["cur"], s.inv_date(inv)))
                if inv_k not in self.used and a > 10 * res + 20:
                    cands.append((p, inv_k, a))
        if not cands:
            return False
        p, inv_k, a = self.r.choice(cands)
        self._misallocate(p, inv_k, a, missing=self.r.random() < 0.4, scenario=scenario)
        self.used |= {p["k"], inv_k}
        return True

    def fx_conversion_error(self, scenario=None) -> bool:
        s = self.s
        cands = self.open_period_invoices(foreign=True, unpaid=True)
        if not cands:
            return False
        inv = self.r.choice(cands)
        d = s.inv_date(inv)
        rate, cause, det = self.wrong_rate(inv["cur"], d, inv["total"])
        old = s.rows_of(inv=inv["k"])
        old = [r_ for r_ in old if r_["pay"] is None]
        new = s.post_invoice(inv, rate=rate)
        s.replace_rows(old, new)
        correct = s.to_base(inv["total"], inv["cur"], d)
        diff = abs(new[0]["debit"] - correct)
        fxid = ("fx", inv["cur"], d)
        self.used.add(inv["k"])
        det.update({"correct_rate": str(s.rate(inv["cur"], d)), "booked_rate": str(rate), "correct_base_minor": correct,
                    "booked_base_minor": new[0]["debit"], "removed_rows": [r_["k"] for r_ in old],
                    "added_rows": [r_["k"] for r_ in new]})
        self.add_issue("fx_conversion_error", [inv["k"]], diff, s.base, 1,
                       [[("doc", inv["k"]), ("row", new[0]["k"]), fxid],
                        [("doc", inv["k"]), ("row", new[1]["k"]), fxid]], scenario, cause, det)
        return True

    def period_cutoff_error(self, scenario=None) -> bool:
        s = self.s
        if self.r.random() < 0.65:
            nexts = [i for i in s.invoices.values() if i["kind"] == "next" and i["k"] not in self.used]
            nexts.sort(key=lambda i: int(i["k"][1:]))
            if not nexts:
                cust = self.r.choice(s.customers)
                nexts = [s.new_invoice(cust, s.business_dt(s.period_end + timedelta(days=self.r.randint(1, 3))), "next")]
            inv = self.r.choice(nexts)
            ts = self.early_posting_ts()
            rows = s.post_invoice(inv, ts=ts)
            s.ledger += rows
            self.used.add(inv["k"])
            self.add_issue("period_cutoff_error", [inv["k"]], inv["total"], inv["cur"], 0,
                           [[("doc", inv["k"]), ("row", rows[0]["k"])], [("doc", inv["k"]), ("row", rows[1]["k"])]],
                           scenario, "next-period invoice posted in current period",
                           {"document_local_date": s.inv_date(inv).isoformat(), "posted_at": ts.isoformat(),
                            "issued_at_rendered_utc": inv["render_utc"], "added_rows": [r_["k"] for r_ in rows]})
            return True
        cands = self.open_period_invoices()
        cands = [i for i in cands if i["remaining"] > 0]
        if not cands:
            return False
        inv = self.r.choice(cands)
        p = s.new_payment(inv["entity"], inv["cur"], self.next_day_trap_ts(), inv["remaining"],
                          [(inv["k"], inv["remaining"])], "cutoff")
        ts = self.early_posting_ts()
        rows = s.post_payment(p, ts=ts)
        s.ledger += rows
        self.used |= {inv["k"], p["k"]}
        cash = [r_ for r_ in rows if r_["account"] == ACC_CASH][0]
        self.add_issue("period_cutoff_error", [p["k"]], p["amount"], p["cur"], 0,
                       [[("doc", p["k"]), ("row", cash["k"])]], scenario,
                       "next-period receipt posted in current period",
                       {"document_local_date": s.pay_date(p).isoformat(), "posted_at": ts.isoformat(),
                        "added_rows": [r_["k"] for r_ in rows]})
        return True

    # ---------------------------------------------------------------- сценарии
    def partial_payment_wrong_fx(self) -> bool:
        s = self.s
        cands = [i for i in self.open_period_invoices(foreign=True, unpaid=True)
                 if s.inv_date(i) <= s.period_end - timedelta(days=2)]
        if not cands:
            return False
        inv = self.r.choice(cands)
        d = self.r.choice([s.inv_date(inv) + timedelta(days=k) for k in range(1, (s.period_end - s.inv_date(inv)).days + 1)])
        p = s.new_payment(inv["entity"], inv["cur"], s.pay_ts(d), inv["total"], [(inv["k"], inv["total"])], "scenario")
        rate, cause, det = self.wrong_rate(p["cur"], d, p["amount"])
        s.ledger += s.post_payment(p)  # чистая версия (для равенств до ошибки)
        self.pre_extra.append(p["k"])
        new, u = self._misallocate(p, inv["k"], inv["total"], missing=False, cash_rate=rate,
                                   scenario="partial_payment_wrong_fx")
        cash = [r_ for r_ in new if r_["account"] == ACC_CASH][0]
        correct = s.to_base(p["amount"], p["cur"], d)
        det.update({"correct_rate": str(s.rate(p["cur"], d)), "booked_rate": str(rate),
                    "correct_base_minor": correct, "booked_base_minor": cash["debit"]})
        self.add_issue("fx_conversion_error", [p["k"]], abs(cash["debit"] - correct), s.base, 1,
                       [[("doc", p["k"]), ("row", cash["k"]), ("fx", p["cur"], d)]],
                       "partial_payment_wrong_fx", cause, det)
        self.used |= {inv["k"], p["k"]}
        return True

    def cutoff_partial_payment_fx(self) -> bool:
        s = self.s
        cands = self.open_period_invoices(foreign=True, unpaid=True)
        if not cands:
            return False
        inv = self.r.choice(cands)
        a = int(inv["total"] * self.r.uniform(0.4, 0.8))
        p = s.new_payment(inv["entity"], inv["cur"], self.next_day_trap_ts(), a, [(inv["k"], a)], "scenario")
        ts = self.early_posting_ts()
        s.ledger += s.post_payment(p, ts=ts)
        self.pre_extra.append(p["k"])
        new, u = self._misallocate(p, inv["k"], a, missing=False, ts=ts, scenario="cutoff_partial_payment_fx")
        cash = [r_ for r_ in new if r_["account"] == ACC_CASH][0]
        self.add_issue("period_cutoff_error", [p["k"]], p["amount"], p["cur"], 0,
                       [[("doc", p["k"]), ("row", cash["k"])]], "cutoff_partial_payment_fx",
                       "partial foreign receipt dated next period posted in current period",
                       {"document_local_date": s.pay_date(p).isoformat(), "posted_at": ts.isoformat()})
        self.used |= {inv["k"], p["k"]}
        return True

    # ---------------------------------------------------------------- план
    def run(self, clean: bool):
        self.pre_extra: list[str] = []
        cfg = self.s.cfg
        if clean:
            return
        plan: list[str] = []
        for name in INTERACTIONS:
            lo, hi = cfg["interactions"].get(name, [0, 0])
            plan += [name] * self.r.randint(lo, hi)
        for t in ERROR_TYPES:
            lo, hi = cfg["errors"].get(t, [0, 0])
            plan += [t] * self.r.randint(lo, hi)
        enabled = [t for t in ERROR_TYPES if cfg["errors"].get(t, [0, 0])[1] > 0]
        while len(plan) < cfg["min_issues_if_not_clean"] and enabled:
            plan.append(self.r.choice(enabled))
        self.r.shuffle(plan)
        plan.sort(key=lambda x: 0 if x in INTERACTIONS else 1)   # сценарии раньше (им нужны свободные счета)
        for name in plan:
            weight = 2 if name in INTERACTIONS else 1
            if len(self.issues) + weight > cfg["max_issues"]:
                continue
            ok = getattr(self, name)()
            self.log.append({"planned": name, "applied": bool(ok)})
            if not ok and name in ERROR_TYPES:
                for alt in enabled:
                    if alt != name and getattr(self, alt)():
                        self.log.append({"planned": name, "applied_instead": alt})
                        break


# ======================================================================= отрисовка

class Renderer:
    def __init__(self, story: Story, cfg: dict):
        self.s = story
        tr = cfg["transform"]
        self.order = tr.get("order", "time")
        self.rkey = sha(story.key + ":render:" + str(tr.get("id_salt", "0")) + ":" + self.order)
        self.rng = random.Random(int(self.rkey[:16], 16))
        self.taken: set[str] = set()
        self.map: dict[str, str] = {}

    def token(self, prefix: str, n: int) -> str:
        while True:
            t = prefix + "".join(self.rng.choice(ID_ALPHABET) for _ in range(n))
            if t not in self.taken:
                self.taken.add(t)
                return t

    def pid(self, key) -> str | None:
        if key is None:
            return None
        key = str(key)
        if key not in self.map:
            if key.startswith("di") or key.startswith("dp"):
                self.map[key] = self.token("DOC-", 8)
            elif key[0] == "i":
                self.map[key] = self.token("INV-", 6)
            elif key[0] == "p":
                self.map[key] = self.token("PAY-", 6)
            elif key[0] == "c":
                self.map[key] = self.token("C-", 5)
            elif key[0] == "v":
                self.map[key] = self.token("V-", 5)
            elif key[0] == "o":
                self.map[key] = self.token("SO-", 6)
            else:
                self.map[key] = self.token("L-", 7)
        return self.map[key]

    def assign_all(self):
        s = self.s
        keys = [c["k"] for c in s.customers] + list(s.vendors)
        keys += [i for i in s.invoices] + ["d" + i for i in s.invoices]
        keys += [p for p in s.payments] + ["d" + p for p in s.payments]
        keys += [i["order"] for i in s.invoices.values() if i["order"]]
        keys += [str(k) for k in s.all_rows]
        keys = sorted(set(keys))
        self.rng.shuffle(keys)
        for k in keys:
            self.pid(k)

    def ts_inv(self, dt: datetime, utc: bool) -> str:
        from datetime import timezone as _tz
        return money.iso(dt.astimezone(_tz.utc) if utc else dt.astimezone(self.s.tzinfo))

    def invoice(self, inv: dict) -> dict:
        lines = []
        for l in inv["lines"]:
            l2 = dict(l)
            if inv["order"]:
                l2["description"] = f"{l['description']} (order {self.pid(inv['order'])})"
            lines.append(l2)
        return {"doc_id": self.pid(inv["doc"]), "invoice_id": self.pid(inv["k"]), "entity_id": self.pid(inv["entity"]),
                "issued_at": self.ts_inv(inv["issued"], inv["render_utc"]),
                "due_at": self.ts_inv(inv["due"], inv["render_utc"]), "currency": inv["cur"],
                "total_minor": inv["total"], "line_items": lines}

    def payment(self, p: dict) -> dict:
        return {"doc_id": self.pid(p["doc"]), "payment_id": self.pid(p["k"]), "entity_id": self.pid(p["entity"]),
                "timestamp": self.ts_inv(p["ts"], True), "currency": p["cur"], "amount_minor": p["amount"],
                "invoice_refs": [{"invoice_id": self.pid(i), "amount_minor": a} for i, a in p["refs"]]}

    def ledger_row(self, r_: dict) -> dict:
        return {"row_id": self.pid(str(r_["k"])), "timestamp": money.iso(r_["ts"]), "account": r_["account"],
                "debit_minor": r_["debit"], "credit_minor": r_["credit"], "currency": self.s.base,
                "entity_id": self.pid(r_["entity"]), "invoice_id": self.pid(r_["inv"]), "payment_id": self.pid(r_["pay"])}

    def evidence_id(self, ev: tuple) -> str:
        if ev[0] == "doc":
            return self.pid("d" + ev[1])
        if ev[0] == "row":
            return self.pid(str(ev[1]))
        return f"fx:{ev[2].isoformat()}:{ev[1]}:{self.s.base}"

    def sort(self, items: list[dict], key) -> list[dict]:
        if self.order == "shuffled":
            items = sorted(items, key=lambda x: canonical_json(x))
            self.rng.shuffle(items)
            return items
        return sorted(items, key=key)


def _utc_key(ts: str) -> tuple:
    return (money.parse_iso(ts).timestamp(),)


def generate_episode(seed: int, config: dict | None = None) -> Episode:
    cfg = resolve_config(config)
    story = Story(seed, cfg)
    story.build()
    pre_report = balance_report(story.ledger)
    clean = cfg["clean"]
    if clean is None:
        clean = random.Random(int(sha(story.key + ":clean")[:16], 16)).random() < cfg["clean_probability"]
    pre_ledger_keys = [r_["k"] for r_ in story.ledger]
    inj = Injector(story)
    inj.run(bool(clean))
    # Равенства «до ошибки» для сценариев: чистая версия их платежей уже была проведена.
    pre_rows = [story.all_rows[k] for k in pre_ledger_keys]
    post_report = balance_report(story.ledger)

    rnd = Renderer(story, cfg)
    rnd.assign_all()
    tr = cfg["transform"]
    episode_id = "ep-" + sha(story.key + ":" + str(tr.get("id_salt", "0")) + ":" + tr.get("order", "time"))[:12]

    ledger = rnd.sort([rnd.ledger_row(r_) for r_ in story.ledger], key=lambda x: (_utc_key(x["timestamp"]), x["row_id"]))
    invoices = rnd.sort([rnd.invoice(i) for i in story.invoices.values()],
                        key=lambda x: (_utc_key(x["issued_at"]), x["invoice_id"]))
    payments = rnd.sort([rnd.payment(p) for p in story.payments.values()],
                        key=lambda x: (_utc_key(x["timestamp"]), x["payment_id"]))
    fx_rows = [{"date": d.isoformat(), "source_currency": c, "target_currency": story.base, "rate": format(r_, "f")}
               for (c, d), r_ in sorted(story.fx.items(), key=lambda kv: (kv[0][1], kv[0][0]))]

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "episode_id": episode_id,
        "base_currency": story.base,
        "currencies": sorted({story.base, *story.foreign}),
        "currency_exponents": {c: money.exponent(c) for c in sorted({story.base, *story.foreign})},
        "period_start": story.period_start.isoformat(),
        "period_end": story.period_end.isoformat(),
        "period_bounds_local": [money.iso(story.local_dt(story.period_start, 0, 0)),
                                money.iso(story.local_dt(story.period_end + timedelta(days=1), 0, 0))],
        "timezone": story.tz,
        "counts": {"ledger": len(ledger), "invoices": len(invoices), "payments": len(payments), "fx": len(fx_rows),
                   "documents": len(invoices) + len(payments)},
        "rounding": {"mode": money.ROUNDING, "unit": "minor"},
    }
    from .policy import build_policy
    policy = build_policy(story.base, story.tz)

    truth_issues = []
    for n, iss in enumerate(inj.issues):
        iid = "ISS-" + sha(rnd.rkey + f":issue:{n}")[:10].upper()
        truth_issues.append({
            "issue_id": iid, "type": iss["type"],
            "affected_ids": sorted(rnd.pid(k) for k in iss["affected"]),
            "expected_amount_minor": iss["amount"], "currency": iss["currency"],
            "tolerance_minor": iss["tolerance_minor"],
            "evidence_sets": [sorted(rnd.evidence_id(e) for e in es) for es in iss["evidence_sets"]],
            "scenario": iss["scenario"],
        })
    truth = {"episode_id": episode_id, "clean": not truth_issues, "issues": truth_issues}

    def rows_pub(rows):
        return [rnd.ledger_row(r_) for r_ in rows]

    prov_inj = []
    for n, iss in enumerate(inj.issues):
        det = {}
        for k, v in iss["detail"].items():
            if k in ("removed_rows", "added_rows"):
                det[k] = [rnd.pid(str(x)) for x in v]
            elif k in ("original", "duplicate", "payment", "invoice"):
                det[k] = rnd.pid(v)
            else:
                det[k] = v
        prov_inj.append({"issue_id": truth_issues[n]["issue_id"], "type": iss["type"], "scenario": iss["scenario"],
                         "cause": iss["cause"], "detail": det})
    provenance = {
        "generator_version": GENERATOR_VERSION,
        "config_hash": config_hash(cfg),
        "story_key_prefix": story.key[:8],
        "clean": bool(clean),
        "transform": cfg["transform"],
        "hidden_history": {
            "base_currency": story.base, "foreign_currencies": story.foreign, "timezone": story.tz,
            "customers": len(story.customers), "recurring_customers": sum(c["recurring"] for c in story.customers),
            "payment_kinds": _count(p["kind"] for p in story.payments.values()),
            "invoice_kinds": _count(i["kind"] for i in story.invoices.values()),
            "expenses": len(story.expenses),
        },
        "balance_before_injection": pre_report,
        "balance_after_injection": post_report,
        "pre_injection_ledger_row_ids": [rnd.pid(str(k)) for k in pre_ledger_keys],
        "pre_injection_ledger": rows_pub(pre_rows),
        "injection_plan": inj.log,
        "injections": prov_inj,
        # Внутренние ключи -> публичные ID (для парных проверок перестановки/смены ID).
        "id_map": dict(sorted(rnd.map.items())),
    }
    public = {"manifest": manifest, "policy": policy, "ledger": ledger, "invoices": invoices,
              "payments": payments, "fx": fx_rows}
    return Episode(seed=seed, config=cfg, episode_id=episode_id, public=public, truth=truth,
                   provenance=provenance, id_map=dict(rnd.map))


def _count(it) -> dict:
    out: dict = {}
    for x in it:
        out[x] = out.get(x, 0) + 1
    return dict(sorted(out.items()))
