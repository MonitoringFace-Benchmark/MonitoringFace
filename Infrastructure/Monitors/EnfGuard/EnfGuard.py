from abc import ABC
from typing import Dict, AnyStr, Any

from Infrastructure.Builders.ToolBuilder import ToolImageManager
from Infrastructure.Builders.ProcessorBuilder.DataConverter.ReplayerConverter import ReplayerConverter
from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate
import os


class EnfGuard(AbstractMonitorTemplate, ABC):
    def __init__(self, image: ToolImageManager, name, params: Dict[AnyStr, Any]):
        super().__init__(image, name, params)
        self.replayer = ReplayerConverter(self.params["replayer"], self.params["path_to_build"])

    def pre_processing(self, path_to_folder: AnyStr, data_file: AnyStr, signature_file: AnyStr, formula_file: AnyStr):
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

    def run_offline(self, time_on=None, time_out=None) -> (AnyStr, int):
        cmd = [
            "-sig", str(self.params["signature"]),
            "-formula", str(self.params["formula"]),
            "-log", str(self.params["data"])
        ]

        cmd += ["-monitoring"]

        if "func" in self.params:
            cmd += ["-func", str(self.params["func"])]

        return self.image.run(self.params["folder"], cmd, time_on, time_out)

    def post_processing(self, stdout_input: AnyStr) -> list[AnyStr]:
        return stdout_input.split("\n")
