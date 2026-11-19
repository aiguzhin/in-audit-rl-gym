"""Конфигурация генератора: значения по умолчанию, слияние, канонический хеш."""
from __future__ import annotations

import copy
import hashlib
import json

GENERATOR_VERSION = "1.0.0"
SCHEMA_VERSION = "1.0"

ERROR_TYPES = (
    "duplicate_invoice",
    "missing_or_partial_allocation",
    "fx_conversion_error",
    "period_cutoff_error",
)
INTERACTIONS = ("partial_payment_wrong_fx", "cutoff_partial_payment_fx")

DEFAULT_CONFIG: dict = {
    "size": {
        "customers": [8, 22],
        "vendors": [5, 14],
        "prior_invoices": [4, 12],
        "period_invoices": [20, 70],
        "next_invoices": [3, 6],
        "expenses": [60, 220],
    },
    "currencies": {
        "base_pool": ["USD", "EUR", "KZT", "GBP"],
        "foreign_pool": ["USD", "EUR", "GBP", "JPY", "KWD", "CNY", "KZT"],
        "n_foreign": [1, 3],
    },
    "timezones": ["+05:00", "+03:00", "+09:00", "+00:00", "-05:00", "-03:00"],
    "years": [2025, 2026],
    # Режим чистой компании: true / false / null (тогда по clean_probability).
    "clean": None,
    "clean_probability": 0.2,
    # Независимо настраиваемые типы ошибок: [min, max] на эпизод.
    "errors": {
        "duplicate_invoice": [0, 2],
        "missing_or_partial_allocation": [0, 2],
        "fx_conversion_error": [0, 2],
        "period_cutoff_error": [0, 2],
    },
    # Сценарии взаимодействующих ошибок: [min, max] на эпизод.
    "interactions": {
        "partial_payment_wrong_fx": [0, 1],
        "cutoff_partial_payment_fx": [0, 1],
    },
    "min_issues_if_not_clean": 1,
    "max_issues": 12,
    "distractors": {
        "split_payments": True,
        "multi_invoice_payments": True,
        "refunds": True,
        "recurring": True,
        "unidentified_receipts": True,
        "boundary_timestamps": True,
    },
    # Безвредные преобразования: меняют ID и порядок, но не историю компании.
    "transform": {"id_salt": "0", "order": "time"},
    # Секретная соль закрытых прогонов (не публикуется). Входит в вывод seed.
    "secret_salt": "",
}


def deep_merge(base: dict, override: dict | None) -> dict:
    out = copy.deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = deep_merge(out[k], v)
        else:
            out[k] = copy.deepcopy(v)
    return out


def canonical_json(obj) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def resolve_config(config: dict | None) -> dict:
    cfg = deep_merge(DEFAULT_CONFIG, config)
    for t in cfg["errors"]:
        if t not in ERROR_TYPES:
            raise ValueError(f"unknown error type in config: {t}")
    for t in cfg["interactions"]:
        if t not in INTERACTIONS:
            raise ValueError(f"unknown interaction in config: {t}")
    return cfg


def story_key(seed: int, cfg: dict) -> str:
    """Ключ скрытой истории: версия + seed + конфиг без преобразований."""
    story_cfg = {k: v for k, v in cfg.items() if k != "transform"}
    return sha(canonical_json({"v": GENERATOR_VERSION, "seed": int(seed), "cfg": story_cfg}))


def config_hash(cfg: dict) -> str:
    public = {k: v for k, v in cfg.items() if k != "secret_salt"}
    return sha(canonical_json(public))[:16]
