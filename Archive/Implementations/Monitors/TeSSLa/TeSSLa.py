from typing import AnyStr, Tuple, List, Optional

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import DefaultVariableOrder
from Infrastructure.Monitors.BaseMonitorTemplate import BaseMonitorTemplate, OfflineRunnable
from Infrastructure.constants import FOLDER_KEY, POLICY_KEY, TRACE_KEY


class TeSSLa(BaseMonitorTemplate, OfflineRunnable):
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
        # The data folder itself is the container mount (WORKDIR=/data), so paths must be
        # relative to it. Strip any leading "data/" here so this holds whether the framework
        # took the auto-conversion (distance 0) path or the custom preprocessing path.
        policy = str(self.params[POLICY_KEY]).removeprefix("data/")
        trace = str(self.params[TRACE_KEY]).removeprefix("data/")
        cmd = [policy, trace]
        return cmd, "interpreter"

    def post_processing_offline(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        return PropositionList(DefaultVariableOrder())

    @staticmethod
    def supported_policy_formats() -> List[InputOutputPolicyFormats]:
        return [InputOutputPolicyFormats.SRV_POLICY]

    @staticmethod
    def supported_trace_formats() -> List[InputOutputTraceFormats]:
        return [InputOutputTraceFormats.SRV_TRACE]
