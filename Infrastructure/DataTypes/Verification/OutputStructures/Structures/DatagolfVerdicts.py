from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure


class DatagolfVerdicts(AbstractOutputStructure):
    def __init__(self, variable_order):
        self.variable_order = variable_order
