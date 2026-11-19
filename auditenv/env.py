"""RL-среда в стиле Gymnasium (JSON-совместимый контракт).

reset(seed, config) -> (observation, info)
step(action)        -> (observation, reward, terminated, truncated, info)

Действие: {"name": <str>, "args": {...}}
  list_records(table, cursor=None, limit=50)  table in ledger|invoices|payments|fx
  get_record(table, id)
  get_document(doc_id)
  calculator(expression)
  submit(findings)   findings = {"episode_id":..., "findings":[...]}

mode="train": терминальная награда и метрики возвращаются политике.
mode="eval":  политика всегда получает reward=0.0 и пустой info; итог хранится у оценщика
              (grader_result()), который в закрытом прогоне живёт в отдельном процессе (server.py).
"""
from __future__ import annotations

import copy
import json
import time

from . import calculator, matcher
from .generator import Episode, generate_episode

TABLES = ("ledger", "invoices", "payments", "fx")
ID_FIELD = {"ledger": "row_id", "invoices": "invoice_id", "payments": "payment_id", "fx": "fx_id"}
PAGE_MAX = 50
MAX_STEPS = 100
TIME_LIMIT_S = 60.0
ENV_VERSION = "1.0.0"

ACTIONS_SPEC = {
    "list_records": {"args": {"table": "ledger|invoices|payments|fx", "cursor": "str|null", "limit": "1..50"}},
    "get_record": {"args": {"table": "ledger|invoices|payments|fx", "id": "row_id|invoice_id|payment_id|fx_id (doc_id ok)"}},
    "get_document": {"args": {"doc_id": "doc_id of an invoice or payment"}},
    "calculator": {"args": {"expression": "decimal arithmetic: digits . + - * / ( ), <=200 chars"}},
    "submit": {"args": {"findings": "{episode_id, findings:[{type, affected_ids, claimed_amount_minor, currency, "
                                    "evidence_ids, explanation}]}"}},
}

TASK = ("You are auditing one fictional company for one reporting period. Inspect the read-only records with "
        "the tools, then submit findings with evidence. Issue types: duplicate_invoice, "
        "missing_or_partial_allocation, fx_conversion_error, period_cutoff_error. The books may be clean: "
        "an empty findings list is a valid answer. Every action, including errors and submit, uses one step.")


class ActionError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message[:200]


