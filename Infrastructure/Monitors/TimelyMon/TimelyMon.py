import os.path
import re

from typing import Dict, AnyStr, Any, Tuple

from Infrastructure.Builders.ProcessorBuilder.DataConverters.OutOfOrderConverter.OutOfOrderConverter import OutOfOrderConverter
from Infrastructure.Builders.ToolBuilder.ToolImageManager import AbstractToolImageManager
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.OooVerdicts import OooVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrdering, VariableOrder, DefaultVariableOrder
from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate


class TimelyMon(AbstractMonitorTemplate):
    def __init__(self, image: AbstractToolImageManager, name, params: Dict[AnyStr, Any]):
        super().__init__(image, name, params)

    def pre_processing(self, path_to_folder: AnyStr, data_file: AnyStr, signature_file: AnyStr, formula_file: AnyStr):
        self.params["folder"] = path_to_folder
        self.params["signature"] = signature_file
        self.params["formula"] = formula_file

        reordering = "mode" in self.params
        trimmed_data_file = os.path.basename(data_file)
        if reordering:
            OutOfOrderConverter(None, None).convert(
                path_to_folder, data_file, self.name.lower(),
                os.path.basename(data_file), dest=f"{path_to_folder}/scratch", params=self.params
            )

        self.params["data"] = f"scratch/{trimmed_data_file}.{self.name.lower()}" if reordering else data_file

    def run_offline(self, time_on=None, time_out=None) -> Tuple[AnyStr, int]:
        cmd = [self.params["formula"], self.params["data"]]
        
        if not self.params.get("ignore_signature", False):
           cmd += ["--sig-file", self.params["signature"]]

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

        return self.image.run(self.params["folder"], cmd, time_on, time_out)

    def variable_order(self) -> VariableOrdering:
        def parse_variable_order(text):
            match = re.search(r"Order of free variables:\s*\((.*?)\)", text)
            result = match.group(1).split(", ") if match and match.group(1) else []
            return [v.strip() for v in result]

        cmd = [self.params["formula"], "--check"]
        logs, code = self.image.run(self.params["folder"], cmd, measure=False)
        if code == 0:
            return VariableOrder(parse_variable_order(logs))
        else:
            return DefaultVariableOrder()

    def post_processing(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        variable_order = self.variable_order()
        if self.params["output_mode"] == 0:
            res_file_path = self.params["folder"] + "/" + self.params["output_file"]
            if os.path.exists(res_file_path):
                with open(res_file_path, "r") as f:
                    return parse_output_structure(f.read(), variable_order)
            else:
                return OooVerdicts(variable_order=variable_order)
        else:
            return parse_output_structure(stdout_input, variable_order)


def parse_output_structure(input_val: AnyStr, variable_ordering) -> AbstractOutputStructure:
    def parse_pattern(pattern_str: str):
        match = re.match(r'@(\d+)\s*\(time point (\d+)\):\s*(.*)', pattern_str)
        tuples_list = [[num for num in tup.split(',') if num] for tup in re.findall(r'\(([^)]*)\)', match.group(3))]
        return int(match.group(1)), int(match.group(2)), tuples_list

    verdicts = OooVerdicts(variable_order=variable_ordering)
    if input_val == "":
        return verdicts

    for line in input_val.strip().split("\n"):
        ts, tp, tuples = parse_pattern(line)
        verdicts.insert(tuples, tp, ts)
    return verdicts
