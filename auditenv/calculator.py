"""Калькулятор: только десятичная арифметика + - * / и скобки. Не eval, не код, не файлы."""
from __future__ import annotations

from decimal import Decimal, DivisionByZero, InvalidOperation, localcontext

MAX_LEN = 200
MAX_DEPTH = 32
MAX_DIGITS = 40


class CalcError(ValueError):
    pass


def evaluate(expr) -> str:
    if not isinstance(expr, str):
        raise CalcError("expression must be a string")
    if len(expr) > MAX_LEN:
        raise CalcError("expression too long")
    allowed = set("0123456789.+-*/() ")
    if any(ch not in allowed for ch in expr):
        raise CalcError("only digits, '.', + - * / ( ) and spaces are allowed")
    tokens = []
    i = 0
    while i < len(expr):
        ch = expr[i]
        if ch == " ":
            i += 1
        elif ch.isdigit() or ch == ".":
            j = i
            while j < len(expr) and (expr[j].isdigit() or expr[j] == "."):
                j += 1
            num = expr[i:j]
            if num.count(".") > 1 or num == "." or len(num) > MAX_DIGITS:
                raise CalcError("bad number")
            tokens.append(("n", Decimal(num)))
            i = j
        else:
            tokens.append(("o", ch))
            i += 1
    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else ("e", None)

    def take():
        nonlocal pos
        t = peek()
        pos += 1
        return t

    def expr_(d):
        if d > MAX_DEPTH:
            raise CalcError("expression too deep")
        v = term(d)
        while peek() in (("o", "+"), ("o", "-")):
            op = take()[1]
            r = term(d)
            v = v + r if op == "+" else v - r
        return v

    def term(d):
        v = factor(d)
        while peek() in (("o", "*"), ("o", "/")):
            op = take()[1]
            r = factor(d)
            if op == "*":
                v = v * r
            else:
                if r == 0:
                    raise CalcError("division by zero")
                v = v / r
        return v

    def factor(d):
        t = take()
        if t == ("o", "-"):
            return -factor(d + 1)
        if t == ("o", "+"):
            return factor(d + 1)
        if t[0] == "n":
            return t[1]
        if t == ("o", "("):
            v = expr_(d + 1)
            if take() != ("o", ")"):
                raise CalcError("missing ')'")
            return v
        raise CalcError("syntax error")

    with localcontext() as ctx:
        ctx.prec = 34
        ctx.Emax = 10 ** 6
        ctx.Emin = -(10 ** 6)
        try:
            if not tokens:
                raise CalcError("empty expression")
            v = expr_(0)
            if pos != len(tokens):
                raise CalcError("syntax error")
        except (InvalidOperation, DivisionByZero, OverflowError):
            raise CalcError("arithmetic error")
        out = format(v.normalize(), "f")
        if len(out) > 80:
            raise CalcError("result too large")
        return out
