from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.ValueType import ValueType


class Assignment(ValueType):
    def __init__(self, variable_order, values):
        self.order = list(variable_order)
        self.values = list(values)

    def __repr__(self):
        return f"Assignment({self.order}, {self.values})"

    def __eq__(self, other):
        if not isinstance(other, Assignment):
            return False
        return dict(zip(self.order, self.values)) == dict(zip(other.order, other.values))

    def retrieve_order(self, new_order):
        mapping = {v: val for v, val in zip(self.values, self.order)}
        if set(self.values) != set(new_order):
            raise ValueError("New order must contain exactly the same variable names.")
        return Assignment(new_order, [mapping[v] for v in new_order])

    def retrieve_value(self, key):
        return self.values[self.order.index(key)]
