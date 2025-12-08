from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure


class Verdicts(AbstractOutputStructure):
    def __init__(self):
        self.verdict = list()
        self.tp_to_ts = dict()

    def retrieve(self, time_point):
        selected = [val for (tp, _, val) in self.verdict if tp == time_point]
        if selected:
            return time_point, self.tp_to_ts[time_point], selected
        return None

    def insert(self, value, time_point, time_stamp):
        self.tp_to_ts[time_point] = time_stamp
        self.verdict.append(
            (time_point, time_stamp, value if isinstance(value, list) else [value])
        )
