from parse import parse as _
from process import simplify, truth_table

forms = {
    "P(A) & !P(A) & C": "FALSE",
    "TRUE | x": "TRUE",
    "FALSE & x": "FALSE",
    "!!A": "A",
    "!!!!A": "A",
    "A & !A": "FALSE",
    "A & !B": "A & !B",
    "!(a|b)": "!a & !b",
    "((P & Q) & !R) | (P & !(Q | R))": "P & !R",
    "b & y => y": "TRUE"
}

for f, exp in forms.items():
    exp = _(exp)
    ff = simplify(_(f))
    print(f"{f!s:40} {ff!s:31} {exp!s:10} {ff == exp}")

# print(False, find_unification(_("x"), _("f(x, y)")))
# print(find_unification(_("x"), _("f(x, y)")))

truth_table(_("((P & Q) & !R) | (P & !(Q | R))"))
