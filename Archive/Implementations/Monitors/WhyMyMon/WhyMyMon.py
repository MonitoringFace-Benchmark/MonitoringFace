from typing import Dict, AnyStr, Any, Tuple, List, Optional

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.Builders.ToolBuilder.AbstractToolImageManager import AbstractToolImageManager
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PropositionTree
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import DefaultVariableOrder
from Infrastructure.DataTypes.Verification.PDTParser import str_to_proposition_tree
from Infrastructure.Monitors.BaseMonitorTemplate import BaseMonitorTemplate, OfflineRunnable
from Infrastructure.constants import SIGNATURE_KEY, POLICY_KEY, TRACE_KEY


# todo structural issue with hardcoded monitors
# Similar to OnlineExperimentDriver build tool and whymymon and join in temporary container,
# then format is decided by tool


class WhyMyMon(BaseMonitorTemplate, OfflineRunnable):
    def __init__(self, image: AbstractToolImageManager, name, params: Dict[AnyStr, Any]):
        super().__init__(image, name, params)

    def preprocessing_data(self, path_to_folder: AnyStr, data_file: AnyStr, trace_source: InputOutputTraceFormats,
                           path_manager: PathManager):
        raise NotImplementedError("WhyMon does not support non-automatic preprocessing for policies")

    def preprocessing_policy(self, path_to_folder: AnyStr, policy_file: AnyStr, signature_file: AnyStr,
                             policy_source: InputOutputPolicyFormats, path_manager: PathManager):
        raise NotImplementedError("WhyMon does not support non-automatic preprocessing for policies")

    def construct_offline_command(self) -> Tuple[List[str], Optional[str]]:
        cmd = ["-cli"]

        # backend monitor (default: monpoly)
        monitor = self.params.get("monitor")
        if monitor in {"monpoly", "dejavu", "timelymon", "verimon"}:
            cmd += ["-monitor", monitor]

        # explain violations (vio, default) or satisfactions (sat)
        pref = self.params.get("pref")
        if pref in {"vio", "sat"}:
            cmd += ["-pref", pref]

        # checker mode (default: unverified)
        mode = self.params.get("mode")
        if mode in {"verified", "unverified"}:
            cmd += ["-mode", mode]

        cmd += [
            "-sig", str(self.params[SIGNATURE_KEY]),
            "-formula", str(self.params[POLICY_KEY]),
            "-log", str(self.params[TRACE_KEY]),
        ]

        return cmd, None

    def post_processing_offline(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        print(f"Raw output: {stdout_input}")
        if not stdout_input:
            return PropositionTree(DefaultVariableOrder())
        else:
            return str_to_proposition_tree(stdout_input.strip())

    @staticmethod
    def supported_policy_formats() -> List[InputOutputPolicyFormats]:
        return [
            InputOutputPolicyFormats.QTL, InputOutputPolicyFormats.NEGATED_MFOTL, InputOutputPolicyFormats.MFOTL
        ]

    @staticmethod
    def supported_trace_formats() -> List[InputOutputTraceFormats]:
        return [
            InputOutputTraceFormats.CSV, InputOutputTraceFormats.OOO_CSV,
            InputOutputTraceFormats.MONPOLY, InputOutputTraceFormats.MONPOLY_LINEAR,
            InputOutputTraceFormats.DEJAVU_ENCODED, InputOutputTraceFormats.DEJAVU, InputOutputTraceFormats.DEJAVU_LINEAR
        ]
