from typing import Dict, Tuple

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.Assignment import Assignment
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrdering


class DatagolfVerdicts(AbstractOutputStructure):
    def __init__(self, variable_order: VariableOrdering):
        self.variable_order = variable_order
        self.pos_verdicts = dict()
        self.neg_verdicts = dict()
        self.tp_to_ts = dict()

    def time_points(self) -> Dict[int, int]:
        return self.tp_to_ts

    def retrieve_order(self):
        return self.variable_order.retrieve_order()

    def as_oracle(self, other: 'AbstractOutputStructure') -> Tuple[bool, str]:
        from Infrastructure.DataTypes.Verification.OutputStructures.Compare.DataGolfComparator import as_oracle
        return as_oracle(self, other)

    def retrieve_negative_verdict(self, time_point):
        if time_point not in self.tp_to_ts:
            return None
        selected = self.neg_verdicts[time_point]
        return self.tp_to_ts[time_point], time_point, selected

    def retrieve_positive_verdict(self, time_point):
        if time_point not in self.tp_to_ts:
            return None
        selected = self.pos_verdicts[time_point]
        return self.tp_to_ts[time_point], time_point, selected

    def insert_positive_verdict(self, values, time_point: int, time_stamp: int):
        self.tp_to_ts[time_point] = time_stamp
        values = list(map(lambda va: Assignment(va, self.variable_order), values))
        self.pos_verdicts[time_point] = values

    def insert_negative_verdict(self, values, time_point: int, time_stamp: int):
        self.tp_to_ts[time_point] = time_stamp
        values = list(map(lambda va: Assignment(va, self.variable_order), values))
        self.neg_verdicts[time_point] = values

    def printing(self):
        print(f"Variable order: {self.variable_order.retrieve_order()}")
        for time_point in sorted(self.tp_to_ts.keys()):
            pos = self.retrieve_positive_verdict(time_point)
            neg = self.retrieve_negative_verdict(time_point)
            print(f"Time point {time_point} (timestamp {self.tp_to_ts[time_point]}):")
            print(f"  Positive verdicts: {[str(v) for v in pos[2]]}")
            print(f"  Negative verdicts: {[str(v) for v in neg[2]]}")
