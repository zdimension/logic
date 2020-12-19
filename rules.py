# coding: utf-8
from collections import OrderedDict

from expression import Imp, Equ
from parse import parse as _


class Ruleset(OrderedDict):
    def add_raw(self, a, b, bidi: bool = False):
        self[a] = b
        if bidi:
            self[b] = a

    def add(self, *rules: str) -> "Ruleset":
        res = self.copy()
        for expr in rules:
            rule = _(expr)
            if isinstance(rule, Imp):
                res.add_raw(rule.get_left(), rule.get_right())
            elif isinstance(rule, Equ):
                res.add_raw(rule.get_left(), rule.get_right(), True)
            else:
                raise TypeError("Invalid rule: " + str(rule))
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
    "$X &* FALSE -> FALSE"
]

DEF_DISJUNCTION = [
    "$X |* !$X   -> TRUE",
    "$X |* TRUE  -> TRUE",
    "$X |* FALSE -> $X"
]

DE_MORGAN = [
    "!($X & $Y) <-> (!$X | !$Y)",
    "!($X | $Y) <-> (!$X & !$Y)"
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
    *DE_MORGAN
)

RULES_DNF = RULES_STD.add(DISTRIB_DNF)
RULES_CNF = RULES_STD.add(DISTRIB_CNF)
