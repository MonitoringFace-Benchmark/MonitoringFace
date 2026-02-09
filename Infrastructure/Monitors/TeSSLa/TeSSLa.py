from typing import AnyStr, Tuple, List, Optional

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import DefaultVariableOrder
from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate


class TeSSLa(AbstractMonitorTemplate):
    def __init__(self, image: AnyStr, name: str, params: AnyStr):
        super().__init__(image, name, params)

    def pre_processing(
            self, path_to_folder: AnyStr, data_file: AnyStr, signature_file: AnyStr, formula_file: AnyStr,
            trace_source: InputOutputTraceFormats, policy_source: InputOutputPolicyFormats, path_manager: PathManager
    ):
        self.params["folder"] = path_to_folder
        self.params["formula"] = formula_file.removeprefix("data/")
        self.params["data"] = data_file.removeprefix("data/")

    def run_offline_command(self, time_on=None, time_out=None) -> Tuple[List[str], Optional[str]]:
        cmd = [self.params["formula"], self.params["data"]]
        return cmd, "interpreter"

    def post_processing(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        return PropositionList(DefaultVariableOrder())

    @staticmethod
    def supported_policy_formats() -> List[InputOutputPolicyFormats]:
        pass

    @staticmethod
    def supported_trace_formats() -> List[InputOutputTraceFormats]:
        pass
