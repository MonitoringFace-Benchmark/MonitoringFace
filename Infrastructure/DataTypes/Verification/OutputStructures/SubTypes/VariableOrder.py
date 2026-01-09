from abc import ABC, abstractmethod
from typing import List


class VariableOrdering(ABC):
    @abstractmethod
    def retrieve_order(self):
        pass


class VariableOrder(VariableOrdering):
    def __init__(self, variable_order: List[str]):
        self.variable_order = variable_order

    def retrieve_order(self):
        return self.variable_order


class DefaultVariableOrder(VariableOrdering):
    def __init__(self, variable_order=None):
        self.variable_order = [] if None else variable_order

    def retrieve_order(self):
        return []
