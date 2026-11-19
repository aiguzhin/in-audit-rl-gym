"""Изолированный процесс среды (закрытый прогон).

Протокол — JSON Lines через stdin/stdout:
  -> {"cmd": "reset", "seed": int, "config": {...}}   <- {"observation", "info"}
  -> {"cmd": "step", "action": {...}}                  <- {"observation","reward","terminated","truncated","info"}
  -> {"cmd": "close"}
Эталон, seed и итог оценщика остаются в этом процессе; итог дописывается в --grader-log,
путь к которому знает только оценщик. Агент получает только наблюдения.
"""
from __future__ import annotations

import argparse
import json
import sys

from .env import AuditEnv


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="eval", choices=["train", "eval"])
    ap.add_argument("--grader-log", required=True)
    args = ap.parse_args(argv)
    env = AuditEnv(mode=args.mode, record=False)
    out = sys.stdout
    sys.stdout = sys.stderr          # ничто постороннее не попадёт в канал агента

    def send(obj):
        out.write(json.dumps(obj, ensure_ascii=False) + "\n")
        out.flush()

    for line in sys.stdin:
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            send({"error": "bad_message"})
            continue
        cmd = msg.get("cmd")
        if cmd == "reset":
            obs, info = env.reset(msg["seed"], msg.get("config"))
            send({"observation": obs, "info": info})
        elif cmd == "step":
            obs, rew, term, trunc, info = env.step(msg.get("action"))
            send({"observation": obs, "reward": rew, "terminated": term, "truncated": trunc, "info": info})
            if term or trunc:
                with open(args.grader_log, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(env.grader_result(), ensure_ascii=False) + "\n")
        elif cmd == "close":
            break
        else:
            send({"error": "unknown_cmd"})


if __name__ == "__main__":
    main()
