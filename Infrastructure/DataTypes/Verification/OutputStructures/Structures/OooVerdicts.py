from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure


class OooVerdicts(AbstractOutputStructure):
    def __init__(self):
        self.ooo_verdict = list()
        self.tp_to_ts = dict()

    def retrieve(self, time_point):
        selected = [x for (tp, _, val) in self.ooo_verdict if tp == time_point for x in val]
        return time_point, self.tp_to_ts[time_point], selected

    def insert(self, value, time_point, time_stamp):
        self.tp_to_ts[time_point] = time_stamp
        self.ooo_verdict.append((time_point, time_stamp, value if isinstance(value, list) else [value]))
