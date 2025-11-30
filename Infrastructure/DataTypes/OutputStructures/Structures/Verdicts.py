from Infrastructure.DataTypes.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure


class Verdicts(AbstractOutputStructure):
    def __init__(self):
        self.verdict = dict()
        self.tp_to_ts = dict()

    def retrieve(self, time_point):
        return time_point, self.tp_to_ts[time_point], self.verdict[time_point]

    def insert(self, value, time_point, time_stamp):
        self.tp_to_ts[time_point] = time_stamp
        self.verdict[time_point].append(value)
