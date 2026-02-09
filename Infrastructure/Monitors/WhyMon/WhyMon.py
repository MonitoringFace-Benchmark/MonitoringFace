from typing import Dict, AnyStr, Any, Tuple, List, Optional

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.Builders.ToolBuilder.AbstractToolImageManager import AbstractToolImageManager
from Infrastructure.Builders.ProcessorBuilder.DataConverters.ReplayerConverter.ReplayerConverter import ReplayerConverter
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PropositionTree
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import DefaultVariableOrder
from Infrastructure.DataTypes.Verification.PDTParser import str_to_proposition_tree
from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate
from Infrastructure.constants import SIGNATURE_KEY, POLICY_KEY, TRACE_KEY


class WhyMon(AbstractMonitorTemplate):
    def __init__(self, image: AbstractToolImageManager, name, params: Dict[AnyStr, Any]):
        super().__init__(image, name, params)
        self.replayer = ReplayerConverter(self.params["replayer"], self.params["path_to_project"])

    def pre_processing(
            self, path_to_folder: AnyStr, data_file: AnyStr, signature_file: AnyStr, formula_file: AnyStr,
            trace_source: InputOutputTraceFormats, policy_source: InputOutputPolicyFormats, path_manager: PathManager
    ):
        raise NotImplementedError("WhyMon does not support non-automatic pre-processing")

    def run_offline_command(self) -> Tuple[List[str], Optional[str]]:
        cmd = [
            "-sig", str(self.params[SIGNATURE_KEY]),
            "-formula", str(self.params[POLICY_KEY]),
            "-log", str(self.params[TRACE_KEY])
        ]

        if "mode" in self.params:
            val = self.params["mode"]
            cmd += ["-mode"]
            if val == "unverified":
                cmd += ["unverified"]
            elif val == "verified":
                cmd += ["verified"]
            elif val == "light":
                cmd += ["light"]
            else:
                cmd += ["light"]

        if "measure" in self.params:
            val = self.params["measure"]
            cmd += ["-measure"]
            if val == "size":
                cmd += ["size"]
            elif val == "none":
                cmd += ["none"]
            else:
                cmd += ["size"]
        return cmd, None

    def post_processing(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        if not stdout_input:
            return PropositionTree(DefaultVariableOrder())
        else:
            return str_to_proposition_tree(stdout_input.strip())

    @staticmethod
    def supported_policy_formats() -> List[InputOutputPolicyFormats]:
        return [
            InputOutputPolicyFormats.UNICODE_MFOTL, InputOutputPolicyFormats.NEGATED_MFOTL,
            InputOutputPolicyFormats.MFOTL, InputOutputPolicyFormats.NEGATED_UNICODE_MFOTL
        ]

    @staticmethod
    def supported_trace_formats() -> List[InputOutputTraceFormats]:
        return [InputOutputTraceFormats.MONPOLY, InputOutputTraceFormats.MONPOLY_LINEAR]
