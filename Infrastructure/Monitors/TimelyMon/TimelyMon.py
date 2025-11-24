import os.path
import time
import re

from abc import ABC
from typing import Dict, AnyStr, Any

from Infrastructure.Builders.ToolBuilder.ToolImageManager import ToolImageManager
from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate


class TimelyMon(AbstractMonitorTemplate, ABC):
    def __init__(self, image: ToolImageManager, name, params: Dict[AnyStr, Any]):
        super().__init__(image, name, params)

    def pre_processing(self, path_to_folder: AnyStr,
                       data_file: AnyStr,
                       signature_file: AnyStr,
                       formula_file: AnyStr):
        self.params["folder"] = path_to_folder

        self.params["data"] = data_file
        self.params["signature"] = signature_file
        self.params["formula"] = formula_file

    def run_offline(self, time_on=None, time_out=None) -> (AnyStr, int):
        cmd = [self.params["formula"], self.params["data"], "--sig-file", self.params["signature"]]
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

    def post_processing(self, stdout_input: AnyStr) -> list[AnyStr]:
        # sort and rewrite input
        if self.params["output_mode"] == 0:
            res_file_path = self.params["folder"] + "/" + self.params["output_file"]
            if os.path.exists(res_file_path):
                with open(res_file_path, "r") as f:
                    return parse_list_to_verifiable_output(f.readlines())
            else:
                return [""]
        else:
            return parse_str_to_verifiable_output(stdout_input)


def parse_str_to_verifiable_output(input_val: AnyStr) -> list[AnyStr]:
    return parse_list_to_verifiable_output(input_val.splitlines())


def parse_list_to_verifiable_output(input_val: list[AnyStr]) -> list[AnyStr]:
    collect: Dict[str, list[list[str]]] = {}

    for line in input_val:
        prefix, val = parse(line)
        collect.setdefault(prefix, []).extend(val)

    return [f"{key}: " + " ".join(f"({','.join(map(str, item))})" for item in sorted(collect[key])) for key in sorted(collect)]


def parse(line: AnyStr) -> (AnyStr, list[list[AnyStr]]):
    prefix, postfix = line.split(":")
    tuples = [list(match.split(',')) for match in re.findall(r'\(([^)]+)\)', postfix)]
    return prefix, tuples


if __name__ == "__main__":
    d = {"worker": 6, "output_mode": 1, "output_file": "scratch/test.txt"}
    timely = ToolImageManager("TimelyMon", "development", False,
                              "/Infrastructure/build")

    tm = TimelyMon(timely, "timely", d)
    tm.pre_processing(
        "/Users/krq770/Desktop/MonitoringFace/Infrastructure/experiments/Nokia/data",
        data_file="Trace/trace.csv",
        formula_file="Formula/formula_delete.mfotl",
        signature_file="Signature/sig.sig"
    )

    start_time = time.time()
    (x, y) = tm.run_offline(None, 300)
    end_time = time.time()

    print(x)
    print(y)

    execution_time = end_time - start_time
    print(f"Function executed in {execution_time:.4f} seconds")

    print(tm.post_processing(x))
