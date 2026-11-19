"""Общий matcher и терминальная награда (раздел 05 кейса). Публичный код.

Нормализация
  * type: str.strip().lower()
  * affected_ids: множество строк после strip; doc_id переводится в invoice_id/payment_id
  * evidence_ids: множество строк после strip; invoice_id/payment_id переводится в doc_id
  * currency: strip().upper()
  * claimed_amount_minor: целое (bool/float/строка = неверная структура); сравнивается |x|
Допуски: tolerance_minor из эталона (опубликованы в policy.json по типам).
TP: тип, канонические affected_ids (точное равенство множеств), |сумма - эталон| <= допуск,
    валюта, и evidence_ids содержат хотя бы один полный допустимый набор доказательств.
Сопоставление взаимно однозначное: максимальное паросочетание (Кун), выводы обходятся по порядку
подачи, эталон — по порядку issue_id. При неоднозначности выигрывает более ранний вывод.
Несопоставленные и повторные выводы = FP, несопоставленный эталон = FN.
"""
from __future__ import annotations

MAX_FINDINGS = 30
MAX_EVIDENCE = 10
MAX_EXPLANATION = 1000
MAX_AFFECTED = 10
STEP_COST = 0.002
REQUIRED = ("type", "affected_ids", "claimed_amount_minor", "currency", "evidence_ids", "explanation")


class InvalidSubmission(ValueError):
    pass


def _is_int(x) -> bool:
    return isinstance(x, int) and not isinstance(x, bool)


def validate(submission, episode_id: str) -> list[dict]:
    """Проверка структуры. Любое нарушение -> InvalidSubmission (эпизод завершается с наградой -1)."""
    if not isinstance(submission, dict):
        raise InvalidSubmission("submission must be an object")
    if set(submission) - {"episode_id", "findings"}:
        raise InvalidSubmission("unexpected top-level keys")
    if submission.get("episode_id") != episode_id:
        raise InvalidSubmission("episode_id mismatch")
    fs = submission.get("findings")
    if not isinstance(fs, list):
        raise InvalidSubmission("findings must be a list")
    if len(fs) > MAX_FINDINGS:
        raise InvalidSubmission("too many findings")
    for f in fs:
        if not isinstance(f, dict) or set(f) != set(REQUIRED):
            raise InvalidSubmission("finding must have exactly the required keys")
        if not isinstance(f["type"], str) or not isinstance(f["currency"], str):
            raise InvalidSubmission("type/currency must be strings")
        if not _is_int(f["claimed_amount_minor"]):
            raise InvalidSubmission("claimed_amount_minor must be an integer")
        for key, cap in (("affected_ids", MAX_AFFECTED), ("evidence_ids", MAX_EVIDENCE)):
            v = f[key]
            if not isinstance(v, list) or len(v) > cap or not all(isinstance(x, str) for x in v):
                raise InvalidSubmission(f"{key} must be a list of <= {cap} strings")
        if not f["affected_ids"]:
            raise InvalidSubmission("affected_ids must not be empty")
        if not isinstance(f["explanation"], str) or len(f["explanation"]) > MAX_EXPLANATION:
            raise InvalidSubmission("explanation must be a string <= 1000 chars")
    return fs


def build_aliases(public: dict) -> tuple[dict, dict]:
    """doc_id -> бизнес-ID (для affected_ids) и бизнес-ID -> doc_id (для evidence_ids)."""
    to_business, to_doc = {}, {}
    for i in public["invoices"]:
        to_business[i["doc_id"]] = i["invoice_id"]
        to_doc[i["invoice_id"]] = i["doc_id"]
    for p in public["payments"]:
        to_business[p["doc_id"]] = p["payment_id"]
        to_doc[p["payment_id"]] = p["doc_id"]
    return to_business, to_doc


def normalize(f: dict, aliases: tuple[dict, dict]) -> dict:
    to_business, to_doc = aliases
    aff = frozenset(to_business.get(x.strip(), x.strip()) for x in f["affected_ids"])
    ev = frozenset(to_doc.get(x.strip(), x.strip()) for x in f["evidence_ids"])
    return {"type": f["type"].strip().lower(), "affected": aff, "amount": abs(int(f["claimed_amount_minor"])),
            "currency": f["currency"].strip().upper(), "evidence": ev}


