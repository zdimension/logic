# coding: utf-8
from collections import Set
from typing import List
import numpy as np

from expression import Term


def find_neighbors(nb: int, bits: int) -> Set[int]:
    return {nb ^ (1 << b) for b in range(bits)}


def group_by(items: List[List[int]]):
    for i, num in enumerate(items):
        for j, num2 in enumerate(items[i+1:]):
            if num & num2:
                continue
            both = num | num2
            d1 = np.bitwise_xor.reduce(list(num))
            d2 = np.bitwise_xor.reduce(list(num2))
            if d1 == d2:
                continue
            diff = np.bitwise_xor.reduce(list(both))
            count = 0
            while diff:
                count += diff & 1
                if count == 2:
                    break
                diff >>= 1
            else:
                yield both


def execute(vars: int, *minterms: int) -> Term:
    s1 = list(group_by([{x} for x in minterms]))
    print(s1)
    s2 = list(group_by(s1))
    print(s2)
    return None
