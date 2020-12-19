# coding: utf-8
from abc import ABC, abstractmethod
import dataclasses
from functools import reduce
from typing import Dict, Tuple, Iterable, Generator, Set, Callable


@dataclasses.dataclass
class Interpretation:
    values: Dict[str, bool] = dataclasses.field(default_factory=dict)

    def to_sub(self) -> "Unification":
        return {Variable(name): (Negative, Positive)[val]() for name, val in self.values.items()}


@dataclasses.dataclass(frozen=True)
class Term(ABC):
    def evaluate(self, interp: Interpretation) -> bool:
        raise NotImplementedError

    def get_children(self) -> Generator["Term", None, None]:
        yield self
        for f in dataclasses.fields(self):
            val = getattr(self, f.name)
            if isinstance(val, Term):
                yield from val.get_children()
            elif isinstance(val, (tuple, frozenset)):
                for item in val:
                    yield from item.get_children()

    def get_vars(self) -> Set["NamedValue"]:
        return set(v for v in self.get_children() if isinstance(v, NamedValue))

    def is_atomic(self) -> bool:
        return isinstance(self, (Literal, NamedValue))

    def map_fields(self, func: Callable[["Term"], "Term"]) -> "Term":
        edits = {}
        for field in dataclasses.fields(self):
            val = getattr(self, field.name)
            if isinstance(val, Term):
                edits[field.name] = func(val)
            elif isinstance(val, tuple):
                edits[field.name] = tuple(func(v) for v in val)
            elif isinstance(val, frozenset):
                edits[field.name] = frozenset(func(v) for v in val)
        return dataclasses.replace(self, **edits)

    def apply_sub(self, find: "Term", replace: "Term") -> "Term":
        if self == find:
            return replace

        return self.map_fields(lambda val: val.apply_sub(find, replace))

    def apply_subs(self, subs: "Unification") -> "Term":
        return reduce(
            lambda cur, sub: cur.apply_sub(*sub),
            subs.items(),
            self)

    def get_truth_table(self):
        from truth_table import TruthTable
        return TruthTable.from_term(self)


class Literal(Term, ABC):
    @staticmethod
    def from_bool(val: bool) -> "Literal":
        return (Negative, Positive)[val]()


@dataclasses.dataclass(frozen=True)
class Positive(Literal):
    def __str__(self):
        return "TRUE"

    def evaluate(self, interp: Interpretation) -> bool:
        return True


@dataclasses.dataclass(frozen=True)
class Negative(Literal):
    def __str__(self):
        return "FALSE"

    def evaluate(self, interp: Interpretation) -> bool:
        return False


@dataclasses.dataclass(frozen=True)
class NamedValue(Term):
    name: str

    def __str__(self):
        return self.name

    def evaluate(self, interp: Interpretation) -> bool:
        if self.name not in interp.values:
            raise UnboundLocalError(f"Unbound value {self.name}")
        return interp.values[self.name]


@dataclasses.dataclass(frozen=True)
class Variable(NamedValue):
    pass


@dataclasses.dataclass(frozen=True)
class Constant(NamedValue):
    pass


class Predicate(Term, ABC):
    @abstractmethod
    def get_args(self) -> Tuple[Term, ...]:
        raise NotImplementedError

    def commutes(self) -> bool:
        return False

    def arity(self):
        return len(self.get_args())


@dataclasses.dataclass(frozen=True)
class NamedPredicate(Predicate):
    name: str
    args: Tuple[Term, ...]

    def evaluate(self, interp: Interpretation) -> bool:
        raise NotImplementedError

    def get_args(self) -> Tuple[Term, ...]:
        return self.args

    def __str__(self):
        return f"{self.name}({', '.join(map(str, self.args))})"


@dataclasses.dataclass(frozen=True)
class BuiltinOp(Predicate, ABC):
    args: Tuple[Term, ...]

    @staticmethod
    def get_op():
        raise NotImplementedError

    def __str__(self):
        return "(" + f" {self.get_op()} ".join(map(str, self.args)) + ")"

    def get_args(self) -> Tuple[Term, ...]:
        return self.args


@dataclasses.dataclass(frozen=True)
class BinOp(BuiltinOp, ABC):
    def __init__(self, args: Iterable[Term], op: str = None):
        self.__dict__["args"] = tuple(args)


@dataclasses.dataclass(frozen=True)
class VariadicOp(BuiltinOp, ABC):
    placeholder: str

    def __init__(self, args: Iterable[Term], placeholder: str = ""):
        nargs = []
        for arg in args:
            if type(arg) == type(self):
                nargs.extend(arg.args)
            else:
                nargs.append(arg)
        self.__dict__["args"] = frozenset(nargs)
        self.__dict__["placeholder"] = placeholder

    def commutes(self) -> bool:
        return True


@dataclasses.dataclass(frozen=True, init=False)
class And(VariadicOp):
    @staticmethod
    def get_op():
        return "&"

    def evaluate(self, interp: Interpretation) -> bool:
        for arg in self.args:
            if not arg.evaluate(interp):
                return False
        return True


@dataclasses.dataclass(frozen=True, init=False)
class Or(VariadicOp):
    @staticmethod
    def get_op():
        return "|"

    def evaluate(self, interp: Interpretation) -> bool:
        for arg in self.args:
            if arg.evaluate(interp):
                return True
        return False


@dataclasses.dataclass(frozen=True, init=False)
class Imp(BinOp):
    @staticmethod
    def get_op():
        return "→"

    def evaluate(self, interp: Interpretation) -> bool:
        return not self.args[0].evaluate(interp) or self.args[1].evaluate(interp)


@dataclasses.dataclass(frozen=True)
class Not(Predicate):
    elem: Term

    def __str__(self):
        return f"!{self.elem}"

    def evaluate(self, interp: Interpretation) -> bool:
        return not self.elem.evaluate(interp)

    def get_args(self) -> Tuple[Term, ...]:
        return self.elem,


Unification = Dict[Term, Term]
Unifications = Iterable[Unification]
