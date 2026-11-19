"""API FinSpector: аккаунты, профили, таблица лидеров.

Стандартная библиотека + psycopg. Результат НЕ принимается на веру: сервер заново генерирует
ту же компанию по номеру и сценарию и считает награду общим matcher'ом.

  GET  /api/health
  POST /api/register   {username, password, display?}      -> {token, user}
  POST /api/login      {username, password}                -> {token, user}
  GET  /api/me         (Authorization: Bearer <token>)     -> профиль, статистика, история, достижения
  GET  /api/daily                                          -> номер «компании дня»
  GET  /api/leaderboard?limit=20&scope=all|daily
  GET  /api/stats
  POST /api/results    {name?, seed, preset, steps, findings}  (токен необязателен)

Переменные окружения: DATABASE_URL, ALLOWED_ORIGINS, PORT, SESSION_SECRET (необязательна:
по умолчанию выводится из DATABASE_URL, чтобы не хранить ещё один секрет).
Без DATABASE_URL работает на SQLite в памяти — для локальной проверки и тестов.
"""
from __future__ import annotations

import base64
import datetime as dt
import hashlib
import hmac
import json
import os
import re
import secrets
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
NAME_RE = re.compile(r"[^\w \-.]", re.UNICODE)
USER_RE = re.compile(r"^[a-z0-9_]{3,24}$")
MAX_BODY = 64_000
TOKEN_TTL = 30 * 24 * 3600
TZ = dt.timezone(dt.timedelta(hours=5))          # «компания дня» меняется в полночь по Астане
SECRET = (os.environ.get("SESSION_SECRET")
          or hashlib.sha256(("fin-audit-session:" + os.environ.get("DATABASE_URL", secrets.token_hex(16))).encode()).hexdigest()).encode()
RATE: dict[str, list[float]] = {}
LOCK = threading.Lock()


class ApiError(Exception):
    def __init__(self, code: int, msg: str):
        super().__init__(msg)
        self.code, self.msg = code, msg


# ------------------------------------------------------------------ база
class DB:
    def __init__(self, url: str | None = None):
        url = url if url is not None else os.environ.get("DATABASE_URL")
        self.pg = bool(url)
        self.url = url
        if self.pg:
            import psycopg
            self.conn = psycopg.connect(url, autocommit=True)
            self.ph, serial, real, ts = "%s", "SERIAL PRIMARY KEY", "DOUBLE PRECISION", "TIMESTAMPTZ DEFAULT now()"
        else:
            self.conn = sqlite3.connect(":memory:", check_same_thread=False)
            self.ph, serial, real, ts = "?", "INTEGER PRIMARY KEY AUTOINCREMENT", "REAL", "TEXT DEFAULT CURRENT_TIMESTAMP"
        self.exec(f"""CREATE TABLE IF NOT EXISTS results(id {serial}, created_at {ts}, name TEXT NOT NULL,
            seed INTEGER NOT NULL, preset TEXT NOT NULL, episode_id TEXT NOT NULL, reward {real} NOT NULL,
            f1 {real}, precision {real}, recall {real}, tp INTEGER, fp INTEGER, fn INTEGER, steps INTEGER)""")
        self.exec(f"""CREATE TABLE IF NOT EXISTS users(id {serial}, created_at {ts}, username TEXT UNIQUE NOT NULL,
            display TEXT NOT NULL, pass_hash TEXT NOT NULL)""")
        for col in ("user_id INTEGER", "clean INTEGER", "day TEXT"):
            if self.pg:
                self.exec(f"ALTER TABLE results ADD COLUMN IF NOT EXISTS {col}")
            else:
                try:
                    self.exec(f"ALTER TABLE results ADD COLUMN {col}")
                except sqlite3.OperationalError:
                    pass

    def _cursor_exec(self, sql, args):
        cur = self.conn.cursor()
        cur.execute(sql, args)
        return cur

    def exec(self, sql, args=(), fetch=False):
        sql = sql.replace("?", self.ph)
        with LOCK:
            try:
                cur = self._cursor_exec(sql, args)
            except Exception:
                if self.pg and self.conn.closed:      # переподключение после простоя Neon
                    import psycopg
                    self.conn = psycopg.connect(self.url, autocommit=True)
                    cur = self._cursor_exec(sql, args)
                else:
                    raise
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


