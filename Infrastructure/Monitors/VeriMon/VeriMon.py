from typing import Dict, AnyStr, Any, Tuple

from Infrastructure.Builders.ToolBuilder.ToolImageManager import AbstractToolImageManager
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrdering

from Infrastructure.Monitors.SharedLogic.SharedLogic import MonPolyVeriMonWrapper


class VeriMon:
    def __init__(self, image: AbstractToolImageManager, name, params: Dict[AnyStr, Any]):
        self.name = name
        self.logic = MonPolyVeriMonWrapper(image, name, params)

    def pre_processing(self, path_to_folder: AnyStr, data_file: AnyStr, signature_file: AnyStr, formula_file: AnyStr):
        self.logic.pre_processing(path_to_folder, data_file, signature_file, formula_file)

    def compile(self):
        self.logic.compile()

    def run_offline(self, time_on=None, time_out=None) -> Tuple[AnyStr, int]:
        return self.logic.run_offline(time_on, time_out)

    def variable_order(self) -> VariableOrdering:
        return self.logic.variable_order()

    def post_processing(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        return self.logic.post_processing(stdout_input)

