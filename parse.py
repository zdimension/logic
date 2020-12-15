# coding: utf-8
from typing import List, Optional

from expression import *

OPS = "|&!()→*"
BINOPS = {
    "&": And,
    "|": Or,
    "→": Imp,
}
CONSTS = {
    "FALSE": Negative,
    "TRUE": Positive
}


@dataclass
class Token:
    OP = 0
    VAR = 1

    val: str
    type: int


def tokenize(expr: str) -> List[Token]:
    expr = expr.replace(" ", "").replace("=>", "→")
    tokens = []

    pos = 0
    while pos < len(expr):
        cur = expr[pos]
        token_type = None
        if cur in OPS:
            lg = 1
            token_type = Token.OP
        else:
            npos = pos + 1
            while npos < len(expr) and expr[npos] not in OPS:
                npos += 1
            lg = npos - pos
            token_type = Token.VAR
        tokens.append(Token(expr[pos:pos + lg], token_type))
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

    def expect(*vals: Iterable[str]) -> bool:
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
        if tok.val == "(":
            read()
            res = read_expr()
            assert expect(")"), "Unclosed parenthesis"
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
                return NamedFunction(name, tuple(args))
            if name[0].isupper():
                return Variable(name)
            else:
                return Constant(name)
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

    return read_expr()
