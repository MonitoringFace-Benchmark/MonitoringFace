from Infrastructure.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure


class OooVerdicts(AbstractOutputStructure):
    def __init__(self):
        self.oooverdict = dict()
        self.tp_to_ts = dict()
        pass

    def retrieve_index(self, time_point):
        pass

    def insert_index(self, value, time_point, time_stamp=None):

        pass
