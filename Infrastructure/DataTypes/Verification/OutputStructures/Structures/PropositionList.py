from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure


class PropositionList(AbstractOutputStructure):
    def __init__(self):
        self.prop_list = dict()
        self.tp_to_ts = dict()

    def retrieve(self, time_point):
        return time_point, self.tp_to_ts[time_point], self.tp_to_ts[time_point]

    def insert(self, value, time_point, time_stamp=None):
        self.tp_to_ts[time_point] = time_stamp if time_stamp else time_point
        self.prop_list[time_point] = value
