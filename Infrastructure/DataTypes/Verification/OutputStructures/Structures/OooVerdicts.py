from typing import Tuple

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.Assignment import Assignment
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.Proposition import Proposition


class OooVerdicts(AbstractOutputStructure):
    def __init__(self, variable_order=None):
        self.ooo_verdict: list[Tuple[int, int, list[Assignment]]] = list()
        self.tp_to_ts = dict()
        self.variable_order = variable_order

    def retrieve(self, time_point):
        selected = [x for (tp, _, val) in self.ooo_verdict if tp == time_point for x in val]
        return self.tp_to_ts[time_point], time_point, selected

    def insert(self, value, time_point, time_stamp):
        self.tp_to_ts[time_point] = time_stamp
        values = value if isinstance(value, list) else [value]
        if self.variable_order:
            values = list(map(lambda va: Assignment(va, self.variable_order), values))
        else:
            values = list(map(lambda va: Proposition(va), values))
        self.ooo_verdict.append((time_stamp, time_point, values))
