# coding: utf-8
import operator
from collections import OrderedDict, Mapping
from functools import reduce

from expression import Imp, Equ, Not, Negative, Positive, Term, VariadicOp, Variable
from parse import parse as _


class Ruleset(Mapping):
    def __init__(self, *args, **kwargs):
        self.__dict = OrderedDict(*args, **kwargs)
        self.__hash = None

    def __getitem__(self, item):
        return self.__dict[item]

    def __iter__(self):
        return iter(self.__dict)

    def __len__(self):
        return len(self.__dict)

    def __hash__(self):
        return reduce(operator.xor, map(hash, self.__dict.items()), 0)

    def __repr__(self):
        return '{}({!r})'.format(self.__class__.__name__, self.__dict.items())

    def copy(self, *args, **kwargs):
        new_dict = self.__dict.copy()

        if args or kwargs:
            new_dict.update(OrderedDict(*args, **kwargs))

        return self.__class__(new_dict)

    def add_raw(self, a, b, bidi: bool = False):
        self.__dict[a] = b
        if bidi:
            self.__dict[b] = a

    def add(self, *rules: str) -> "Ruleset":
        res = self.copy()
        for expr in rules:
            rule = expr if isinstance(expr, Term) else _(expr)
            if isinstance(rule, Imp):
                if isinstance(rule.get_left(), VariadicOp) and rule.get_left().commutes() and rule.get_left().placeholder == "*":
                    res.add_raw(type(rule.get_left())((Variable("$@"), *rule.get_left().get_args())), type(rule.get_left())((Variable("$@"), rule.get_right())))
                res.add_raw(rule.get_left(), rule.get_right())
            elif isinstance(rule, Equ):
                res.add_raw(rule.get_left(), rule.get_right(), True)
            elif isinstance(rule, Not):
                res.add_raw(rule.elem, Negative())
            else:
                res.add_raw(rule, Positive())
            # else:
            #     raise TypeError("Invalid rule: " + str(rule))
        return res


DOUBLE_NEGATION = "!!$X -> $X"

DEF_NEGATION = [
    "!FALSE -> TRUE",
    "!TRUE  -> FALSE"
]

DEF_EQUIVALENCE = [
    "($X <-> $X) -> TRUE",
    "($X <-> $Y) -> [($X -> $Y) & ($Y -> $X)]",
]

DEF_IMPLICATION = [
    "TRUE -> $X  ⊨ $X",
    "FALSE -> $X ⊨ TRUE",
    "($X -> $Y)   <-> (!$X | $Y)"
]

DEF_CONJUNCTION = [
    "$X &* !$X   -> FALSE",
    "$X &* TRUE  -> $X",
    "$X &* FALSE -> FALSE",
    "$X# & TRUE  -> $X#",
    "$X &* FALSE -> FALSE"
]

DEF_DISJUNCTION = [
    "$X |* !$X   -> TRUE",
    "$X |* TRUE  -> TRUE",
    "$X# | FALSE -> $X#"
]

DE_MORGAN = [
    "!($X & $Y) <-> (!$X | !$Y)",
    "!($X | $Y) <-> (!$X & !$Y)"
]

DEF_QUANTIFIERS = [
    "[!∃$X P($X)] -> ∀$X !P($X)",
    "[!∀$X P($X)] -> ∃$X !P($X)",

    "[$C | ∀$X P($X)] -> ∀$X ($C | P($X))",
    "[$C | ∃$X P($X)] -> ∃$X ($C | P($X))",

    "[$C & ∀$X P($X)] -> ∀$X ($C & P($X))",
    "[$C & ∃$X P($X)] -> ∃$X ($C & P($X))",
]

DISTRIB_DNF = " ($X & $Y#  |  $X & $Z#)  <-> [$X & ($Y# | $Z#)]"
DISTRIB_CNF = "[($X | $Y#) & ($X | $Z#)] <-> [$X | ($Y# & $Z#)]"


RULES_STD = Ruleset().add(
    DOUBLE_NEGATION,
    *DEF_NEGATION,
    *DEF_EQUIVALENCE,
    *DEF_IMPLICATION,
    *DEF_CONJUNCTION,
    *DEF_DISJUNCTION,
    *DE_MORGAN,
    *DEF_QUANTIFIERS
)

RULES_DNF = RULES_STD.add(DISTRIB_DNF)
RULES_CNF = RULES_STD.add(DISTRIB_CNF)