# ------------------------------------------------------------------ безопасность
def rate(key: str, limit: int, window: int = 60):
    now = time.time()
    with LOCK:
        hits = [t for t in RATE.get(key, []) if now - t < window]
        if len(hits) >= limit:
            raise ApiError(429, "Слишком много запросов. Подождите минуту.")
        RATE[key] = hits + [now]


def hash_password(pw: str) -> str:
    salt = secrets.token_bytes(16)
    h = hashlib.scrypt(pw.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    return "scrypt$" + base64.b64encode(salt).decode() + "$" + base64.b64encode(h).decode()


def check_password(pw: str, stored: str) -> bool:
    try:
        _, s, h = stored.split("$")
        got = hashlib.scrypt(pw.encode(), salt=base64.b64decode(s), n=2 ** 14, r=8, p=1, dklen=32)
        return hmac.compare_digest(got, base64.b64decode(h))
    except Exception:
        return False


def make_token(uid: int) -> str:
    body = base64.urlsafe_b64encode(json.dumps({"uid": uid, "exp": int(time.time()) + TOKEN_TTL}).encode()).decode().rstrip("=")
    sig = hmac.new(SECRET, body.encode(), hashlib.sha256).hexdigest()
    return body + "." + sig


def read_token(token: str | None) -> int | None:
    if not token or "." not in token:
        return None
    body, sig = token.rsplit(".", 1)
    if not hmac.compare_digest(sig, hmac.new(SECRET, body.encode(), hashlib.sha256).hexdigest()):
        return None
    try:
        data = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    except Exception:
        return None
    return int(data["uid"]) if data.get("exp", 0) > time.time() else None


def user_public(row) -> dict:
    return {"id": row[0], "username": row[1], "display": row[2], "created_at": str(row[3])}


# ------------------------------------------------------------------ логика
def today() -> str:
    return dt.datetime.now(TZ).date().isoformat()


def daily_seed(day: str | None = None) -> int:
    day = day or today()
    return int(hashlib.sha256(("fin-audit-daily:" + day).encode()).hexdigest()[:8], 16) % 1_000_000


def register(body: dict, ip: str) -> dict:
    rate("auth:" + ip, 8)
    username = str(body.get("username", "")).strip().lower()
    password = str(body.get("password", ""))
    display = NAME_RE.sub("", str(body.get("display") or username))[:32].strip() or username
    if not USER_RE.match(username):
        raise ApiError(400, "Логин: 3–24 символа, только латинские буквы, цифры и _.")
    if len(password) < 8 or len(password) > 200:
        raise ApiError(400, "Пароль должен быть не короче 8 символов.")
    if get_db().exec("SELECT 1 FROM users WHERE username = ?", (username,), fetch=True):
        raise ApiError(409, "Такой логин уже занят. Выберите другой.")
    get_db().exec("INSERT INTO users(username, display, pass_hash) VALUES(?,?,?)", (username, display, hash_password(password)))
    row = get_db().exec("SELECT id, username, display, created_at FROM users WHERE username = ?", (username,), fetch=True)[0]
    return {"token": make_token(row[0]), "user": user_public(row)}


def login(body: dict, ip: str) -> dict:
    rate("auth:" + ip, 8)
    username = str(body.get("username", "")).strip().lower()
    rows = get_db().exec("SELECT id, username, display, created_at, pass_hash FROM users WHERE username = ?", (username,), fetch=True)
    if not rows or not check_password(str(body.get("password", "")), rows[0][4]):
        raise ApiError(401, "Неверный логин или пароль.")
    return {"token": make_token(rows[0][0]), "user": user_public(rows[0][:4])}


ACHIEVEMENTS = [
    ("first", "Первый аудит", "Сохранить первый результат"),
    ("positive", "В плюсе", "Получить положительную награду"),
    ("perfect", "Без единой ошибки", "F1 = 1 на компании с ошибками"),
    ("clean", "Чистые руки", "Не обвинить чистую компанию: награда выше 0.9"),
    ("tangle", "Распутал клубок", "F1 = 1 в сценарии со взаимодействующими ошибками"),
    ("thrifty", "Экономный", "Награда выше 0.8 меньше чем за 25 шагов"),
    ("daily", "Компания дня", "Пройти компанию дня"),
    ("ten", "Опытный аудитор", "Сохранить 10 результатов"),
]


def me(uid: int) -> dict:
    u = get_db().exec("SELECT id, username, display, created_at FROM users WHERE id = ?", (uid,), fetch=True)
    if not u:
        raise ApiError(401, "Сессия устарела. Войдите снова.")
    rows = get_db().exec("SELECT created_at, seed, preset, reward, f1, tp, fp, fn, steps, clean, day FROM results "
                         "WHERE user_id = ? ORDER BY id DESC LIMIT 200", (uid,), fetch=True)
    keys = ("created_at", "seed", "preset", "reward", "f1", "tp", "fp", "fn", "steps", "clean", "day")
    hist = [{k: (str(v) if k == "created_at" else v) for k, v in zip(keys, r)} for r in rows]
    n = len(hist)
    got = set()
    if n:
        got.add("first")
    for h in hist:
        if h["reward"] > 0:
            got.add("positive")
        if not h["clean"] and h["f1"] == 1:
            got.add("perfect")
        if h["clean"] and h["reward"] > 0.9:
            got.add("clean")
        if h["preset"] == "inter" and h["f1"] == 1:
            got.add("tangle")
        if h["reward"] > 0.8 and h["steps"] < 25:
            got.add("thrifty")
        if h["day"]:
            got.add("daily")
    if n >= 10:
        got.add("ten")
    best = max((h["reward"] for h in hist), default=None)
    rank = None
    if best is not None:
        rank = int(get_db().exec("SELECT COUNT(*) FROM results WHERE reward > ?", (best,), fetch=True)[0][0]) + 1
    return {"user": user_public(u[0]),
            "stats": {"runs": n, "best": best, "avg": (sum(h["reward"] for h in hist) / n) if n else None,
                      "avg_f1": (sum(h["f1"] or 0 for h in hist) / n) if n else None,
                      "found": sum(h["tp"] or 0 for h in hist), "false": sum(h["fp"] or 0 for h in hist), "rank": rank},
            "history": hist,
            "achievements": [{"id": a, "title": t, "hint": d, "done": a in got} for a, t, d in ACHIEVEMENTS]}


def submit(body: dict, ip: str, uid: int | None) -> dict:
    rate("res:" + ip, 10)
    if uid:
        u = get_db().exec("SELECT display FROM users WHERE id = ?", (uid,), fetch=True)
        if not u:
            raise ApiError(401, "Сессия устарела. Войдите снова.")
        name = u[0][0]
    else:
        name = NAME_RE.sub("", str(body.get("name", "")))[:32].strip()
        if len(name) < 2:
            raise ApiError(400, "Имя должно содержать от 2 до 32 символов.")
    try:
        seed = int(body.get("seed"))
        steps = int(body.get("steps", 0))
    except (TypeError, ValueError):
        raise ApiError(400, "Номер компании и шаги должны быть числами.")
    if not 0 <= seed <= 999_999 or not 0 <= steps <= 99:
        raise ApiError(400, "Номер компании 0–999999, шаги 0–99.")
    preset = body.get("preset")
    if preset not in PRESETS:
        raise ApiError(400, "Неизвестный сценарий.")
    ep = generate_episode(seed, PRESETS[preset])
    res = score({"episode_id": ep.episode_id, "findings": body.get("findings")}, ep.truth, ep.public, steps)
    if not res["valid"]:
        raise ApiError(400, "Выводы не прошли проверку. У каждого вывода должны быть тип, ID, сумма и валюта.")
    day = today() if (preset == "mixed" and seed == daily_seed()) else None
    get_db().exec("INSERT INTO results(name,seed,preset,episode_id,reward,f1,precision,recall,tp,fp,fn,steps,user_id,clean,day) "
                  "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                  (name, seed, preset, ep.episode_id, res["reward"], res["f1"], res["precision"], res["recall"],
                   res["tp"], res["fp"], res["fn"], steps, uid, 1 if ep.truth["clean"] else 0, day))
    if day:
        better = get_db().exec("SELECT COUNT(*) FROM results WHERE day = ? AND reward > ?", (day, res["reward"]), fetch=True)[0][0]
    else:
        better = get_db().exec("SELECT COUNT(*) FROM results WHERE reward > ?", (res["reward"],), fetch=True)[0][0]
    return {"saved": True, "rank": int(better) + 1, "daily": bool(day), "reward": res["reward"], "f1": res["f1"],
            "tp": res["tp"], "fp": res["fp"], "fn": res["fn"]}


