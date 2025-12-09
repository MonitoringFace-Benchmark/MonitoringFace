from typing import Tuple

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.Assignment import Assignment


class OooVerdicts(AbstractOutputStructure):
    def __init__(self, variable_order=None):
        self.ooo_verdict: list[Tuple[int, int, list[Assignment]]] = list()
        self.tp_to_ts = dict()
        self.variable_order = variable_order

    def retrieve(self, time_point):
        selected = [x for (tp, _, val) in self.ooo_verdict if tp == time_point for x in val]
        return time_point, self.tp_to_ts[time_point], selected

    def insert(self, value, time_point, time_stamp):
        self.tp_to_ts[time_point] = time_stamp
        self.ooo_verdict.append((time_point, time_stamp, value if isinstance(value, list) else [value]))
