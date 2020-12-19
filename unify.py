# coding: utf-8

# deterministic
import dataclasses
import itertools
from functools import lru_cache
from typing import Iterable, Tuple, Dict

from expression import Term, Constant, Variable, Predicate, VariadicOp, NamedPredicate

Unification = Dict[Term, Term]
Unifications = Iterable[Unification]


def unify_args(test: Iterable[Tuple[Term, Term]], res=None, bidi: bool = False) -> Unifications:
    for a1, a2 in test:
        if not (subs := find_unifications(a1, a2, bidi)):
            return []  # no unification
        choices = []
        for sub in subs:
            if res is None:
                nres = sub
            else:
                if any(src in res and dest != res[src] for src, dest in sub.items()):
                    continue  # conflict
                nres = res.copy()
                nres.update(sub)
            new_args = test[1:]
            if bidi:
                new_args = [(b1.apply_subs(nres), b2.apply_subs(nres)) for b1, b2 in new_args[1:]]
            choices.extend(unify_args(new_args, nres, bidi))
        return choices
    else:
        return [res]


@lru_cache(maxsize=32)
def find_unifications(haystack: Term, needle: Term, bidi: bool = False) -> Unifications:
    return [dict(t) for t in {frozenset(d.items()) for d in gen_unifications(haystack, needle, bidi)}]


def gen_unifications(haystack: Term, needle: Term, bidi: bool = False) -> Unifications:
    if haystack == needle:
        return [{}]

    # placeholders can be unified with anything
    if isinstance(needle, Constant) and needle.name[0] == "$":
        return [{needle: haystack}]

    # can unify except if both are constants and their name is different
    if isinstance(haystack, Constant) and isinstance(needle, Constant):
        return []

    if bidi:
        if isinstance(haystack, Variable) or isinstance(needle, Variable):
            l1, l2 = sorted((haystack, needle), key=lambda t: isinstance(t, Variable))
            if l2 in l1.get_children():  # can't unify x and f(x)
                return {}
            return [{l2: l1}]

    if isinstance(haystack, Predicate) and isinstance(needle, Predicate):
        return unify_functions(haystack, needle, bidi)

    return []


def unify_functions(haystack: Predicate, needle: Predicate, bidi: bool = False) -> Unifications:
    # can't unify two different builtin functions except if we're targetting the base type
    if type(haystack) != type(needle):
        return []

    if isinstance(haystack, NamedPredicate) and isinstance(needle, NamedPredicate):
        if haystack.name != needle.name:  # can't unify two different functions
            return []

    if haystack.arity() != needle.arity():  # can't unify functions with different arity
        if isinstance(haystack, VariadicOp) and isinstance(needle, VariadicOp):  # except if they're variadic
            ha, na = haystack.get_args(), needle.get_args()
            if needle.placeholder == "*":
                if len(na) < len(ha):
                    combs = [list(zip(h, n))
                             for h in itertools.combinations(ha, len(na))
                             for n in itertools.permutations(na)]
                    for comb in combs:
                        yield from unify_args(comb, bidi=bidi)
                    return
            # todo: should allow min and max numbers
            elif varargs := {t for t in na if isinstance(t, Constant) and t.name[-1] == "#"}:
                statargs = set(na) - varargs
                combs = (list(zip(h, statargs)) for h in itertools.permutations(ha, len(statargs)))
                varg = varargs.pop()  # todo
                for comb in combs:
                    hvarargs = set(ha) - set(t[0] for t in comb)
                    for hvarperm in itertools.permutations(hvarargs):
                        hna = comb + [(dataclasses.replace(haystack, args=hvarargs), varg)]
                        yield from unify_args(hna, bidi=bidi)
                return
        return []

    # can unify if all parameters are unifiable, elementwise
    if haystack.commutes():
        # test all ways to associate the parameters
        tests = [list(zip(h, n))
                 for h in itertools.permutations(haystack.get_args())
                 for n in itertools.permutations(needle.get_args())]
    else:
        # direct bijection
        tests = [list(zip(haystack.get_args(), needle.get_args()))]

    for test in tests:
        yield from unify_args(test, bidi=bidi)
