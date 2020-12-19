# coding: utf-8
import itertools
from functools import lru_cache

from expression import *
from rules import Ruleset, RULES_DNF
from unify import find_unifications


@lru_cache(maxsize=32)
def simplify_basic(term: Term, rules: Ruleset = RULES_DNF) -> Term:
    if term.is_atomic():
        return term

    if term in rules:
        return rules[term]

    if isinstance(term, VariadicOp) and term.arity() == 1:
        return list(term.args)[0]

    return term


@lru_cache(maxsize=32)
def simplify_deep(term: Term, rules: Ruleset = RULES_DNF) -> Term:
    term = simplify_basic(term, rules)

    return term.map_fields(lambda t: simplify(t, rules))


@lru_cache(maxsize=32)
def simplify(term: Term, rules: Ruleset = RULES_DNF) -> Term:
    term = simplify_deep(term, rules)
    history = [term]
    while True:
        rules_simp = set(dest.apply_subs(unif) for src, dest in rules.items() for unif in find_unifications(term, src))
        potential = list(sorted(filter(lambda r: r and r != term, (simplify_deep(item) for item in itertools.chain(
            [term],
            rules_simp))), key=lambda r: len(list(r.get_children()))))
        for choice in potential:
            if choice in history:
                return term
            term = choice
            history.append(choice)
            break
        else:
            break

    return simplify_deep(term) or term


