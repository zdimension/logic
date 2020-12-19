# coding: utf-8
import dataclasses
import itertools
from typing import Dict, Tuple, Optional, Sequence

from expression import Term, Interpretation, Variable, Literal
from process import simplify


@dataclasses.dataclass
class TruthTable:
    table: Dict[Tuple[bool], bool]
    variables: Optional[Sequence[str]] = None
    term: Optional[Term] = None

    @staticmethod
    def from_term(term: Term) -> "TruthTable":
        variables = sorted(v.name for v in term.get_vars())
        return TruthTable({
            tuple(vals): term.evaluate(Interpretation(dict(zip(variables, vals))))
            for vals in itertools.product((False, True), repeat=len(variables))
        }, variables, term)

    def __str__(self):
        variables = self.variables or [chr(ord("A") + x) for x in range(len([*self.table.keys()][0]))]
        variables_obj = list(map(Variable, variables))
        header = " | ".join(variables) + " | " + (str(self.term) if self.term else "RESULT")
        lines = [header, "-" * len(header)]
        for vals, res in self.table.items():
            lines.append(" | ".join("FT"[x] for x in vals) + " | " + "FT"[res] + " | " +
                         str(simplify(self.term.apply_subs(dict(zip(variables_obj, map(Literal.from_bool, vals)))))))
        return "\n".join(lines)

    def get_truth_density(self) -> float:
        return sum(self.table.values()) / len(self.table)

    def get_operator_number(self) -> int:
        return sum(v * 2 ** i for i, v in enumerate(self.table.values()))