def leaderboard(limit: int, scope: str) -> dict:
    limit = max(1, min(limit, 50))
    keys = ("name", "reward", "f1", "tp", "fp", "fn", "steps", "preset", "seed", "created_at", "registered")
    sel = "SELECT name,reward,f1,tp,fp,fn,steps,preset,seed,created_at,user_id FROM results "
    if scope == "daily":
        rows = get_db().exec(sel + "WHERE day = ? ORDER BY reward DESC, steps ASC, id ASC LIMIT ?", (today(), limit), fetch=True)
    else:
        rows = get_db().exec(sel + "ORDER BY reward DESC, steps ASC, id ASC LIMIT ?", (limit,), fetch=True)
    out = []
    for r in rows:
        d = dict(zip(keys, r))
        d["created_at"] = str(d["created_at"])
        d["registered"] = d["registered"] is not None
        out.append(d)
    return {"scope": scope, "day": today(), "daily_seed": daily_seed(), "results": out}


def stats() -> dict:
    n, avg, best = get_db().exec("SELECT COUNT(*), AVG(reward), MAX(reward) FROM results", fetch=True)[0]
    players = get_db().exec("SELECT COUNT(DISTINCT name) FROM results", fetch=True)[0][0]
    users = get_db().exec("SELECT COUNT(*) FROM users", fetch=True)[0][0]
    today_n = get_db().exec("SELECT COUNT(*) FROM results WHERE day = ?", (today(),), fetch=True)[0][0]
    return {"runs": int(n), "players": int(players), "users": int(users), "today": int(today_n),
            "avg_reward": float(avg or 0), "best_reward": float(best or 0)}


