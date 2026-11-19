"""Запуск политик: в процессе (обучение/отладка) и через изолированный процесс (закрытый прогон)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time

from .env import AuditEnv
from .generator import generate_episode
from .policies import make_policy


def run_inprocess(policy, seed: int, config: dict | None, mode: str = "train", episode=None):
    env = AuditEnv(mode=mode)
    obs, info = env.reset(seed, config, episode=episode)
    policy.begin(obs, info)
    t0 = time.perf_counter()
    while True:
        obs, rew, term, trunc, info = env.step(policy.act(obs))
        if term or trunc:
            break
    res = env.grader_result()["result"]
    res["wall_s"] = round(time.perf_counter() - t0, 4)
    return env.trajectory, res


class RemoteEnv:
    """Клиент изолированной среды. Политика видит только step(); эталон в другом процессе."""

    def __init__(self, grader_log: str, mode: str = "eval"):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.proc = subprocess.Popen([sys.executable, "-m", "auditenv.server", "--mode", mode,
                                      "--grader-log", grader_log], cwd=root, stdin=subprocess.PIPE,
                                     stdout=subprocess.PIPE, text=True, bufsize=1,
                                     env={**os.environ, "PYTHONPATH": root})

    def _call(self, msg):
        self.proc.stdin.write(json.dumps(msg) + "\n")
        self.proc.stdin.flush()
        return json.loads(self.proc.stdout.readline())

    def reset(self, seed, config):
        r = self._call({"cmd": "reset", "seed": seed, "config": config})
        return r["observation"], r["info"]

    def step(self, action):
        r = self._call({"cmd": "step", "action": action})
        return r["observation"], r["reward"], r["terminated"], r["truncated"], r["info"]

    def close(self):
        try:
            self.proc.stdin.write(json.dumps({"cmd": "close"}) + "\n")
            self.proc.stdin.flush()
        except Exception:
            pass
        self.proc.wait(timeout=10)


def run_isolated(policy_names, episodes: list[tuple[int, dict]], seed: int = 0):
    """Закрытый прогон: одинаковые политики на одинаковых эпизодах; итоги читает только оценщик."""
    fd, log = tempfile.mkstemp(prefix="grader_", suffix=".jsonl")
    os.close(fd)
    env = RemoteEnv(log)
    trajectories, order = [], []
    try:
        for ep_seed, cfg in episodes:
            truth = None
            for name in policy_names:
                if name == "oracle":
                    truth = truth or generate_episode(ep_seed, cfg).truth   # эталон — на стороне оценщика
                pol = make_policy(name, truth=truth, seed=seed)
                obs, info = env.reset(ep_seed, cfg)
                pol.begin(obs, info)
                traj = [{"episode_id": info["episode_id"], "step": 0, "action": None, "observation": obs,
                         "reward": 0.0, "terminated": False, "truncated": False, "policy": name}]
                t0 = time.perf_counter()
                while True:
                    act = pol.act(obs)
                    obs, rew, term, trunc, inf = env.step(act)
                    traj.append({"episode_id": info["episode_id"], "step": len(traj), "action": act,
                                 "observation": obs, "reward": rew, "terminated": term, "truncated": trunc,
                                 "policy": name})
                    if term or trunc:
                        break
                trajectories += traj
                order.append((ep_seed, name, round(time.perf_counter() - t0, 4)))
    finally:
        env.close()
    with open(log, encoding="utf-8") as fh:
        results = [json.loads(x) for x in fh if x.strip()]
    os.unlink(log)
    out = []
    for (ep_seed, name, wall), g in zip(order, results):
        r = g["result"]
        r.update({"seed": ep_seed, "policy": name, "episode_id": g["episode_id"], "wall_s": wall})
        out.append(r)
    return out, trajectories
