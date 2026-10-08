from typing import Dict, AnyStr, Any, Tuple, List, Optional

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.Builders.ToolBuilder.AbstractToolImageManager import AbstractToolImageManager
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import DefaultVariableOrder
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.Monitors.BaseMonitorTemplate import BaseMonitorTemplate, OfflineRunnable, OnlineRunnable, \
    policy_companion
from Infrastructure.constants import SIGNATURE_KEY, POLICY_KEY, TRACE_KEY, POLICY_FUNCTIONS_KEY


class EnfGuard(BaseMonitorTemplate, OfflineRunnable, OnlineRunnable):
    def __init__(self, image: AbstractToolImageManager, name, params: Dict[AnyStr, Any]):
        super().__init__(image, name, params)

    def preprocessing_data(
            self, path_to_folder: AnyStr, data_file: AnyStr,
            trace_source: InputOutputTraceFormats, path_manager: PathManager
    ):
        raise NotImplementedError("EnfGuard does not support non-automatic preprocessing for data")

    def preprocessing_policy(
            self, path_to_folder: AnyStr, policy_file: AnyStr, signature_file: AnyStr,
            policy_source: InputOutputPolicyFormats, path_manager: PathManager
    ):
        raise NotImplementedError("EnfGuard does not support non-automatic preprocessing for policies")

    def construct_offline_command(self) -> Tuple[List[str], Optional[str]]:
        cmd = [
            "-sig", str(self.params[SIGNATURE_KEY]),
            "-formula", str(self.params[POLICY_KEY]),
            "-log", str(self.params[TRACE_KEY])
        ]

        if self.params.get("monitoring", False):
            cmd += ["-monitoring"]
        functions = policy_companion(self.params, POLICY_FUNCTIONS_KEY, online=False) or self.params.get("func")
        if functions:
            cmd += ["-func", str(functions)]
        return cmd, None

    def post_processing_offline(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        return PropositionList(DefaultVariableOrder())

    def construct_online_command(self) -> Tuple[List[str], Optional[str]]:
        cmd = [
            "-sig", "additional/signature.sig",
            "-formula", "additional/policy.policy"
        ]
        if self.params.get("monitoring", False):
            cmd += ["-monitoring"]
        functions = policy_companion(self.params, POLICY_FUNCTIONS_KEY, online=True)
        if functions:
            cmd += ["-func", functions]
        return cmd, None

    @staticmethod
    def latency_marker() -> Optional[str]:
        pass

    def post_processing_online(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        pass

    @staticmethod
    def supported_policy_formats() -> List[InputOutputPolicyFormats]:
        return [InputOutputPolicyFormats.UNICODE_MFOTL, InputOutputPolicyFormats.MFOTL, InputOutputPolicyFormats.NEGATED_MFOTL]

    @staticmethod
    def supported_trace_formats() -> List[InputOutputTraceFormats]:
        return [InputOutputTraceFormats.MONPOLY, InputOutputTraceFormats.MONPOLY_LINEAR]
