from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.Assignment import Assignment
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.Proposition import Proposition
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrdering


class Verdicts(AbstractOutputStructure):
    def __init__(self, variable_order: VariableOrdering):
        self.verdict = list()
        self.tp_to_ts = dict()
        self.variable_order = variable_order

    def retrieve_order(self):
        return self.variable_order.retrieve_order()

    def retrieve(self, time_point):
        selected = [val for (tp, _, val) in self.verdict if tp == time_point]
        if selected:
            return self.tp_to_ts[time_point], time_point, selected
        return None

    def insert(self, value, time_point, time_stamp):
        self.tp_to_ts[time_point] = time_stamp
        values = value if isinstance(value, list) else [value]
        if self.variable_order:
            values = list(map(lambda va: Assignment(va, self.variable_order), values))
        else:
            values = list(map(lambda va: Proposition(va), values))
        self.verdict.append((time_stamp, time_point, values))
