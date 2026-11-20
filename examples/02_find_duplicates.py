# Своя проверка: ищем дубли счетов и отправляем выводы оценщику.
from auditenv.env import AuditEnv

env = AuditEnv(mode="train")
# В этой компании специально спрятаны 2 дубля счетов (и больше ничего)
config = {"clean": False,
          "errors": {"missing_or_partial_allocation": [0, 0],
                     "fx_conversion_error": [0, 0], "period_cutoff_error": [0, 0], "duplicate_invoice": [2, 2]},
          "interactions": {"partial_payment_wrong_fx": [0, 0], "cutoff_partial_payment_fx": [0, 0]}}
obs, info = env.reset(seed=7, config=config)
episode_id = obs["manifest"]["episode_id"]

def read_all(table):
    """Читает таблицу целиком, страницами по 50 строк (1 страница = 1 шаг)."""
    rows, cursor = [], None
    while True:
        args = {"table": table, "limit": 50}
        if cursor:
            args["cursor"] = cursor
        obs, *_ = env.step({"name": "list_records", "args": args})
        rows += obs["result"]["records"]
        cursor = obs["result"]["next_cursor"]
        if not cursor:
            return rows

invoices = read_all("invoices")
ledger = read_all("ledger")
print(f"Прочитано: {len(invoices)} счетов, {len(ledger)} проводок")

# Строки журнала по каждому счёту (счёт 1200 — дебиторская задолженность)
posted = {}
for r in ledger:
    if r["invoice_id"] and not r["payment_id"] and r["account"].startswith("1200"):
        posted.setdefault(r["invoice_id"], r["row_id"])

def fingerprint(inv):
    # тот же клиент, валюта, сумма и день выставления
    return (inv["entity_id"], inv["currency"], inv["total_minor"], inv["issued_at"][:10])

seen, findings = {}, []
for inv in sorted(invoices, key=lambda x: x["issued_at"]):
    if inv["invoice_id"] not in posted:      # счёт не проведён — пропускаем
        continue
    key = fingerprint(inv)
    if key in seen:
        first = seen[key]
        findings.append({
            "type": "duplicate_invoice",
            "affected_ids": [first["invoice_id"], inv["invoice_id"]],
            "claimed_amount_minor": inv["total_minor"],
            "currency": inv["currency"],
            "evidence_ids": [first["doc_id"], inv["doc_id"], posted[inv["invoice_id"]]],
            "explanation": "Тот же клиент, сумма и день",
        })
        print("Дубль:", first["invoice_id"], "и", inv["invoice_id"])
    else:
        seen[key] = inv

submit = {"name": "submit", "args": {"findings": {"episode_id": episode_id, "findings": findings}}}
obs, reward, terminated, truncated, info = env.step(submit)
print()
print(f"Награда: {reward:+.3f}")
print(f'Точность {info["precision"]:.2f} · полнота {info["recall"]:.2f} · F1 {info["f1"]:.2f}')
print(f'Верно {info["tp"]} · неверно {info["fp"]} · пропущено {info["fn"]}')
