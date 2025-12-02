

class Assignment:
    def __init__(self, variable_order, values):
        self.order = list(variable_order)
        self.values = list(values)

    def retrieve_order(self, new_order):
        mapping = {v: val for v, val in zip(self.order, self.values)}
        if set(mapping.keys()) != set(new_order):
            raise ValueError("New order must contain exactly the same variable names.")
        return Assignment(new_order, [mapping[v] for v in new_order])
