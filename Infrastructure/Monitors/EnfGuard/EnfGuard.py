from typing import Dict, AnyStr, Any, Tuple, List, Optional

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.Builders.ToolBuilder.AbstractToolImageManager import AbstractToolImageManager
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import DefaultVariableOrder
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate


class EnfGuard(AbstractMonitorTemplate):
    def __init__(self, image: AbstractToolImageManager, name, params: Dict[AnyStr, Any]):
        super().__init__(image, name, params)

    def pre_processing(
            self, path_to_folder: AnyStr, data_file: AnyStr, signature_file: AnyStr, formula_file: AnyStr,
            trace_source: InputOutputTraceFormats, trace_target: InputOutputTraceFormats,
            policy_source: InputOutputPolicyFormats, policy_target: InputOutputPolicyFormats, path_manager: PathManager
    ):
        raise NotImplementedError("EnfGuard does not support non-automatic pre-processing")

    def run_offline_command(self) -> Tuple[List[str], Optional[str]]:
        cmd = [
            "-sig", str(self.params["signature"]),
            "-formula", str(self.params["formula"]),
            "-log", str(self.params["data"])
        ]

        if self.params.get("monitoring", False):
            cmd += ["-monitoring"]
        if "func" in self.params:
            cmd += ["-func", str(self.params["func"])]
        return cmd, None

    def post_processing(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        return PropositionList(DefaultVariableOrder())

    @staticmethod
    def supported_policy_formats() -> List[InputOutputPolicyFormats]:
        return [InputOutputPolicyFormats.MFOTL, InputOutputPolicyFormats.NEGATED_MFOTL]

    @staticmethod
    def supported_trace_formats() -> List[InputOutputTraceFormats]:
        return [InputOutputTraceFormats.MONPOLY, InputOutputTraceFormats.MONPOLY_LINEAR]
