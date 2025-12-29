from typing import List, Any

from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.ValueType import ValueType
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrdering


class Assignment(ValueType):
    def __init__(self, values: List[Any], variable_order: VariableOrdering):
        self.order = variable_order.variable_order
        self.values = values

    def __repr__(self):
        return f"Assignment({self.values}, {self.order})"

    def __eq__(self, other):
        if not isinstance(other, Assignment):
            return False
        return dict(zip(self.order, self.values)) == dict(zip(other.order, other.values))

    def retrieve_order(self, new_order: VariableOrdering):
        mapping = {v: val for v, val in zip(self.values, self.order)}
        if set(self.values) != set(new_order.variable_order):
            raise ValueError("New order must contain exactly the same variable names.")
        return Assignment([mapping[v] for v in new_order.variable_order], new_order)

    def retrieve_value(self, key):
        return self.values[self.order.index(key)]
