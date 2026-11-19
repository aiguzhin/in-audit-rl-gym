"""CLI.

python -m auditenv check     — единая команда проверки (тесты + данные + политики + парные проверки)
python -m auditenv export    — 10 train и 10 dev эпизодов + траектории
python -m auditenv demo      — показ эпизода со скриптовой политикой
"""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import subprocess
import sys
import time
from collections import Counter
from pathlib import Path

from .checks import paired_check, verify_episode
from .config import config_hash, resolve_config
from .generator import generate_episode
from .policies import BASELINES, SimpleReconciler, make_policy
from .runner import run_inprocess, run_isolated

ROOT = Path(__file__).resolve().parents[1]


def load_split(name: str) -> dict:
    return json.loads((ROOT / "configs" / f"{name}.json").read_text(encoding="utf-8"))


def split_episodes(split: dict) -> list[tuple[int, dict]]:
    out = []
    for group in split["groups"]:
        for s in group["seeds"]:
            out.append((s, group["config"]))
    return out


def write_jsonl(path: Path, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def export_episode(ep, pub_dir: Path, grader_dir: Path):
    pub_dir.mkdir(parents=True, exist_ok=True)
    grader_dir.mkdir(parents=True, exist_ok=True)
    p = ep.public
    (pub_dir / "manifest.json").write_text(json.dumps(p["manifest"], indent=2, ensure_ascii=False), encoding="utf-8")
    (pub_dir / "policy.json").write_text(json.dumps(p["policy"], indent=2, ensure_ascii=False), encoding="utf-8")
    cols = ["row_id", "timestamp", "account", "debit_minor", "credit_minor", "currency", "entity_id", "invoice_id", "payment_id"]
    with (pub_dir / "ledger.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for r in p["ledger"]:
            w.writerow(["null" if r[c] is None else r[c] for c in cols])
    with (pub_dir / "fx.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["date", "source_currency", "target_currency", "rate"])
        for r in p["fx"]:
            w.writerow([r["date"], r["source_currency"], r["target_currency"], r["rate"]])
    write_jsonl(pub_dir / "invoices.jsonl", p["invoices"])
    write_jsonl(pub_dir / "payments.jsonl", p["payments"])
    (grader_dir / "truth.json").write_text(json.dumps(ep.truth, indent=2, ensure_ascii=False), encoding="utf-8")
    prov = {k: v for k, v in ep.provenance.items() if k != "pre_injection_ledger"}
    (grader_dir / "provenance.json").write_text(json.dumps(prov, indent=2, ensure_ascii=False), encoding="utf-8")


def cmd_export(args):
    traj_all = []
    index = []
    for split_name in ("train", "dev"):
        split = load_split(split_name)
        for seed, cfg in split_episodes(split):
            ep = generate_episode(seed, cfg)
            export_episode(ep, ROOT / "episodes" / split_name / ep.episode_id,
                           ROOT / "grader_data" / split_name / ep.episode_id)
            index.append({"split": split_name, "seed": seed, "episode_id": ep.episode_id,
                          "config_hash": config_hash(resolve_config(cfg)), "issues": len(ep.truth["issues"]),
                          "counts": ep.public["manifest"]["counts"]})
            for name in ("random_explorer", "simple_reconciler", "flag_all"):
                traj, res = run_inprocess(make_policy(name, seed=0), seed, cfg, mode="train", episode=ep)
                for t in traj:
                    t.update({"policy": name, "split": split_name})
                traj_all += traj
    write_jsonl(ROOT / "trajectories" / "trajectories.jsonl", traj_all)
    (ROOT / "episodes" / "index.json").write_text(json.dumps(index, indent=2), encoding="utf-8")
    print(f"exported {len(index)} episodes, {len(traj_all)} trajectory steps")


def summarize(results):
    table = {}
    for name in BASELINES:
        rs = [r for r in results if r["policy"] == name]
        if not rs:
            continue
        table[name] = {k: round(statistics.mean(r[k] for r in rs), 4)
                       for k in ("precision", "recall", "f1", "reward", "inspection_steps", "wall_s")}
        table[name]["episodes"] = len(rs)
    return table


def failure_analysis(results, episodes):
    """Измеренный разбор: какие типы пропускает/ложно находит простой алгоритм."""
    truth_by_id = {}
    for seed, cfg in episodes:
        ep = generate_episode(seed, cfg)
        truth_by_id[ep.episode_id] = {i["issue_id"]: i for i in ep.truth["issues"]}
    missed, fp = Counter(), Counter()
    for r in results:
        if r["policy"] != "simple_reconciler" or not r.get("valid"):
            continue
        for iid in r.get("missed_issue_ids", []):
            i = truth_by_id[r["episode_id"]][iid]
            missed[i["type"] + (f" [{i['scenario']}]" if i["scenario"] else "")] += 1
        for pf in r.get("per_finding", []):
            if pf["result"] == "FP":
                fp[pf["closest_failure"]] += 1
    return {"missed_by_type": dict(missed.most_common()), "false_positive_reasons": dict(fp.most_common())}


def cmd_check(args):
    t0 = time.time()
    report = {"sections": {}}
    ok_all = True
    print("[1/5] unit tests ...")
    ut = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"], cwd=ROOT,
                        capture_output=True, text=True)
    report["sections"]["unit_tests"] = {"ok": ut.returncode == 0, "tail": ut.stderr.strip().splitlines()[-3:]}
    ok_all &= ut.returncode == 0

    split = load_split(args.split)
    episodes = split_episodes(split)
    print(f"[2/5] data & truth on {len(episodes)} episodes ...")
    data = []
    for seed, cfg in episodes:
        v = verify_episode(generate_episode(seed, cfg))
        data.append({"seed": seed, **v})
    passed = sum(d["ok"] for d in data)
    report["sections"]["data_and_truth"] = {"passed": passed, "total": len(data),
                                            "failed": [d for d in data if not d["ok"]]}
    ok_all &= passed == len(data)

    print("[3/5] baseline policies (isolated grader process) ...")
    results, traj = run_isolated(list(BASELINES), episodes, seed=0)
    table = summarize(results)
    report["sections"]["baselines"] = table
    oracle_ok = all(r["reward"] == 1.0 for r in results if r["policy"] == "oracle")
    attack_ok = all(r["reward"] < 0 for r in results if r["policy"] == "flag_all")
    report["sections"]["baseline_sanity"] = {"oracle_max_reward": oracle_ok, "flag_all_negative": attack_ok}
    ok_all &= oracle_ok and attack_ok
    write_jsonl(ROOT / "reports" / "check_trajectories.jsonl",
                [t for t in traj if t["policy"] != "oracle"])

    print("[4/5] paired reproducibility/transform checks ...")
    pairs = [paired_check(seed, cfg) for seed, cfg in episodes[:20]]
    report["sections"]["paired"] = {"passed": sum(p["ok"] for p in pairs), "total": len(pairs),
                                    "failed": [p for p in pairs if not p["ok"]]}
    ok_all &= all(p["ok"] for p in pairs)

    print("[5/5] failure analysis ...")
    report["sections"]["failure_analysis_simple_reconciler"] = failure_analysis(results, episodes)
    report["ok"] = bool(ok_all)
    report["elapsed_s"] = round(time.time() - t0, 1)
    out = ROOT / "reports"
    out.mkdir(exist_ok=True)
    (out / "check_report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in report["sections"].items() if k != "data_and_truth"} |
                     {"data_and_truth": f"{passed}/{len(data)}"}, indent=2, ensure_ascii=False))
    print("RESULT:", "PASS" if ok_all else "FAIL", f"({report['elapsed_s']} s)")
    return 0 if ok_all else 1


def cmd_demo(args):
    ep = generate_episode(args.seed, load_split("dev")["groups"][0]["config"])
    traj, res = run_inprocess(SimpleReconciler(), args.seed, None, mode="train", episode=ep)
    m = ep.public["manifest"]
    print(f"episode {m['episode_id']}: base {m['base_currency']}, period {m['period_start']}..{m['period_end']} "
          f"tz {m['timezone']}, counts {m['counts']}")
    for t in traj[1:]:
        a = t["action"]
        brief = a["name"] + " " + json.dumps(a["args"])[:80] if a["name"] != "submit" else \
            f"submit ({len(a['args']['findings']['findings'])} findings)"
        print(f"  step {t['step']:>3}: {brief}")
    print(f"result: reward={res['reward']:.3f} P={res['precision']:.2f} R={res['recall']:.2f} F1={res['f1']:.2f} "
          f"steps={res['inspection_steps']} hidden issues={len(ep.truth['issues'])}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(prog="auditenv")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--split", default="check")
    sub.add_parser("export")
    d = sub.add_parser("demo")
    d.add_argument("--seed", type=int, default=2001)
    args = ap.parse_args(argv)
    return {"check": cmd_check, "export": cmd_export, "demo": cmd_demo}[args.cmd](args) or 0


if __name__ == "__main__":
    sys.exit(main())
