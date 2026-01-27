from typing import AnyStr, Tuple

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrdering, \
    DefaultVariableOrder
from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate


class TeSSLa(AbstractMonitorTemplate):
    def __init__(self, image: AnyStr, name: str, params: AnyStr):
        super().__init__(image, name, params)

    def pre_processing(self, path_to_folder: AnyStr, data_file: AnyStr, signature_file: AnyStr, formula_file: AnyStr):
        self.params["folder"] = path_to_folder
        self.params["formula"] = formula_file.removeprefix("data/")
        self.params["data"] = data_file.removeprefix("data/")

    def run_offline(self, time_on=None, time_out=None) -> Tuple[AnyStr, int]:
        cmd = [self.params["formula"], self.params["data"]]
        self.image.name = "interpreter"
        return self.image.run(self.params["folder"], cmd, time_on, time_out, measure=False)

    def variable_order(self) -> VariableOrdering:
        return DefaultVariableOrder()

    def post_processing(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        return PropositionList(self.variable_order())
