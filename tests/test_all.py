"""Тесты среды, сопоставления и награды. Запуск: python -m unittest discover -s tests"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from auditenv import calculator, matcher                               # noqa: E402
from auditenv.checks import paired_check, verify_episode                # noqa: E402
from auditenv.env import AuditEnv                                       # noqa: E402
from auditenv.generator import generate_episode                         # noqa: E402
from auditenv.policies import FlagAll, Oracle, SimpleReconciler         # noqa: E402
from auditenv.runner import run_inprocess                               # noqa: E402

ERR_CFG = {"clean": False, "errors": {t: [1, 1] for t in ("duplicate_invoice", "missing_or_partial_allocation",
                                                            "fx_conversion_error", "period_cutoff_error")}}
CLEAN_CFG = {"clean": True}
INTER_CFG = {"clean": False, "interactions": {"partial_payment_wrong_fx": [1, 1], "cutoff_partial_payment_fx": [1, 1]}}


def findings_from_truth(truth):
    return [{"type": i["type"], "affected_ids": i["affected_ids"], "claimed_amount_minor": i["expected_amount_minor"],
             "currency": i["currency"], "evidence_ids": i["evidence_sets"][0], "explanation": "x"}
            for i in truth["issues"]]


def sc(ep, findings, steps=0):
    return matcher.score({"episode_id": ep.episode_id, "findings": findings}, ep.truth, ep.public, steps)


class TestGenerator(unittest.TestCase):
    def test_reproducible(self):
        a, b = generate_episode(7, ERR_CFG), generate_episode(7, ERR_CFG)
        self.assertEqual(json.dumps([a.public, a.truth], sort_keys=True), json.dumps([b.public, b.truth], sort_keys=True))

    def test_four_types_independent(self):
        for t in ERR_CFG["errors"]:
            cfg = {"clean": False, "interactions": {"partial_payment_wrong_fx": [0, 0], "cutoff_partial_payment_fx": [0, 0]},
                   "errors": {x: ([2, 2] if x == t else [0, 0]) for x in ERR_CFG["errors"]}}
            ep = generate_episode(11, cfg)
            self.assertEqual({i["type"] for i in ep.truth["issues"]}, {t}, t)

    def test_clean_and_interactions(self):
        self.assertEqual(generate_episode(3, CLEAN_CFG).truth["issues"], [])
        scen = {i["scenario"] for i in generate_episode(3, INTER_CFG).truth["issues"]}
        self.assertTrue({"partial_payment_wrong_fx", "cutoff_partial_payment_fx"} <= scen)

    def test_episodes_valid(self):
        for seed in range(25):
            for cfg in (ERR_CFG, CLEAN_CFG, INTER_CFG, {}):
                v = verify_episode(generate_episode(seed, cfg))
                self.assertTrue(v["ok"], (seed, cfg, v["problems"]))

    def test_paired(self):
        for seed in range(5):
            r = paired_check(seed, INTER_CFG)
            self.assertTrue(r["ok"], r["problems"])

    def test_sizes(self):
        m = generate_episode(5, {}).public["manifest"]["counts"]
        self.assertTrue(200 <= m["ledger"] <= 2000 and 20 <= m["documents"] <= 200, m)


class TestEnvContract(unittest.TestCase):
    def setUp(self):
        self.env = AuditEnv(mode="train")
        self.obs, self.info = self.env.reset(1, ERR_CFG)

    def test_reset_obs(self):
        for k in ("task", "manifest", "policy", "remaining_steps"):
            self.assertIn(k, self.obs)
        self.assertNotIn("seed", json.dumps(self.info))

    def test_page_limit_and_cursor(self):
        o, *_ = self.env.step({"name": "list_records", "args": {"table": "ledger", "limit": 50}})
        self.assertEqual(len(o["result"]["records"]), 50)
        cur = o["result"]["next_cursor"]
        o2, *_ = self.env.step({"name": "list_records", "args": {"table": "ledger", "cursor": cur}})
        o3, *_ = self.env.step({"name": "list_records", "args": {"table": "ledger", "cursor": cur}})
        self.assertEqual(o2["result"], o3["result"])          # стабильные курсоры
        o4, *_ = self.env.step({"name": "list_records", "args": {"table": "ledger", "limit": 51}})
        self.assertEqual(o4["error"]["code"], "bad_args")

    def test_errors_consume_step(self):
        o, r, term, trunc, _ = self.env.step({"name": "get_record", "args": {"table": "ledger", "id": "NOPE"}})
        self.assertEqual(o["error"]["code"], "not_found")
        self.assertEqual(o["remaining_steps"], 99)
        o, *_ = self.env.step({"name": "rm -rf", "args": {}})
        self.assertEqual(o["error"]["code"], "unknown_action")
        o, *_ = self.env.step("not json")
        self.assertEqual(o["remaining_steps"], 97)

    def test_step_limit_truncates(self):
        for i in range(100):
            o, r, term, trunc, info = self.env.step({"name": "calculator", "args": {"expression": "1+1"}})
        self.assertTrue(trunc and not term)
        self.assertEqual(self.env.grader_result()["result"]["tp"], 0)   # пустой итоговый ответ
        o, r, term, *_ = self.env.step({"name": "calculator", "args": {"expression": "1"}})
        self.assertEqual(o["error"]["code"], "episode_finished")

    def test_time_limit(self):
        t = [0.0]
        env = AuditEnv(clock=lambda: t[0])
        env.reset(1, ERR_CFG)
        t[0] = 61
        o, r, term, trunc, _ = env.step({"name": "calculator", "args": {"expression": "1"}})
        self.assertTrue(trunc)

    def test_submit_terminates_and_resubmit(self):
        ep = self.env._ep
        o, r, term, trunc, info = self.env.step({"name": "submit", "args": {"findings": {
            "episode_id": ep.episode_id, "findings": findings_from_truth(ep.truth)}}})
        self.assertTrue(term and not trunc)
        self.assertAlmostEqual(r, 1.0)
        o, r2, *_ = self.env.step({"name": "submit", "args": {"findings": {"episode_id": ep.episode_id, "findings": []}}})
        self.assertEqual(r2, 0.0)
        self.assertAlmostEqual(self.env.grader_result()["result"]["reward"], 1.0)

    def test_invalid_submission(self):
        o, r, term, *_ = self.env.step({"name": "submit", "args": {"findings": {"episode_id": "x", "findings": "bad"}}})
        self.assertTrue(term)
        self.assertEqual(r, -1.0)
        self.assertEqual(self.env.grader_result()["events"][0]["event"], "invalid_submission")

    def test_eval_mode_hides_reward(self):
        env = AuditEnv(mode="eval")
        env.reset(1, ERR_CFG)
        ep = env._ep
        o, r, term, trunc, info = env.step({"name": "submit", "args": {"findings": {
            "episode_id": ep.episode_id, "findings": findings_from_truth(ep.truth)}}})
        self.assertEqual((r, info), (0.0, {}))
        self.assertEqual(env.grader_result()["result"]["reward"], 1.0)

    def test_no_leakage(self):
        ep = generate_episode(2, INTER_CFG)
        for pol in (SimpleReconciler(), FlagAll()):
            traj, _ = run_inprocess(pol, 2, None, episode=ep)
            text = json.dumps([t["observation"] for t in traj])
            for bad in ("issue_id", "evidence_sets", "expected_amount", "provenance", "truth", "scenario"):
                self.assertNotIn(bad, text)
            for iss in ep.truth["issues"]:
                self.assertNotIn(iss["issue_id"], text)

    def test_reset_isolation(self):
        self.env.step({"name": "calculator", "args": {"expression": "1"}})
        o, _ = self.env.reset(1, ERR_CFG)
        self.assertEqual(o["remaining_steps"], 100)
        self.assertEqual(self.env.trajectory[-1]["step"], 0)

    def test_calculator(self):
        self.assertEqual(calculator.evaluate("(12.5 + 7.5) * 3 / 4"), "15")
        for bad in ("__import__('os')", "open('x')", "2**10", "1/0", "a+1", "1" * 300):
            with self.assertRaises(calculator.CalcError):
                calculator.evaluate(bad)


class TestReward(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ep = generate_episode(4, ERR_CFG)
        cls.clean = generate_episode(4, CLEAN_CFG)

    def test_correct_beats_silence_on_errors(self):
        self.assertGreater(sc(self.ep, findings_from_truth(self.ep.truth), 30)["reward"], sc(self.ep, [], 0)["reward"])

    def test_silence_beats_false_accusation_on_clean(self):
        fake = findings_from_truth(self.ep.truth)[:1]
        self.assertEqual(sc(self.clean, [], 10)["f1"], 1.0)
        self.assertGreater(sc(self.clean, [], 10)["reward"], sc(self.clean, fake, 0)["reward"])

    def test_duplicates_no_gain(self):
        f = findings_from_truth(self.ep.truth)
        self.assertLess(sc(self.ep, f + f, 0)["reward"], sc(self.ep, f, 0)["reward"])
        self.assertEqual(sc(self.ep, f + f, 0)["tp"], len(f))

    def test_flag_all_bad(self):
        _, res = run_inprocess(FlagAll(), 4, None, episode=self.ep)
        self.assertLess(res["reward"], 0)

    def test_step_cost_small(self):
        f = findings_from_truth(self.ep.truth)
        a, b = sc(self.ep, f, 10)["reward"], sc(self.ep, f, 60)["reward"]
        self.assertGreater(a, b)
        self.assertLess(a - b, 0.11)

    def test_guessed_ids_wrong_currency_bad_evidence(self):
        f = findings_from_truth(self.ep.truth)[0]
        g = dict(f, affected_ids=["INV-GUESS1"])
        c = dict(f, currency="XXX")
        e = dict(f, evidence_ids=[f["evidence_ids"][0]])
        a = dict(f, claimed_amount_minor=f["claimed_amount_minor"] + 1000)
        for bad in (g, c, e, a):
            self.assertEqual(sc(self.ep, [bad])["tp"], 0)

    def test_explanation_text_irrelevant(self):
        f = findings_from_truth(self.ep.truth)
        g = [dict(x, explanation="I am absolutely certain, trust me") for x in f]
        self.assertEqual(sc(self.ep, f)["reward"], sc(self.ep, g)["reward"])

    def test_invalid_structures(self):
        f = findings_from_truth(self.ep.truth)[0]
        for bad in ([dict(f, claimed_amount_minor=1.5)], [dict(f, explanation="x" * 1001)],
                    [dict(f, evidence_ids=["a"] * 11)], [f] * 31, [{"type": "x"}]):
            self.assertEqual(sc(self.ep, bad)["reward"], -1.0)

    def test_doc_id_aliases(self):
        f = findings_from_truth(self.ep.truth)
        self.assertEqual(sc(self.ep, f)["tp"], len(f))

    def test_oracle_max(self):
        _, res = run_inprocess(Oracle(self.ep.truth), 4, None, episode=self.ep)
        self.assertEqual(res["reward"], 1.0)


if __name__ == "__main__":
    unittest.main()
