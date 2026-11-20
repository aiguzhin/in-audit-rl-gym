# Своя политика в виде класса: тот же интерфейс, что у базовых политик (begin + act).
from auditenv.env import AuditEnv
from auditenv.policies import Policy, submit_action

class Allocator(Policy):
    """Читает платежи и журнал, ищет оплаты, «застрявшие» на счёте 2900 (невыясненные суммы)."""
    name = "allocator"
    TABLES = ["payments", "ledger"]

    def begin(self, obs, info):
        super().begin(obs, info)
        self.data = {t: [] for t in self.TABLES}
        self.queue, self.cursor = list(self.TABLES), None

    def act(self, obs):
        res = obs.get("result") or {}
        if res.get("table") in self.data:                 # пришла очередная страница
            self.data[res["table"]] += res["records"]
            self.cursor = res["next_cursor"]
            if self.cursor is None:
                self.queue.pop(0)
        if self.queue:                                    # читаем дальше
            args = {"table": self.queue[0], "limit": 50}
            if self.cursor:
                args["cursor"] = self.cursor
            return {"name": "list_records", "args": args}
        return submit_action(self.episode_id, self.check())

    def check(self):
        base = self.manifest["base_currency"]
        rows_by_pay = {}
        for r in self.data["ledger"]:
            if r["payment_id"]:
                rows_by_pay.setdefault(r["payment_id"], []).append(r)
        findings = []
        for p in self.data["payments"]:
            rows = rows_by_pay.get(p["payment_id"], [])
            suspense = [r for r in rows if r["account"].startswith("2900")]
            if not suspense or p["currency"] != base:
                continue   # платежи в другой валюте — домашнее задание: нужен курс из таблицы fx
            for ref in p["invoice_refs"]:
                ar = [r for r in rows if r["account"].startswith("1200") and r["invoice_id"] == ref["invoice_id"]]
                credited = sum(r["credit_minor"] for r in ar)
                if credited < ref["amount_minor"]:
                    findings.append({
                        "type": "missing_or_partial_allocation",
                        "affected_ids": [p["payment_id"], ref["invoice_id"]],
                        "claimed_amount_minor": ref["amount_minor"] - credited,
                        "currency": p["currency"],
                        "evidence_ids": [p["doc_id"], ref["invoice_id"], suspense[0]["row_id"]] + [r["row_id"] for r in ar[:1]],
                        "explanation": "Часть оплаты не разнесена на счёт",
                    })
        return findings

config = {"clean": False,
          "errors": {"duplicate_invoice": [0, 0],
                     "fx_conversion_error": [0, 0], "period_cutoff_error": [0, 0], "missing_or_partial_allocation": [2, 2]},
          "interactions": {"partial_payment_wrong_fx": [0, 0], "cutoff_partial_payment_fx": [0, 0]}}
total = 0
for seed in range(1, 6):
    env = AuditEnv(mode="train", time_limit_s=10**9)
    obs, info = env.reset(seed=seed, config=config)
    pol = Allocator()
    pol.begin(obs, info)
    while True:
        obs, reward, done, cut, info = env.step(pol.act(obs))
        if done or cut:
            break
    total += reward
    print(f"компания №{seed}: награда {reward:+.3f} · F1 {info['f1']:.2f} · "
          f"верно {info['tp']}, неверно {info['fp']}, пропущено {info['fn']} · шагов {info['inspection_steps']}")
print(f"Среднее: {total / 5:+.3f}")
print("Пропуски — это платежи в другой валюте. Допишите пересчёт по курсу из таблицы fx и награда вырастет.")
