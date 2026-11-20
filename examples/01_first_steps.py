# Первые шаги: создаём компанию и делаем один запрос к книгам.
from auditenv.env import AuditEnv

env = AuditEnv(mode="train")
obs, info = env.reset(seed=42)          # seed — номер компании

m = obs["manifest"]
print("Компания:", m["episode_id"])
print("Период:", m["period_start"], "—", m["period_end"])
print("Валюта учёта:", m["base_currency"], "| часовой пояс:", m["timezone"])
print("Сколько записей:", m["counts"])

# Действие — это словарь {"name": ..., "args": {...}}. Каждое стоит 1 шаг из 100.
action = {"name": "list_records", "args": {"table": "invoices", "limit": 5}}
obs, reward, terminated, truncated, info = env.step(action)

exp = m["currency_exponents"]
for inv in obs["result"]["records"]:
    total = inv["total_minor"] / 10 ** exp[inv["currency"]]
    print(f'{inv["invoice_id"]}  клиент {inv["entity_id"]}  {total:,.2f} {inv["currency"]}')

print("Осталось шагов:", obs["remaining_steps"])
