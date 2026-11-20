# Ваш код. Среда уже установлена — просто импортируйте её.
from auditenv.env import AuditEnv

env = AuditEnv(mode="train")
obs, info = env.reset(seed=2026)
print(obs["task"])
print()
print("Доступные действия:")
for name, spec in obs["actions"].items():
    print(" ", name, spec["args"])
