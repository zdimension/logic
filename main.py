from parse import parse as _
from rules import RULES_CNF, DISTRIB_DNF, DISTRIB_CNF
from simplify import *
from unify import unify_functions

# print(simplify(_("TRUE | x")))
# print(simplify(_("((P & Q) & !R) | (P & !(Q | R))")))
# print(find_unifications(_("p(X,Y,Z)"), _("p(Y,Z,X)"), True))
# print([str(apply_subs(x, {
#     _("Y"): _("f(a)"),
#     _("Z"): _("g(a)"),
#     _("X"): _("a")
# })) for x in (_("p(h(Y,Z),f(a),g(a))"), _("p(h(f(X),g(X)),Y,Z)"))])

forms = {
    "!!A": "A",
    "TRUE & x & y": "x & y",
    "P(A) & !P(A) & C": "FALSE",
    "TRUE | x": "TRUE",
    "FALSE & x": "FALSE",
    "!!!!A": "A",
    "A & !A": "FALSE",
    "A & !B": "A & !B",
    "!(a|b)": "!a & !b",
    "b & y => y": "TRUE",
    "((P & Q) & !R) | (P & !(Q | R))": "P & !R",
    "(!Q & !R) | (Q & !R)": "!R",
    "(!R & !Q) | (!R & Q)": "!R",
    "(((!Q & !R) | (Q & !R)) & P)": "P & !R",
    "(A & !B) | (!A & B)": "(A & !B) | (!A & B)",
    "(A & !B) | (!A & B) => (A | B) & (!A | !B)": "TRUE"
}

for f, exp in forms.items():
    exp = _(exp)
    ff = simplify(_(f))
    print(f"{f!s:50} {ff!s:31} {exp!s:30} {ff == exp} {simplify(_(f), RULES_CNF)}")

# print(False, find_unification(_("x"), _("f(x, y)")))
# print(find_unification(_("x"), _("f(x, y)")))
f = _("((P & Q) & !R) | (P & !(Q | R))")
# table = get_truth_table(f)
# print(table)
# print(table.get_truth_density())
# print(table.get_operator_number())

system = [
    # "MgO & H2 -> Mg & H2O",
    # "C & O2 -> CO2",
    # "CO2 & H2O -> H2CO3",
    "MgO",
    "H2",
    "O2",
    "C"
]

target = "H2CO3"

r = RULES_DNF.add(
    "($A | $P1#) & (!$A | $P2#) & $X# -> ($P1# | $P2#) & $X#",
    "$A & (!$A | $P1#) & $X# -> $P1# & $X#",
)#.add(*system)
print("\n".join([str(k) + " -> " + str(v) for k, v in r.items()]))
full = And([Not(_(target)), *map(_, system)])
print(full)
full = simplify_deep(full, r)
print(full)
#print(simplify(full, r))