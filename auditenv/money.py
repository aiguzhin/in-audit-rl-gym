"""Деньги, валюты, курсы и время.

Все суммы — целые минимальные единицы (int). Курсы — Decimal из десятичных строк.
Округление при конвертации — ROUND_HALF_UP до минимальной единицы целевой валюты.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal, localcontext

CURRENCY_EXPONENTS = {
    "USD": 2, "EUR": 2, "GBP": 2, "KZT": 2, "CNY": 2, "JPY": 0, "KWD": 3,
}

# Ориентировочная стоимость 1 единицы валюты в USD (только для генерации вымышленных курсов).
USD_VALUE = {
    "USD": Decimal("1"), "EUR": Decimal("1.08"), "GBP": Decimal("1.27"),
    "KZT": Decimal("0.0021"), "CNY": Decimal("0.14"), "JPY": Decimal("0.0067"),
    "KWD": Decimal("3.25"),
}

ROUNDING = "ROUND_HALF_UP"


def exponent(currency: str) -> int:
    return CURRENCY_EXPONENTS[currency]


def convert_minor(amount_minor: int, src: str, dst: str, rate: Decimal | str) -> int:
    """Конвертирует amount_minor (src) в минимальные единицы dst по курсу rate (dst за 1 src)."""
    if src == dst:
        return int(amount_minor)
    rate = Decimal(str(rate))
    with localcontext() as ctx:
        ctx.prec = 50
        major = Decimal(int(amount_minor)).scaleb(-exponent(src))
        value = (major * rate).scaleb(exponent(dst))
        return int(value.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def conversion_resolution(src: str, dst: str, rate: Decimal | str) -> int:
    """Сколько минимальных единиц src может отображаться в одну единицу dst (+1 на округление).

    Используется как допуск при восстановлении суммы в валюте платежа по сумме в базовой валюте.
    """
    if src == dst:
        return 0
    rate = Decimal(str(rate))
    per_unit = Decimal(1).scaleb(exponent(src) - exponent(dst)) / rate
    return int(per_unit.to_integral_value(rounding="ROUND_CEILING")) + 1


def fmt_rate(value: Decimal) -> str:
    """Курс как десятичная строка с 6 значащими цифрами (без экспоненты)."""
    q = Decimal(value)
    adjusted = q.adjusted()
    places = max(0, 6 - adjusted - 1)
    s = format(q.quantize(Decimal(1).scaleb(-places), rounding=ROUND_HALF_UP), "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


# ---------------------------------------------------------------- время

def parse_tz(offset: str) -> timezone:
    """'+05:00' -> timezone(timedelta(hours=5))."""
    sign = 1 if offset[0] == "+" else -1
    hh, mm = offset[1:].split(":")
    return timezone(sign * timedelta(hours=int(hh), minutes=int(mm)))


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def parse_iso(s: str) -> datetime:
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        raise ValueError("timestamp without offset")
    return dt


def local_date(ts: str, tz_offset: str) -> date:
    """Дата документа в часовом поясе компании (по политике — для курса и периода)."""
    return parse_iso(ts).astimezone(parse_tz(tz_offset)).date()
