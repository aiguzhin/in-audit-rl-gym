# Сравниваем пять базовых политик на нескольких компаниях.
from auditenv.env import AuditEnv
from auditenv.generator import generate_episode
from auditenv.policies import BASELINES, make_policy

def run(policy_name, seed):
    ep = generate_episode(seed)
    env = AuditEnv(mode="train", time_limit_s=10**9)
    obs, info = env.reset(episode=ep)
    pol = make_policy(policy_name, truth=ep.truth if policy_name == "oracle" else None, seed=seed)
    pol.begin(obs, info)
    while True:
        obs, reward, terminated, truncated, info = env.step(pol.act(obs))
        if terminated or truncated:
            return reward, info

seeds = [1, 2, 3, 4, 5]
print(f'{"политика":<20}' + "".join(f"{'№' + str(s):>9}" for s in seeds) + f'{"среднее":>10}')
for name in BASELINES:
    rewards = [run(name, s)[0] for s in seeds]
    print(f"{name:<20}" + "".join(f"{r:>+9.3f}" for r in rewards) + f"{sum(rewards) / len(rewards):>+10.3f}")
