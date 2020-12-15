# coding: utf-8
import itertools
from functools import lru_cache
from typing import Generator, Callable, Set, Optional

from expression import *
from parse import parse as _

rules = {
    _("!!$X"): _("$X"),

    _("!FALSE"): _("TRUE"),
    _("!TRUE"): _("FALSE"),

    _("$X &* !$X"): _("FALSE"),
    _("$X |* !$X"): _("TRUE"),

    _("$X &* TRUE"): _("$X"),
    _("$X &* FALSE"): _("FALSE"),

    _("$X |* TRUE"): _("TRUE"),
    _("$X |* FALSE"): _("$X"),

    _("($A & $B) | (!$A & $C)"): _("$B | $C"),
}

rules_bidi = {
    _("!($X & $Y)"): _("!$X | !$Y"),
    _("!($X | $Y)"): _("!$X & !$Y"),
    _("$X → $Y"): _("!$X | $Y"),
    _("$X & $Y# | $X & $Z#"): _("$X & ($Y# | $Z#)")
}

for k, v in rules_bidi.items():
    rules[k] = v
    rules[v] = k


def get_all(term: Term) -> Generator[Term, None, None]:
    yield term
    for f in dataclasses.fields(term):
        val = getattr(term, f.name)
        if isinstance(val, Term):
            yield from get_all(val)
        elif isinstance(val, (tuple, frozenset)):
            for item in val:
                yield from get_all(item)


def map_fields(t: Term, func: Callable[[Term], Term]) -> Term:
    edits = {}
    for field in dataclasses.fields(t):
        val = getattr(t, field.name)
        if isinstance(val, Term):
            edits[field.name] = func(val)
        elif isinstance(val, tuple):
            edits[field.name] = tuple(func(v) for v in val)
        elif isinstance(val, frozenset):
            edits[field.name] = frozenset(func(v) for v in val)
    return dataclasses.replace(t, **edits)


def apply_sub(t: Term, find: Term, replace: Term) -> Term:
    if t == find:
        return replace

    return map_fields(t, lambda val: apply_sub(val, find, replace))


def apply_subs(t: Term, subs: Unification) -> Term:
    for find, replace in subs.items():
        t = apply_sub(t, find, replace)
    return t


def unify_args(test: Iterable[Tuple[Term, Term]], res=None) -> Unifications:
    for a1, a2 in test:
        if not (subs := find_unifications(a1, a2)):
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
            choices.extend(unify_args(test[1:], nres))
        return choices
    else:
        return [res]


def unify_functions(haystack: Function, needle: Function) -> Unifications:
    # can't unify two different builtin functions except if we're targetting the base type
    if type(haystack) != type(needle):
        return []

    if isinstance(haystack, NamedFunction) and isinstance(needle, NamedFunction):
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
                        yield from unify_args(comb)
                    return
            # elif varargs := {t for t in na if isinstance(t, Constant) and t.name[-1] == "#"}:
            #     statargs = set(na) - varargs
            #     combs = (zip(statargs, n) for n in itertools.permutations(na, len(statargs)))
        return []

    # can unify if all parameters are unifiable, elementwise
    if haystack.commutes():
        tests = [list(zip(h, n))
                 for h in itertools.permutations(haystack.get_args())
                 for n in itertools.permutations(needle.get_args())]
    else:
        tests = [list(zip(haystack.get_args(), needle.get_args()))]
    for test in tests:
        yield from unify_args(test)


def gen_unifications(haystack: Term, needle: Term) -> Unifications:
    # haystack, needle = map(eval, sorted(map(repr, (haystack, needle))))

    if haystack == needle:
        return [{}]

    # placeholders can be unified with anything
    if isinstance(needle, Constant) and needle.name[0] == "$":
        return [{needle: haystack}]

    # can unify except if both are constants and their name is different
    if isinstance(haystack, Constant) and isinstance(needle, Constant):
        return []

    # if isinstance(haystack, Variable) or isinstance(needle, Variable):
    #     l1, l2 = sorted((haystack, needle), key=lambda t: isinstance(t, Variable))
    #     if l2 in get_all(l1):  # can't unify x and f(x)
    #         return {}
    #     return {l2: l1}

    if isinstance(haystack, Function) and isinstance(needle, Function):
        return unify_functions(haystack, needle)

    return []


@lru_cache(maxsize=32)
def find_unifications(haystack: Term, needle: Term) -> Unifications:
    return [dict(t) for t in {frozenset(d.items()) for d in gen_unifications(haystack, needle)}]


def is_atomic(term: Term) -> bool:
    return isinstance(term, (Literal, NamedValue))


@lru_cache(maxsize=32)
def simplify_deep(term: Term) -> Term:
    if is_atomic(term):
        return term

    if term in rules:
        return rules[term]

    if isinstance(term, VariadicOp) and term.arity() == 1:
        return list(term.args)[0]

    return map_fields(term, simplify)


@lru_cache(maxsize=32)
def simplify(term: Term) -> Term:
    history = [term]
    while True:
        potential = filter(lambda r: r and r != term, (simplify_deep(item) for item in itertools.chain(
            [term],
            (apply_subs(dest, unif) for src, dest in rules.items() for unif in find_unifications(term, src)))))
        for choice in potential:
            if choice in history:
                return term
            term = choice
            history.append(choice)
            break
        else:
            break

    return simplify_deep(term) or term


def get_vars(term: Term) -> Set[NamedValue]:
    return set(v for v in get_all(term) if isinstance(v, NamedValue))


def truth_table(term: Term):
    variables = sorted(v.name for v in get_vars(term))
    interp = Interpretation()
    header = " | ".join(variables) + " | " + str(term)
    print(header)
    print("-" * len(header))
    for vals in itertools.product((False, True), repeat=len(variables)):
        interp.values = dict(zip(variables, vals))
        print(" | ".join("FT"[x] for x in vals) + " | " + "FT"[term.evaluate(interp)] + " | " + str(
            simplify(apply_subs(term, interp.to_sub()))))
