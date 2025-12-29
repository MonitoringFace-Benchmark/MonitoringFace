from abc import ABC
from typing import List


class VariableOrdering(ABC):
    variable_order: List[str] = []


class VariableOrder(VariableOrdering):
    def __init__(self, variable_order: List[str]):
        self.variable_order = variable_order


class DefaultVariableOrder(VariableOrdering):
    pass
