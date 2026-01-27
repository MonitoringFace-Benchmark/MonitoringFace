from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrdering


class PropositionList(AbstractOutputStructure):
    def __init__(self, variable_order: VariableOrdering):
        self.prop_list = dict()
        self.tp_to_ts = dict()
        self.variable_order = variable_order

    def retrieve_order(self):
        return self.variable_order.retrieve_order()

    def retrieve(self, time_point):
        if time_point in self.prop_list:
            return time_point, self.tp_to_ts[time_point], self.prop_list[time_point]
        return None

    def insert(self, value, time_point, time_stamp=None):
        self.tp_to_ts[time_point] = time_stamp if time_stamp else time_point
        self.prop_list[time_point] = value
