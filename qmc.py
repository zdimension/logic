# coding: utf-8
from collections import Set
from typing import List
import numpy as np

from expression import Term


def find_neighbors(nb: int, bits: int) -> Set[int]:
    return {nb ^ (1 << b) for b in range(bits)}


def group_by(items):
    items = list(items)
    res = set()
    rem = set()
    for i, term1 in enumerate(items):
        for j, term2 in enumerate(items[i+1:]):
            diff = [i for i, (a, b) in enumerate(zip(term1, term2)) if a != b]
            if len(diff) != 1:
                continue
            n = diff[0]
            rem.add(term1)
            rem.add(term2)
            res.add(term1[:n] + "-" + term1[n+1:])
    return res, rem

def to_nums(imp: str):
    ids = [i for i, c in enumerate(imp) if c == "-"]
    for i, j in enumerate(ids):
        pass

def execute(vars: int, *minterms: int) -> Term:

    return


    imps = [[f"{x:04b}" for x in minterms]]
    while True:
        res, rem = group_by(imps[-1])
        if not res:
            break
        for x in rem:
            imps[-1].remove(x)
        imps.append(list(res))
    print(imps)
    return None
