"""API таблицы лидеров Fin-Audit RL Gym.

Стандартная библиотека + psycopg. Результат НЕ принимается на веру: сервер заново генерирует
ту же компанию по номеру и сценарию и считает награду общим matcher'ом.

  GET  /api/health
  GET  /api/leaderboard?limit=20
  GET  /api/stats
  POST /api/results  {name, seed, preset, steps, findings:[...]}

Переменные окружения: DATABASE_URL (Render подставляет из базы), ALLOWED_ORIGINS, PORT.
Без DATABASE_URL работает на SQLite в памяти — для локальной проверки.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from auditenv.generator import generate_episode  # noqa: E402
from auditenv.matcher import score  # noqa: E402

PRESETS = {
    "mixed": {},
    "inter": {"clean": False, "interactions": {"partial_payment_wrong_fx": [1, 1], "cutoff_partial_payment_fx": [1, 1]}},
    "clean": {"clean": True},
    "single": {"clean": False, "interactions": {"partial_payment_wrong_fx": [0, 0], "cutoff_partial_payment_fx": [0, 0]},
               "errors": {t: [1, 1] for t in ("duplicate_invoice", "missing_or_partial_allocation",
                                              "fx_conversion_error", "period_cutoff_error")}},
}
ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "https://fin-audit-rl-gym.onrender.com").split(",") if o.strip()]
NAME_RE = re.compile(r"[^\w \-.А-Яа-яЁё]", re.UNICODE)
MAX_BODY = 64_000
RATE: dict[str, list[float]] = {}
LOCK = threading.Lock()


# ------------------------------------------------------------------ база
class DB:
    def __init__(self):
        url = os.environ.get("DATABASE_URL")
        self.pg = bool(url)
        if self.pg:
            import psycopg
            self.conn = psycopg.connect(url, autocommit=True)
            self.ph = "%s"
            ddl = """CREATE TABLE IF NOT EXISTS results(
              id SERIAL PRIMARY KEY, created_at TIMESTAMPTZ DEFAULT now(), name TEXT NOT NULL,
              seed INTEGER NOT NULL, preset TEXT NOT NULL, episode_id TEXT NOT NULL,
              reward DOUBLE PRECISION NOT NULL, f1 DOUBLE PRECISION, precision DOUBLE PRECISION, recall DOUBLE PRECISION,
              tp INTEGER, fp INTEGER, fn INTEGER, steps INTEGER)"""
        else:
            self.conn = sqlite3.connect(":memory:", check_same_thread=False)
            self.ph = "?"
            ddl = """CREATE TABLE IF NOT EXISTS results(
              id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT DEFAULT CURRENT_TIMESTAMP, name TEXT NOT NULL,
              seed INTEGER NOT NULL, preset TEXT NOT NULL, episode_id TEXT NOT NULL,
              reward REAL NOT NULL, f1 REAL, precision REAL, recall REAL, tp INTEGER, fp INTEGER, fn INTEGER, steps INTEGER)"""
        self.exec(ddl)

    def exec(self, sql, args=(), fetch=False):
        sql = sql.replace("?", self.ph)
        with LOCK:
            cur = self.conn.cursor()
            cur.execute(sql, args)
            rows = cur.fetchall() if fetch else None
            if not self.pg:
                self.conn.commit()
            return rows


db: DB | None = None


def get_db() -> DB:
    global db
    if db is None:
        db = DB()
    return db


# ------------------------------------------------------------------ логика
def submit(body: dict, ip: str) -> tuple[int, dict]:
    now = time.time()
    with LOCK:
        hits = [t for t in RATE.get(ip, []) if now - t < 60]
        if len(hits) >= 10:
            return 429, {"error": "Слишком много отправок. Подождите минуту."}
        RATE[ip] = hits + [now]
    name = NAME_RE.sub("", str(body.get("name", "")))[:32].strip()
    if len(name) < 2:
        return 400, {"error": "Имя должно содержать от 2 до 32 символов."}
    try:
        seed = int(body.get("seed"))
        steps = int(body.get("steps", 0))
    except (TypeError, ValueError):
        return 400, {"error": "Номер компании и шаги должны быть числами."}
    if not 0 <= seed <= 999_999 or not 0 <= steps <= 99:
        return 400, {"error": "Номер компании 0–999999, шаги 0–99."}
    preset = body.get("preset")
    if preset not in PRESETS:
        return 400, {"error": "Неизвестный сценарий."}
    ep = generate_episode(seed, PRESETS[preset])
    res = score({"episode_id": ep.episode_id, "findings": body.get("findings")}, ep.truth, ep.public, steps)
    if not res["valid"]:
        return 400, {"error": "Выводы не прошли проверку структуры. Проверьте, что у каждого вывода есть тип, ID, сумма и валюта.", "detail": res["error"]}
    get_db().exec("INSERT INTO results(name,seed,preset,episode_id,reward,f1,precision,recall,tp,fp,fn,steps) "
                  "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
                  (name, seed, preset, ep.episode_id, res["reward"], res["f1"], res["precision"], res["recall"],
                   res["tp"], res["fp"], res["fn"], steps))
    better = get_db().exec("SELECT COUNT(*) FROM results WHERE reward > ?", (res["reward"],), fetch=True)[0][0]
    return 200, {"saved": True, "rank": int(better) + 1, "reward": res["reward"], "f1": res["f1"],
                 "tp": res["tp"], "fp": res["fp"], "fn": res["fn"]}


def leaderboard(limit: int) -> dict:
    rows = get_db().exec("SELECT name,reward,f1,tp,fp,fn,steps,preset,seed,created_at FROM results "
                         "ORDER BY reward DESC, steps ASC, id ASC LIMIT ?", (max(1, min(limit, 50)),), fetch=True)
    keys = ("name", "reward", "f1", "tp", "fp", "fn", "steps", "preset", "seed", "created_at")
    return {"results": [{k: (str(v) if k == "created_at" else v) for k, v in zip(keys, r)} for r in rows]}


def stats() -> dict:
    n, avg, best = get_db().exec("SELECT COUNT(*), AVG(reward), MAX(reward) FROM results", fetch=True)[0]
    players = get_db().exec("SELECT COUNT(DISTINCT name) FROM results", fetch=True)[0][0]
    return {"runs": int(n), "players": int(players), "avg_reward": float(avg or 0), "best_reward": float(best or 0)}


# ------------------------------------------------------------------ HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = "FinAuditAPI/1.0"

    def _cors(self):
        origin = self.headers.get("Origin")
        if origin and (origin in ORIGINS or "*" in ORIGINS):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, code: int, obj: dict):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        try:
            if u.path in ("/", "/api/health"):
                return self._json(200, {"ok": True, "db": "postgres" if get_db().pg else "memory"})
            if u.path == "/api/leaderboard":
                limit = int(parse_qs(u.query).get("limit", ["20"])[0])
                return self._json(200, leaderboard(limit))
            if u.path == "/api/stats":
                return self._json(200, stats())
            return self._json(404, {"error": "Не найдено."})
        except Exception as e:  # noqa: BLE001
            return self._json(500, {"error": "Ошибка сервера.", "detail": type(e).__name__})

    def do_POST(self):
        if urlparse(self.path).path != "/api/results":
            return self._json(404, {"error": "Не найдено."})
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0 or length > MAX_BODY:
            return self._json(413, {"error": "Слишком большой запрос."})
        try:
            body = json.loads(self.rfile.read(length))
            if not isinstance(body, dict):
                raise ValueError
        except (ValueError, json.JSONDecodeError):
            return self._json(400, {"error": "Тело запроса должно быть JSON-объектом."})
        try:
            ip = (self.headers.get("X-Forwarded-For") or self.client_address[0]).split(",")[0].strip()
            code, obj = submit(body, ip)
            return self._json(code, obj)
        except Exception as e:  # noqa: BLE001
            return self._json(500, {"error": "Ошибка сервера.", "detail": type(e).__name__})

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))


def main():
    port = int(os.environ.get("PORT", "8000"))
    get_db()
    print(f"listening on :{port}, db={'postgres' if get_db().pg else 'memory'}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
