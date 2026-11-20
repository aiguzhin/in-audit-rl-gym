"""Тесты API: аккаунты, токены, пересчёт результата, компания дня, профиль."""
import json
import sys
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))
import server  # noqa: E402
from auditenv.generator import generate_episode  # noqa: E402


def truth_findings(seed, preset="mixed"):
    ep = generate_episode(seed, server.PRESETS[preset])
    return [{"type": i["type"], "affected_ids": i["affected_ids"], "claimed_amount_minor": i["expected_amount_minor"],
             "currency": i["currency"], "evidence_ids": i["evidence_sets"][0], "explanation": ""} for i in ep.truth["issues"]]


class TestAPI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server.db = server.DB(url="")
        server.ORIGINS[:] = ["*"]
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
        cls.base = f"http://127.0.0.1:{cls.srv.server_address[1]}"
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def setUp(self):
        server.RATE.clear()

    def req(self, path, body=None, token=None):
        h = {"Content-Type": "application/json"}
        if token:
            h["Authorization"] = "Bearer " + token
        r = urllib.request.Request(self.base + path, data=json.dumps(body).encode() if body is not None else None,
                                   headers=h, method="POST" if body is not None else "GET")
        try:
            with urllib.request.urlopen(r) as x:
                return x.status, json.loads(x.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_register_login_me(self):
        c, r = self.req("/api/register", {"username": "aigerim_1", "password": "secret-123", "display": "Айгерим"})
        self.assertEqual(c, 200, r)
        tok = r["token"]
        self.assertEqual(self.req("/api/register", {"username": "aigerim_1", "password": "secret-123"})[0], 409)
        self.assertEqual(self.req("/api/login", {"username": "aigerim_1", "password": "wrong-pass"})[0], 401)
        c, r = self.req("/api/login", {"username": "AIGERIM_1", "password": "secret-123"})
        self.assertEqual(c, 200)
        c, r = self.req("/api/results", {"seed": 2026, "preset": "mixed", "steps": 20, "findings": truth_findings(2026)}, token=tok)
        self.assertEqual(c, 200, r)
        self.assertAlmostEqual(r["reward"], 1 - 0.002 * 20)
        c, me = self.req("/api/me", token=tok)
        self.assertEqual(c, 200)
        self.assertEqual(me["user"]["display"], "Айгерим")
        self.assertEqual(me["stats"]["runs"], 1)
        done = {a["id"] for a in me["achievements"] if a["done"]}
        self.assertTrue({"first", "positive", "perfect", "thrifty"} <= done)

    def test_bad_inputs(self):
        self.assertEqual(self.req("/api/register", {"username": "x", "password": "secret-123"})[0], 400)
        self.assertEqual(self.req("/api/register", {"username": "good_name", "password": "short"})[0], 400)
        self.assertEqual(self.req("/api/me")[0], 401)
        self.assertEqual(self.req("/api/me", token="forged.token")[0], 401)
        self.assertEqual(self.req("/api/results", {"name": "Гость", "seed": 1, "preset": "nope", "steps": 1, "findings": []})[0], 400)
        self.assertEqual(self.req("/api/results", {"name": "Гость", "seed": 1, "preset": "mixed", "steps": 1, "findings": "x"})[0], 400)

    def test_server_recomputes_score(self):
        fake = truth_findings(2026)[:1]
        fake[0]["claimed_amount_minor"] += 999
        c, r = self.req("/api/results", {"name": "Хитрец", "seed": 2026, "preset": "mixed", "steps": 0, "findings": fake})
        self.assertEqual(c, 200)
        self.assertEqual(r["tp"], 0)

    def test_daily(self):
        c, d = self.req("/api/daily")
        seed = d["seed"]
        c, r = self.req("/api/results", {"name": "Гость дня", "seed": seed, "preset": "mixed", "steps": 10,
                                         "findings": truth_findings(seed)})
        self.assertTrue(r["daily"])
        c, lb = self.req("/api/leaderboard?scope=daily")
        self.assertEqual(lb["results"][0]["name"], "Гость дня")
        c, s = self.req("/api/stats")
        self.assertGreaterEqual(s["today"], 1)


if __name__ == "__main__":
    unittest.main()


class TestUsernameCheck(TestAPI):
    def test_check_username(self):
        c, r = self.req("/api/check-username?u=Free_Name")
        self.assertEqual((c, r["valid"], r["available"], r["username"]), (200, True, True, "free_name"))
        self.req("/api/register", {"username": "taken_1", "password": "secret-123"})
        self.assertFalse(self.req("/api/check-username?u=taken_1")[1]["available"])
        bad = self.req("/api/check-username?u=ab")[1]
        self.assertFalse(bad["valid"])
