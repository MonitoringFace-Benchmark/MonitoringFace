from typing import Dict, AnyStr, Any, Tuple, List, Optional

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.Monitors.MonitorExceptions import ToolException
from Infrastructure.Builders.ToolBuilder.AbstractToolImageManager import AbstractToolImageManager
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import DefaultVariableOrder
from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate
from Infrastructure.constants import POLICY_KEY, FOLDER_KEY, TRACE_KEY


class DejaVu(AbstractMonitorTemplate):
    def __init__(self, image: AbstractToolImageManager, name, params: Dict[AnyStr, Any]):
        super().__init__(image, name, params)

    def pre_processing(
            self, path_to_folder: AnyStr, data_file: AnyStr, signature_file: AnyStr, formula_file: AnyStr,
            trace_source: InputOutputTraceFormats, policy_source: InputOutputPolicyFormats, path_manager: PathManager
    ):
        raise NotImplementedError("DejaVu does not support non-automatic pre-processing")

    def compile(self):
        cmd = ["build", str(self.params[POLICY_KEY])]
        out, code = self.image.run(self.params[FOLDER_KEY], cmd, measure=False, name="")
        if code != 0:
            raise ToolException(f"DejaVu compilation failed with code {code} and output: {out}")

    def run_offline_command(self) -> Tuple[List[str], Optional[str]]:
        cmd = ["run", str(self.params[POLICY_KEY]), str(self.params[TRACE_KEY])]
        return cmd, ""

    def post_processing(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        prop_list = PropositionList(DefaultVariableOrder())
        if stdout_input == "":
            return prop_list

        lines = stdout_input.strip()
        for line in filter(lambda l: "violated on event number" in l, lines.split("\n")):
            num_str = line.split("number")[1].strip().rstrip(":")
            try:
                prop_list.insert(False, int(num_str))
            except ValueError:
                pass
        return prop_list

    @staticmethod
    def supported_policy_formats() -> List[InputOutputPolicyFormats]:
        return [InputOutputPolicyFormats.QTL]

    @staticmethod
    def supported_trace_formats() -> List[InputOutputTraceFormats]:
        return [InputOutputTraceFormats.DEJAVU, InputOutputTraceFormats.DEJAVU_LINEAR, InputOutputTraceFormats.DEJAVU_ENCODED]
