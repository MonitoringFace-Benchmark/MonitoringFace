from typing import Dict, AnyStr, Any, Tuple, List, Optional

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.Builders.ToolBuilder.ToolImageManager import AbstractToolImageManager
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrder, DefaultVariableOrder
from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate
from Infrastructure.Monitors.SharedFunctions import parse_pattern, parse_variable_order_monpoly


class MonPoly(AbstractMonitorTemplate):
    def __init__(self, image: AbstractToolImageManager, name, params: Dict[AnyStr, Any]):
        super().__init__(image, name, params)

    def pre_processing(
            self, path_to_folder: AnyStr, data_file: AnyStr, signature_file: AnyStr, formula_file: AnyStr,
            trace_source: InputOutputTraceFormats, trace_target: InputOutputTraceFormats,
            policy_source: InputOutputPolicyFormats, policy_target: InputOutputPolicyFormats, path_manager: PathManager
    ):
        raise NotImplementedError("MonPoly does not support non-automatic pre-processing")

    def run_offline_command(self) -> Tuple[List[str], Optional[str]]:
        cmd = [
            "-sig", str(self.params["signature"]),
            "-formula", str(self.params["formula"]),
            "-log", str(self.params["data"])
        ]

        if "negate" in self.params:
            cmd += ["-negate"]

        if "no_trigger" in self.params:
            cmd += ["-no_trigger"]

        if "unfold_let" in self.params:
            val = self.params["unfold_let"]
            cmd += ["-unfold_let"]
            if val == "full":
                cmd += ["full"]
            elif val == "smart":
                cmd += ["smart"]
            else:
                cmd += ["no"]

        if "nonewlastts" in self.params:
            cmd += ["-nonewlastts"]

        if "no_rw" in self.params:
            cmd += ["-no_rw"]
        return cmd, None

    def post_processing(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        cmd = ["-sig", str(self.params["signature"]), "-formula", str(self.params["formula"]), "-check"]
        logs, code = self.image.run(self.params["folder"], cmd, measure=False)
        variable_order = VariableOrder(parse_variable_order_monpoly(logs)) if code == 0 else DefaultVariableOrder()
        verdicts = Verdicts(variable_order=variable_order)

        if stdout_input == "":
            return verdicts

        for line in stdout_input.strip().split("\n"):
            try:
                ts, tp, vals = parse_pattern(line)
                verdicts.insert(vals, tp, ts)
            except Exception:
                if line.startswith("@MaxTS"):
                    pass
                else:
                    raise ValueError(f"Could not parse line: {line}")

        return verdicts

    @staticmethod
    def supported_policy_formats() -> List[InputOutputPolicyFormats]:
        return [InputOutputPolicyFormats.MFOTL, InputOutputPolicyFormats.NEGATED_MFOTL]

    @staticmethod
    def supported_trace_formats() -> List[InputOutputTraceFormats]:
        return [InputOutputTraceFormats.MONPOLY, InputOutputTraceFormats.MONPOLY_LINEAR]
