# coding: utf-8
from collections import OrderedDict
from parse import parse as _

rules = OrderedDict()


def replace(a, b, bidi: bool = False):
    a, b = map(_, (a, b))
    rules[a] = b
    if bidi:
        rules[b] = a


replace("!!$X", "$X", True)

replace("!FALSE", "TRUE")
replace("!TRUE", "FALSE")

replace("TRUE → $X", "$X")
replace("FALSE → $X", "TRUE")

replace("$X & $Y# | $X & $Z#", "$X & ($Y# | $Z#)", True)
#replace("($X | $Y#) & ($X | $Z#)", "$X | ($Y# & $Z#)", True)

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
