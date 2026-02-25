import os.path
import re
from typing import Dict, AnyStr, Any, Tuple, List, Optional

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.Builders.ToolBuilder.ToolImageManager import AbstractToolImageManager
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.OooVerdicts import OooVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrder, DefaultVariableOrder
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate
from Infrastructure.Monitors.SharedFunctions import parse_variable_order_timely
from Infrastructure.constants import POLICY_KEY, TRACE_KEY, SIGNATURE_KEY


class TimelyMon(AbstractMonitorTemplate):
    def __init__(self, image: AbstractToolImageManager, name, params: Dict[AnyStr, Any]):
        super().__init__(image, name, params)

    def preprocessing_data(
            self, path_to_folder: AnyStr, data_file: AnyStr,
            trace_source: InputOutputTraceFormats, path_manager: PathManager
    ):
        raise NotImplementedError("TimelyMon does not support non-automatic preprocessing for data")

    def preprocessing_policy(self, path_to_folder: AnyStr, policy_file: AnyStr, signature_file: AnyStr,
                             policy_source: InputOutputPolicyFormats, path_manager: PathManager):
        raise NotImplementedError("TimelyMon does not support non-automatic preprocessing for policies")

    def run_offline_command(self) -> Tuple[List[str], Optional[str]]:
        cmd = [self.params[POLICY_KEY], self.params[TRACE_KEY]]

        if not self.params.get("ignore_signature", False):
            cmd += ["--sig-file", self.params[SIGNATURE_KEY]]

        if "worker" in self.params:
            cmd += ["-w", str(self.params["worker"])]

        if "step" in self.params:
            cmd += ["--step", str(self.params["step"])]

        if "output_mode" in self.params:
            mode = self.params["output_mode"]
            cmd += ["-m", str(self.params["output_mode"])]
            if mode == 0:
                cmd += ["-o", str(self.params["output_file"])]
            elif mode == 2:
                cmd += ["-b", str(self.params["batches"])]

        if "clean_up_step" in self.params:
            cmd += ["--clean-up-step", str(self.params["clean_up_step"])]

        if "future_temporal_clean_up" in self.params:
            cmd += ["--future-temporal-clean-up", str(self.params["future_temporal_clean_up"])]

        if "past_temporal_clean_up" in self.params:
            cmd += ["--past-temporal-clean-up", str(self.params["past_temporal_clean_up"])]

        if "relational_clean_up" in self.params:
            cmd += ["--relational-clean-up", str(self.params["relational_clean_up"])]
        return cmd, None

    def post_processing(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        cmd = [self.params["formula"], "--check"]
        logs, code = self.image.run(self.params["folder"], cmd, measure=False)
        variable_order = VariableOrder(parse_variable_order_timely(logs)) if code == 0 else DefaultVariableOrder()
        if self.params["output_mode"] == 0:
            res_file_path = self.params["folder"] + "/" + self.params["output_file"]
            if os.path.exists(res_file_path):
                with open(res_file_path, "r") as f:
                    return parse_output_structure(f.read(), variable_order)
            else:
                return OooVerdicts(variable_order=variable_order)
        else:
            return parse_output_structure(stdout_input, variable_order)

    @staticmethod
    def supported_policy_formats() -> List[InputOutputPolicyFormats]:
        return [InputOutputPolicyFormats.MFOTL, InputOutputPolicyFormats.NEGATED_MFOTL]

    @staticmethod
    def supported_trace_formats() -> List[InputOutputTraceFormats]:
        return [InputOutputTraceFormats.CSV, InputOutputTraceFormats.OOO_CSV]


def parse_output_structure(input_val: AnyStr, variable_ordering) -> AbstractOutputStructure:
    def parse_pattern(pattern_str: str):
        match = re.match(r'@(\d+)\s*\(time point (\d+)\):\s*(.*)', pattern_str)
        if not match:
            raise ValueError()
        tuples_list = [[num for num in tup.split(',') if num] for tup in re.findall(r'\(([^)]*)\)', match.group(3))]
        return int(match.group(1)), int(match.group(2)), tuples_list

    verdicts = OooVerdicts(variable_order=variable_ordering)
    if input_val.strip() == "":
        return verdicts

    for line in input_val.strip().split("\n"):
        try:
            ts, tp, tuples = parse_pattern(line)
            verdicts.insert(tuples, tp, ts)
        except Exception():
            pass
    return verdicts
