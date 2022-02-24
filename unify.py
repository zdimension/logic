# coding: utf-8

# deterministic
import dataclasses
import itertools
from functools import lru_cache
from typing import Iterable, Tuple, Dict, List

from expression import Term, Constant, Variable, Predicate, VariadicOp, NamedPredicate, Quantifier

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
    if isinstance(needle, Variable) and needle.name[0] == "$":
        return [{needle: haystack}]

    # can unify except if both are constants and their name is different
    if isinstance(haystack, Constant) and isinstance(needle, Constant):
        return []

    if isinstance(haystack, Quantifier) and isinstance(needle, Quantifier) and type(haystack) == type(needle):
        return gen_unifications(haystack.expr, needle.expr)

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
                if len(na) < len(
                        ha):  # we're unifying something looking like A & B & C with a needle looking like $A & $B
                    test1 = list(k_subset(list(ha), len(na)))
                    node_type = type(needle)
                    for comb in test1:
                        comb = [node_type(arg) if len(arg) > 1 else arg[0] for arg in comb]
                        for n in itertools.permutations(na):
                            yield from unify_args(list(zip(comb, n)), bidi=bidi)
                    #combs = [list(zip(h, n))
                    #         for h in itertools.combinations(ha, len(na))
                    #         for n in itertools.permutations(na)]
                    #for comb in combs:
                    #    yield from unify_args(comb, bidi=bidi)
                    #non_place = node_type(tuple(list(needle.get_args()) + [Variable(f"${i}") for i in range(len(ha) - len(na))]))
                    #ur = list(unify_functions(haystack, non_place, bidi))
                    #yield from ur
                    # for h in itertools.combinations(ha, len(na)):
                    #     for n in itertools.permutations(na):
                    #         ur = unify_args(list(zip(h, n)), bidi=bidi)
                    #         for unif in ur:
                    #             if True or len(unif) == len(na):
                    #                 yield unif
                    #         #yield from ur
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


def k_subset(ns: List, m: int):
    """Returns all the possible partitions of ns into m non-empty sets

    https://codereview.stackexchange.com/a/1944/113123"""

    def visit(n, a):
        ps = [[] for _ in range(m)]
        for j in range(n):
            ps[a[j + 1]].append(ns[j])
        return ps

    def f(mu: int, nu: int, sigma: int, n: int, a: List[int]):
        if mu == 2:
            yield visit(n, a)
        else:
            for v in f(mu - 1, nu - 1, (mu + sigma) % 2, n, a):
                yield v
        if nu == mu + 1:
            a[mu] = mu - 1
            yield visit(n, a)
            while a[nu] > 0:
                a[nu] = a[nu] - 1
                yield visit(n, a)
        elif nu > mu + 1:
            if (mu + sigma) % 2 == 1:
                a[nu - 1] = mu - 1
            else:
                a[mu] = mu - 1
            if (a[nu] + sigma) % 2 == 1:
                for v in b(mu, nu - 1, 0, n, a):
                    yield v
            else:
                for v in f(mu, nu - 1, 0, n, a):
                    yield v
            while a[nu] > 0:
                a[nu] = a[nu] - 1
                if (a[nu] + sigma) % 2 == 1:
                    for v in b(mu, nu - 1, 0, n, a):
                        yield v
                else:
                    for v in f(mu, nu - 1, 0, n, a):
                        yield v

    def b(mu, nu, sigma, n, a):
        if nu == mu + 1:
            while a[nu] < mu - 1:
                yield visit(n, a)
                a[nu] = a[nu] + 1
            yield visit(n, a)
            a[mu] = 0
        elif nu > mu + 1:
            if (a[nu] + sigma) % 2 == 1:
                for v in f(mu, nu - 1, 0, n, a):
                    yield v
            else:
                for v in b(mu, nu - 1, 0, n, a):
                    yield v
            while a[nu] < mu - 1:
                a[nu] = a[nu] + 1
                if (a[nu] + sigma) % 2 == 1:
                    for v in f(mu, nu - 1, 0, n, a):
                        yield v
                else:
                    for v in b(mu, nu - 1, 0, n, a):
                        yield v
            if (mu + sigma) % 2 == 1:
                a[nu - 1] = 0
            else:
                a[mu] = 0
        if mu == 2:
            yield visit(n, a)
        else:
            for v in b(mu - 1, nu - 1, (mu + sigma) % 2, n, a):
                yield v

    n = len(ns)
    a = [0] * (n + 1)
    for j in range(1, m + 1):
        a[n - m + j] = j - 1
    return f(m, n, 0, n, a)