class AuditEnv:
    metadata = {"render_modes": []}

    def __init__(self, mode: str = "train", max_steps: int = MAX_STEPS, time_limit_s: float = TIME_LIMIT_S,
                 clock=time.monotonic, record: bool = True):
        if mode not in ("train", "eval"):
            raise ValueError("mode must be 'train' or 'eval'")
        self.mode = mode
        self.max_steps = max_steps
        self.time_limit_s = time_limit_s
        self.clock = clock
        self.record = record
        self._ep: Episode | None = None
        self._done = True

    # ------------------------------------------------------------------ API
    def reset(self, seed: int | None = None, config: dict | None = None, *, episode: Episode | None = None,
              options: dict | None = None):
        """Новый эпизод. Состояние прошлого эпизода полностью сбрасывается."""
        if episode is None:
            if seed is None:
                raise ValueError("seed is required")
            episode = generate_episode(int(seed), config)
        self._ep = episode
        pub = episode.public
        self._tables = {t: list(pub[t]) for t in TABLES}
        self._tables["fx"] = [dict(r, fx_id=f"fx:{r['date']}:{r['source_currency']}:{r['target_currency']}")
                              for r in pub["fx"]]
        self._index = {t: {r[ID_FIELD[t]]: r for r in self._tables[t]} for t in TABLES}
        self._docs = {}
        for inv in pub["invoices"]:
            self._docs[inv["doc_id"]] = ("invoice", inv)
            self._index["invoices"][inv["doc_id"]] = inv
        for p in pub["payments"]:
            self._docs[p["doc_id"]] = ("payment", p)
            self._index["payments"][p["doc_id"]] = p
        self._steps = 0
        self._inspection_steps = 0
        self._done = False
        self._t0 = self.clock()
        self._grader = {"episode_id": episode.episode_id, "events": [], "result": None}
        self.trajectory: list[dict] = []
        obs = {
            "task": TASK,
            "manifest": copy.deepcopy(pub["manifest"]),
            "policy": copy.deepcopy(pub["policy"]),
            "actions": ACTIONS_SPEC,
            "page_limit": PAGE_MAX,
            "remaining_steps": self.max_steps,
        }
        info = {"episode_id": episode.episode_id, "mode": self.mode, "env_version": ENV_VERSION,
                "max_steps": self.max_steps}
        self._log(None, obs, 0.0, False, False)
        return obs, info

    def step(self, action):
        if self._ep is None:
            raise RuntimeError("call reset() first")
        if self._done:
            obs = {"error": {"code": "episode_finished", "message": "episode already finished; call reset()"},
                   "remaining_steps": 0}
            return obs, 0.0, True, False, {}
        if self.clock() - self._t0 > self.time_limit_s:
            return self._finish_truncated(action, "time_limit")
        self._steps += 1
        name, args = None, None
        try:
            if isinstance(action, str):
                if len(action) > 200_000:
                    raise ActionError("bad_action", "action too large")
                try:
                    action = json.loads(action)
                except json.JSONDecodeError:
                    raise ActionError("bad_action", "action is not valid JSON")
            if not isinstance(action, dict) or not isinstance(action.get("name"), str):
                raise ActionError("bad_action", "action must be {name, args}")
            name, args = action["name"], action.get("args", {})
            if not isinstance(args, dict):
                raise ActionError("bad_action", "args must be an object")
            if name == "submit":
                return self._submit(action, args)
            result = self._dispatch(name, args)
            obs = {"result": result, "error": None, "remaining_steps": self.max_steps - self._steps}
        except ActionError as e:
            obs = {"result": None, "error": {"code": e.code, "message": e.message},
                   "remaining_steps": self.max_steps - self._steps}
        self._inspection_steps += 1
        if self._steps >= self.max_steps:
            return self._finish_truncated(action, "step_limit", obs)
        self._log(action, obs, 0.0, False, False)
        return obs, 0.0, False, False, {}

    def grader_result(self) -> dict:
        """Только для оценщика (не передаётся политике в закрытом режиме)."""
        return copy.deepcopy(self._grader)

    # ------------------------------------------------------------------ действия
    def _dispatch(self, name: str, a: dict):
        if name == "list_records":
            return self._list(a)
        if name == "get_record":
            table, rid = a.get("table"), a.get("id")
            self._check_table(table)
            if not isinstance(rid, str):
                raise ActionError("bad_args", "id must be a string")
            rec = self._index[table].get(rid)
            if rec is None:
                raise ActionError("not_found", f"no such record in {table}")
            return {"table": table, "record": copy.deepcopy(rec)}
        if name == "get_document":
            did = a.get("doc_id")
            if not isinstance(did, str):
                raise ActionError("bad_args", "doc_id must be a string")
            doc = self._docs.get(did)
            if doc is None:
                raise ActionError("not_found", "no such document")
            return {"doc_type": doc[0], "document": copy.deepcopy(doc[1])}
        if name == "calculator":
            try:
                return {"value": calculator.evaluate(a.get("expression"))}
            except calculator.CalcError as e:
                raise ActionError("calculator_error", str(e))
        raise ActionError("unknown_action", "unknown action name")

    def _check_table(self, table):
        if table not in TABLES:
            raise ActionError("bad_args", "table must be one of ledger, invoices, payments, fx")

    def _list(self, a: dict):
        table = a.get("table")
        self._check_table(table)
        limit = a.get("limit", PAGE_MAX)
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= PAGE_MAX:
            raise ActionError("bad_args", "limit must be an integer 1..50")
        cursor = a.get("cursor")
        offset = 0
        if cursor is not None:
            if not isinstance(cursor, str) or not cursor.startswith(table + "@"):
                raise ActionError("bad_cursor", "invalid cursor")
            try:
                offset = int(cursor.split("@", 1)[1])
            except ValueError:
                raise ActionError("bad_cursor", "invalid cursor")
            if not 0 <= offset <= len(self._tables[table]):
                raise ActionError("bad_cursor", "invalid cursor")
        rows = self._tables[table][offset:offset + limit]
        nxt = offset + len(rows)
        return {"table": table, "records": copy.deepcopy(rows), "total": len(self._tables[table]),
                "next_cursor": f"{table}@{nxt}" if nxt < len(self._tables[table]) else None}

    # ------------------------------------------------------------------ завершение
    def _submit(self, action, args):
        sub = args.get("findings")
        if sub is None and "episode_id" in args:
            sub = {k: v for k, v in args.items()}
        res = matcher.score(sub, self._ep.truth, self._ep.public, self._inspection_steps)
        if not res["valid"]:
            self._grader["events"].append({"step": self._steps, "event": "invalid_submission", "error": res["error"]})
        return self._finish(action, res, truncated=False,
                            obs={"result": {"submitted": True, "accepted": res["valid"]}, "error": None,
                                 "remaining_steps": self.max_steps - self._steps})

    def _finish_truncated(self, action, why: str, obs=None):
        res = matcher.score({"episode_id": self._ep.episode_id, "findings": []}, self._ep.truth,
                            self._ep.public, self._inspection_steps)
        self._grader["events"].append({"step": self._steps, "event": "truncated", "reason": why})
        obs = dict(obs or {"result": None, "error": None})
        obs["remaining_steps"] = max(0, self.max_steps - self._steps)
        obs["truncated_reason"] = why
        return self._finish(action, res, truncated=True, obs=obs)

    def _finish(self, action, res: dict, truncated: bool, obs: dict):
        self._done = True
        res = dict(res, truncated=truncated, steps=self._steps, elapsed_s=round(self.clock() - self._t0, 4))
        self._grader["result"] = res
        if self.mode == "train":
            reward = res["reward"]
            info = {k: res[k] for k in ("precision", "recall", "f1", "tp", "fp", "fn", "inspection_steps", "valid")}
        else:
            reward, info = 0.0, {}
        self._log(action, obs, reward, not truncated, truncated)
        return obs, reward, not truncated, truncated, info

    def _log(self, action, obs, reward, terminated, truncated):
        if self.record:
            self.trajectory.append({"episode_id": self._ep.episode_id, "step": self._steps, "action": action,
                                    "observation": obs, "reward": reward, "terminated": terminated,
                                    "truncated": truncated})