def is_tp(nf: dict, issue: dict) -> tuple[bool, str]:
    if nf["type"] != issue["type"]:
        return False, "type"
    if nf["affected"] != frozenset(issue["affected_ids"]):
        return False, "affected_ids"
    if nf["currency"] != issue["currency"]:
        return False, "currency"
    if abs(nf["amount"] - issue["expected_amount_minor"]) > issue["tolerance_minor"]:
        return False, "amount"
    if not any(set(es) <= nf["evidence"] for es in issue["evidence_sets"]):
        return False, "evidence"
    return True, "ok"


def match(findings: list[dict], truth: dict, public: dict) -> dict:
    aliases = build_aliases(public)
    nfs = [normalize(f, aliases) for f in findings]
    issues = sorted(truth["issues"], key=lambda i: i["issue_id"])
    adj = [[j for j, iss in enumerate(issues) if is_tp(nf, iss)[0]] for nf in nfs]
    owner = [-1] * len(issues)

    def try_assign(i, seen):
        for j in adj[i]:
            if j in seen:
                continue
            seen.add(j)
            if owner[j] == -1 or try_assign(owner[j], seen):
                owner[j] = i
                return True
        return False

    for i in range(len(nfs)):
        try_assign(i, set())
    matched = {owner[j]: j for j in range(len(issues)) if owner[j] != -1}
    tp = len(matched)
    fp = len(nfs) - tp
    fn = len(issues) - tp
    # диагностика (только оценщику): почему вывод не совпал
    reasons = []
    for i, nf in enumerate(nfs):
        if i in matched:
            reasons.append({"finding": i, "result": "TP", "issue_id": issues[matched[i]]["issue_id"]})
            continue
        order = ["type", "affected_ids", "currency", "amount", "evidence", "ok"]
        best, rank = "no_issues_in_truth", -1
        for iss in issues:
            why = is_tp(nf, iss)[1]
            if order.index(why) > rank:
                best, rank = why, order.index(why)
        if best == "ok":
            best = "duplicate_or_already_matched"
        reasons.append({"finding": i, "result": "FP", "closest_failure": best})
    missed = [issues[j]["issue_id"] for j in range(len(issues)) if owner[j] == -1]
    return {"tp": tp, "fp": fp, "fn": fn, "per_finding": reasons, "missed_issue_ids": missed}


def metrics(tp: int, fp: int, fn: int) -> dict:
    p = tp / (tp + fp) if (tp + fp) else 0.0
    r = tp / (tp + fn) if (tp + fn) else 0.0
    if tp + fn == 0:                     # эталон пуст
        f1 = 1.0 if fp == 0 else 0.0
    else:
        f1 = 2 * tp / (2 * tp + fp + fn)
    return {"precision": p, "recall": r, "f1": f1}


def terminal_reward(f1: float, inspection_steps: int) -> float:
    return max(-1.0, min(1.0, 2 * f1 - 1 - STEP_COST * inspection_steps))


def score(submission, truth: dict, public: dict, inspection_steps: int) -> dict:
    """Итог для оценщика: метрики, награда, диагностика. Неверная структура -> награда -1."""
    try:
        findings = validate(submission, truth["episode_id"])
    except InvalidSubmission as e:
        return {"valid": False, "error": str(e), "reward": -1.0, "tp": 0, "fp": 0,
                "fn": len(truth["issues"]), "precision": 0.0, "recall": 0.0, "f1": 0.0,
                "inspection_steps": inspection_steps}
    m = match(findings, truth, public)
    met = metrics(m["tp"], m["fp"], m["fn"])
    return {"valid": True, "reward": terminal_reward(met["f1"], inspection_steps), **met,
            "tp": m["tp"], "fp": m["fp"], "fn": m["fn"], "inspection_steps": inspection_steps,
            "per_finding": m["per_finding"], "missed_issue_ids": m["missed_issue_ids"]}
