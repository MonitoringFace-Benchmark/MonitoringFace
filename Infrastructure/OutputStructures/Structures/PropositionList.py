from Infrastructure.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure


class PropositionList(AbstractOutputStructure):
    def __init__(self):
        self.prop_list = dict()
        self.tp_to_ts = dict()

    def retrieve_index(self, time_point):
        if time_point not in self.prop_list:
            return False
        else:
            return self.prop_list[time_point]

    def insert_index(self, value, time_point, time_stamp=None):
        if time_stamp:
            self.tp_to_ts[time_point] = time_stamp
        self.prop_list[time_point] = value
