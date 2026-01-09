import os
import re
from typing import Any, Dict, Tuple

from Infrastructure.Builders.ToolBuilder.ToolImageManager import AbstractToolImageManager
from Infrastructure.Builders.ProcessorBuilder.DataConverters.ReplayerConverter.ReplayerConverter import ReplayerConverter
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrdering, VariableOrder, DefaultVariableOrder
from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate


class MonPolyVeriMonWrapper(AbstractMonitorTemplate):
    def __init__(self, image: AbstractToolImageManager, name, params: Dict[str, Any]):
        super().__init__(image, name, params)
        self.replayer = ReplayerConverter(self.params["replayer"], self.params["path_to_project"])

    def pre_processing(self, path_to_folder: str, data_file: str, signature_file: str, formula_file: str):
        self.params["folder"] = path_to_folder
        self.params["signature"] = signature_file
        self.params["formula"] = formula_file

        trimmed_data_file = os.path.basename(data_file)
        self.replayer.convert(
            path_to_folder,
            data_file,
            self.name.lower(),
            trimmed_data_file,
            dest=f"{path_to_folder}/scratch",
            params=["-a", "0"]
        )

        self.params["data"] = f"scratch/{trimmed_data_file}.{self.name.lower()}"

    def run_offline(self, time_on=None, time_out=None) -> Tuple[str, int]:
        cmd = [
            "-sig", str(self.params["signature"]),
            "-formula", str(self.params["formula"]),
            "-log", str(self.params["data"])
        ]

        if "verified" in self.params:
            cmd += ["-verified"]
            if "no_mw" in self.params:
                cmd += ["-no_mw"]

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

        if "no_rw" in self.params:
            cmd += ["-no_rw"]

        return self.image.run(self.params["folder"], cmd, time_on, time_out)

    def variable_order(self) -> VariableOrdering:
        def parse_variable_order(text):
            match = re.search(r"The sequence of free variables is:\s*\((.*?)\)", text)
            result = match.group(1).split(",") if match and match.group(1) else []
            return [v.strip() for v in result]

        cmd = ["-sig", str(self.params["signature"]), "-formula", str(self.params["formula"]), "-check"]
        logs, code = self.image.run(self.params["folder"], cmd)
        if code == 0:
            return VariableOrder(parse_variable_order(logs))
        else:
            return DefaultVariableOrder()

    def post_processing(self, stdout_input: str) -> AbstractOutputStructure:
        def parse_pattern(pattern_str: str):
            match = re.match(r'@(\d+)\s*\(time point (\d+)\):\s*(.*)', pattern_str)
            tuples_list = [[num for num in tup.split(',') if num] for tup in re.findall(r'\(([^)]*)\)', match.group(3))]
            return int(match.group(1)), int(match.group(2)), tuples_list

        verdicts = Verdicts(variable_order=self.variable_order())
        if stdout_input == "":
            return verdicts

        for line in stdout_input.strip().split("\n"):
            ts, tp, vals = parse_pattern(line)
            verdicts.insert(vals, tp, ts)

        return verdicts
