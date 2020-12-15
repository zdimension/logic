# coding: utf-8
import dataclasses
from abc import ABC, abstractmethod
from typing import Dict, Tuple, Iterable


def dataclass(cls=None, **kwargs):
    def wrap(cls):
        return dataclasses.dataclass(cls, **{"frozen": True, "eq": True, **kwargs})

    if cls is None:
        return wrap
    return wrap(cls)


@dataclass(frozen=False)
class Interpretation:
    values: Dict[str, bool] = dataclasses.field(default_factory=dict)

    def to_sub(self) -> "Unification":
        return {Variable(name): (Negative, Positive)[val]() for name, val in self.values.items()}


class Term(ABC):
    def evaluate(self, interp: Interpretation) -> bool:
        raise NotImplementedError


class Literal(Term, ABC):
    pass


@dataclass
class Positive(Literal):
    def __str__(self):
        return "TRUE"

    def evaluate(self, interp: Interpretation) -> bool:
        return True


@dataclass
class Negative(Literal):
    def __str__(self):
        return "FALSE"

    def evaluate(self, interp: Interpretation) -> bool:
        return False


@dataclass
class NamedValue(Term):
    name: str

    def __str__(self):
        return self.name

    def evaluate(self, interp: Interpretation) -> bool:
        if self.name not in interp.values:
            raise UnboundLocalError(f"Unbound value {self.name}")
        return interp.values[self.name]


@dataclass
class Variable(NamedValue):
    pass


@dataclass
class Constant(NamedValue):
    pass


class Function(Term, ABC):
    @abstractmethod
    def get_args(self) -> Tuple[Term, ...]:
        raise NotImplementedError

    def commutes(self) -> bool:
        return False

    def arity(self):
        return len(self.get_args())


@dataclass
class NamedFunction(Function):
    name: str
    args: Tuple[Term, ...]

    def evaluate(self, interp: Interpretation) -> bool:
        raise NotImplementedError

    def get_args(self) -> Tuple[Term, ...]:
        return self.args

    def __str__(self):
        return f"{self.name}({', '.join(map(str, self.args))})"


@dataclass
class BuiltinOp(Function, ABC):
    args: Tuple[Term, ...]

    @staticmethod
    def get_op():
        raise NotImplementedError

    def __str__(self):
        return "(" + f" {self.get_op()} ".join(map(str, self.args)) + ")"

    def get_args(self) -> Tuple[Term, ...]:
        return self.args


@dataclass
class BinOp(BuiltinOp, ABC):
    def __init__(self, args: Iterable[Term], op: str = None):
        self.__dict__["args"] = tuple(args)


@dataclass
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


@dataclass(init=False)
class And(VariadicOp):
    @staticmethod
    def get_op():
        return "&"

    def evaluate(self, interp: Interpretation) -> bool:
        for arg in self.args:
            if not arg.evaluate(interp):
                return False
        return True


@dataclass(init=False)
class Or(VariadicOp):
    @staticmethod
    def get_op():
        return "|"

    def evaluate(self, interp: Interpretation) -> bool:
        for arg in self.args:
            if arg.evaluate(interp):
                return True
        return False


@dataclass(init=False)
class Imp(BinOp):
    @staticmethod
    def get_op():
        return "→"

    def evaluate(self, interp: Interpretation) -> bool:
        return not self.args[0].evaluate(interp) or self.args[1].evaluate(interp)


@dataclass
class Not(Function):
    elem: Term

    def __str__(self):
        return f"!{self.elem}"

    def evaluate(self, interp: Interpretation) -> bool:
        return not self.elem.evaluate(interp)

    def get_args(self) -> Tuple[Term, ...]:
        return self.elem,


Unification = Dict[Term, Term]
Unifications = Iterable[Unification]
