from typing import AnyStr, Tuple, List, Optional

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import DefaultVariableOrder
from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate
from Infrastructure.constants import FOLDER_KEY, POLICY_KEY, TRACE_KEY


class TeSSLa(AbstractMonitorTemplate):
    def __init__(self, image: AnyStr, name: str, params: AnyStr):
        super().__init__(image, name, params)

    def preprocessing_data(
            self, path_to_folder: AnyStr, data_file: AnyStr,
            trace_source: InputOutputTraceFormats, path_manager: PathManager
    ):
        self.params[TRACE_KEY] = data_file.removeprefix("data/")

    def preprocessing_policy(
            self, path_to_folder: AnyStr, policy_file: AnyStr, signature_file: AnyStr,
            policy_source: InputOutputPolicyFormats, path_manager: PathManager
    ):
        self.params[FOLDER_KEY] = path_to_folder
        self.params[POLICY_KEY] = policy_file.removeprefix("data/")

    def construct_offline_command(self, time_on=None, time_out=None) -> Tuple[List[str], Optional[str]]:
        cmd = [self.params[POLICY_KEY], self.params[TRACE_KEY]]
        return cmd, "interpreter"

    def post_processing(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        return PropositionList(DefaultVariableOrder())

    @staticmethod
    def supported_policy_formats() -> List[InputOutputPolicyFormats]:
        pass

    @staticmethod
    def supported_trace_formats() -> List[InputOutputTraceFormats]:
        pass
