# coding: utf-8
import itertools
from collections import OrderedDict
from functools import lru_cache
from typing import Generator, Callable, Set, Optional, Sequence

from expression import *
from parse import parse as _

rules = OrderedDict()


def replace(a, b, bidi: bool = False):
    a, b = map(_, (a, b))
    rules[a] = b
    if bidi:
        rules[b] = a


replace("!!$X", "$X")

replace("!FALSE", "TRUE")
replace("!TRUE", "FALSE")

replace("TRUE → $X", "$X")
replace("FALSE → $X", "TRUE")

replace("$X & $Y# | $X & $Z#", "$X & ($Y# | $Z#)", True)

replace("$X &* !$X", "FALSE")
replace("$X |* !$X", "TRUE")

replace("$X &* TRUE", "$X")
replace("$X &* FALSE", "FALSE")

replace("$X |* TRUE", "TRUE")
replace("$X |* FALSE", "$X")

# replace("($A & $B) | (!$A & $C)", "$B | $C")

replace("$X → $Y", "!$X | $Y", True)

replace("!($X & $Y)", "!$X | !$Y", True)
replace("!($X | $Y)", "!$X & !$Y", True)


# deterministic
def get_all(term: Term) -> Generator[Term, None, None]:
    yield term
    for f in dataclasses.fields(term):
        val = getattr(term, f.name)
        if isinstance(val, Term):
            yield from get_all(val)
        elif isinstance(val, (tuple, frozenset)):
            for item in val:
                yield from get_all(item)


# deterministic
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


# deterministic
def apply_sub(t: Term, find: Term, replace: Term) -> Term:
    if t == find:
        return replace

    return map_fields(t, lambda val: apply_sub(val, find, replace))


# deterministic
def apply_subs(t: Term, subs: Unification) -> Term:
    for find, replace in subs.items():
        t = apply_sub(t, find, replace)
    return t


# deterministic
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
                new_args = [(apply_subs(b1, nres), apply_subs(b2, nres)) for b1, b2 in new_args[1:]]
            choices.extend(unify_args(new_args, nres, bidi))
        return choices
    else:
        return [res]


def unify_functions(haystack: Function, needle: Function, bidi: bool = False) -> Unifications:
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
                        yield from unify_args(comb, bidi=bidi)
                    return
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
        tests = [list(zip(h, n))
                 for h in itertools.permutations(haystack.get_args())
                 for n in itertools.permutations(needle.get_args())]
    else:
        tests = [list(zip(haystack.get_args(), needle.get_args()))]
    for test in tests:
        yield from unify_args(test, bidi=bidi)


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
            if l2 in get_all(l1):  # can't unify x and f(x)
                return {}
            return [{l2: l1}]

    if isinstance(haystack, Function) and isinstance(needle, Function):
        return unify_functions(haystack, needle, bidi)

    return []


@lru_cache(maxsize=32)
def find_unifications(haystack: Term, needle: Term, bidi: bool = False) -> Unifications:
    return [dict(t) for t in {frozenset(d.items()) for d in gen_unifications(haystack, needle, bidi)}]


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
    term = simplify_deep(term)
    history = [term]
    while True:
        rules_simp = set(apply_subs(dest, unif) for src, dest in rules.items() for unif in find_unifications(term, src))
        potential = list(sorted(filter(lambda r: r and r != term, (simplify_deep(item) for item in itertools.chain(
            [term],
            rules_simp))), key=lambda r: len(list(get_all(r)))))
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


def get_vars(term: Term) -> Set[NamedValue]:
    return set(v for v in get_all(term) if isinstance(v, NamedValue))


@dataclass
class TruthTable:
    table: Dict[Tuple[bool], bool]
    variables: Optional[Sequence[str]] = None
    term: Optional[Term] = None

    def __str__(self):
        variables = self.variables or [chr(ord("A") + x) for x in range(len([*self.table.keys()][0]))]
        variables_obj = list(map(Variable, variables))
        header = " | ".join(variables) + " | " + (str(self.term) if self.term else "RESULT")
        lines = [header, "-" * len(header)]
        for vals, res in self.table.items():
            lines.append(" | ".join("FT"[x] for x in vals) + " | " + "FT"[res] + " | " +
                         str(simplify(apply_subs(self.term, dict(zip(variables_obj, map(get_literal, vals)))))))
        return "\n".join(lines)

    def get_truth_density(self) -> float:
        return sum(self.table.values()) / len(self.table)

    def get_operator_number(self) -> int:
        return sum(v * 2 ** i for i, v in enumerate(self.table.values()))


def get_truth_table(term: Term) -> TruthTable:
    variables = sorted(v.name for v in get_vars(term))
    return TruthTable({
        tuple(vals): term.evaluate(Interpretation(dict(zip(variables, vals))))
        for vals in itertools.product((False, True), repeat=len(variables))
    }, variables, term)


def get_literal(val: bool) -> Literal:
    return (Negative, Positive)[val]()
