from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.Assignment import Assignment
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrdering


class DatagolfVerdicts(AbstractOutputStructure):
    def __init__(self, variable_order: VariableOrdering):
        self.variable_order = variable_order
        self.pos_verdicts = dict()
        self.neg_verdicts = dict()
        self.tp_to_ts = dict()

    def retrieve_order(self):
        return self.variable_order.retrieve_order()

    def insert_positive_verdict(self, values, time_point: int, time_stamp: int):
        self.tp_to_ts[time_point] = time_stamp
        values = list(map(lambda va: Assignment(va, self.variable_order), values))
        self.pos_verdicts[time_point] = values

    def insert_negative_verdict(self, values, time_point: int, time_stamp: int):
        self.tp_to_ts[time_point] = time_stamp
        values = list(map(lambda va: Assignment(va, self.variable_order), values))
        self.neg_verdicts[time_point] = values
