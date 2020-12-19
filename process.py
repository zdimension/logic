# coding: utf-8
import itertools
from functools import lru_cache

from expression import *
from rules import RULES_DNF as RULES
from unification import find_unifications


@lru_cache(maxsize=32)
def simplify_basic(term: Term) -> Term:
    if term.is_atomic():
        return term

    if term in RULES:
        return RULES[term]

    if isinstance(term, VariadicOp) and term.arity() == 1:
        return list(term.args)[0]

    return term


@lru_cache(maxsize=32)
def simplify_deep(term: Term) -> Term:
    term = simplify_basic(term)

    return term.map_fields(simplify)


@lru_cache(maxsize=32)
def find_forms(term: Term):
    term = simplify_basic(term)

    results = {term}

    return results


@lru_cache(maxsize=32)
def simplify(term: Term) -> Term:
    term = simplify_deep(term)
    history = [term]
    while True:
        rules_simp = set(dest.apply_subs(unif) for src, dest in RULES.items() for unif in find_unifications(term, src))
        potential = list(sorted(filter(lambda r: r and r != term, (simplify_deep(item) for item in itertools.chain(
            [term],
            rules_simp))), key=lambda r: len(list(r.get_children()))))
        for choice in potential:
            if choice in history:
                # print([str(x) for x in history])
                return term
            term = choice
            history.append(choice)
            break
        else:
            break

    return simplify_deep(term) or term