# ------------------------------------------------------------------ HTTP
class Handler(BaseHTTPRequestHandler):
    server_version = "FinAuditAPI/2.0"

    def _cors(self):
        origin = self.headers.get("Origin")
        if origin and (origin in ORIGINS or "*" in ORIGINS):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.send_header("Access-Control-Max-Age", "600")

    def _json(self, code: int, obj: dict):
        data = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _uid(self):
        auth = self.headers.get("Authorization", "")
        return read_token(auth[7:].strip()) if auth.startswith("Bearer ") else None

    def _ip(self):
        return (self.headers.get("X-Forwarded-For") or self.client_address[0]).split(",")[0].strip()

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def _handle(self, fn):
        try:
            return self._json(200, fn())
        except ApiError as e:
            return self._json(e.code, {"error": e.msg})
        except Exception as e:  # noqa: BLE001
            sys.stderr.write(f"error: {type(e).__name__}: {e}\n")
            return self._json(500, {"error": "Ошибка сервера. Попробуйте ещё раз."})

    def do_GET(self):
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path == "/api/me":
            uid = self._uid()
            if not uid:
                return self._json(401, {"error": "Войдите в аккаунт."})
            return self._handle(lambda: me(uid))
        routes = {
            "/": lambda: {"ok": True},
            "/api/health": lambda: {"ok": True, "db": "postgres" if get_db().pg else "memory"},
            "/api/stats": stats,
            "/api/daily": lambda: {"day": today(), "seed": daily_seed(), "preset": "mixed"},
            "/api/leaderboard": lambda: leaderboard(int(q.get("limit", ["20"])[0]), q.get("scope", ["all"])[0]),
        }
        if u.path in routes:
            return self._handle(routes[u.path])
        return self._json(404, {"error": "Не найдено."})

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/api/results", "/api/register", "/api/login"):
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
        ip = self._ip()
        if path == "/api/register":
            return self._handle(lambda: register(body, ip))
        if path == "/api/login":
            return self._handle(lambda: login(body, ip))
        return self._handle(lambda: submit(body, ip, self._uid()))

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))


def main():
    port = int(os.environ.get("PORT", "8000"))
    get_db()
    print(f"listening on :{port}, db={'postgres' if get_db().pg else 'memory'}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
