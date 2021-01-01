# coding: utf-8
from typing import List, Optional

from expression import *

NEGATION = "!"
BINOPS = {
    "&": And,
    "|": Or,
    "→": Imp,
    "↔": Equ,
    "⊨": Imp,
    "≔": Equ
}
PARENS = {
    "(": ")",
    "[": "]"
}
CONSTS = {
    "⊥": Negative,
    "⊤": Positive
}
QUANTIFIERS = {
    "∀": Universal,
    "∃": Existential
}
WILDCARDS = [
    "*"
]
COMMA = ","
OPS = [*BINOPS, *PARENS, *PARENS.values(), COMMA, NEGATION, *WILDCARDS, *QUANTIFIERS]



@dataclasses.dataclass(frozen=True)
class Token:
    OP = 0
    VAR = 1
    LITERAL = 2

    val: str
    type: int


CHAR_LUT = {
    ("=>", "->", "⊃", "⟹"): "→",
    ("<=>", "<→", "==", "=", "≡"): "↔",
    ("&&", "∧", "·"): "&",
    ("||", "∨", "+"): "|",
    ("¬", "~"): "!"
}

STR_LUT = {
    ("FALSE", "0"): "⊥",
    ("TRUE", "1"): "⊤"
}


def apply_lut(s: str, lut) -> str:
    for k, v in lut.items():
        if type(k) == str:
            k = [k]
        for kk in k:
            s = s.replace(kk, v)
    return s


def tokenize(expr: str) -> List[Token]:
    expr = apply_lut(expr, CHAR_LUT)

    tokens = []

    pos = 0
    while pos < len(expr):
        cur = expr[pos]
        lg = 1
        if not cur.isspace():
            if cur in OPS:
                token_type = Token.OP
            else:
                npos = pos + 1
                while npos < len(expr) and expr[npos] not in OPS and not expr[npos].isspace():
                    npos += 1
                lg = npos - pos
                token_type = Token.VAR
            tokens.append(Token(apply_lut(expr[pos:pos + lg], STR_LUT), token_type))
        pos += lg
    return tokens


def parse(expr: str) -> Term:
    tokens = tokenize(expr)
    pos = 0

    def die(tok: Token):
        raise SyntaxError("Unexpected token: " + str(tok))

    def peek() -> Optional[Token]:
        if pos < len(tokens):
            return tokens[pos]
        return None

    def expect(*vals: str) -> bool:
        cur = peek()
        if cur and cur.val in vals:
            read()
            return True
        return False

    def read() -> Token:
        nonlocal pos
        if pos >= len(expr):
            raise SyntaxError("Unexpected EOL")
        pos += 1
        return tokens[pos - 1]

    def read_term() -> Term:
        tok = peek()
        if tok.val == "!":
            read()
            return Not(read_term())
        if tok.val in PARENS:
            read()
            res = read_expr()
            assert expect(PARENS[tok.val]), "Unclosed parenthesis"
            return res
        if tok.type == Token.VAR:
            name = read().val
            if name in CONSTS:
                return CONSTS[name]()
            if expect("("):
                args = [read_expr()]
                while expect(","):
                    args.append(read_expr())
                assert expect(")"), "Unclosed parenthesis"
                return NamedPredicate(name, tuple(args))
            if name[0].islower():
                return Constant(name)
            else:
                return Variable(name)
        if tok.val in QUANTIFIERS:
            read()
            var = read()
            assert var.type == Token.VAR and not var.val[0].islower(), "Expected variable after quantifier"
            qexpr = read_expr()
            return QUANTIFIERS[tok.val](Variable(var.val), qexpr)
        die(tok)

    def read_binop(operator: str, clazz: type, left_func: callable):
        def reader() -> Term:
            left = left_func()
            while expect(operator):
                ph = expect("*")
                args = [(left, reader())]
                if ph:
                    args.append("*")
                left = clazz(*args)
            return left

        return reader

    binop_funcs = [read_term]
    for op, cl in BINOPS.items():
        binop_funcs.append(read_binop(op, cl, binop_funcs[-1]))

    def read_expr() -> Term:
        return binop_funcs[-1]()

    res = read_expr()

    assert peek() is None, die(peek())

    return res
