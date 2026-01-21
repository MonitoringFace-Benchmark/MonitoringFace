import time
from abc import ABC
from typing import Dict, AnyStr, Any

from Infrastructure.Builders.ProcessorBuilder.PolicyConverters.QTLTranslator.QTLTranslator import QTLTranslator
from Infrastructure.Builders.ToolBuilder import ToolImageManager
from Infrastructure.Builders.ProcessorBuilder.DataConverters.ReplayerConverter import ReplayerConverter
from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate
import os


class DejaVu(AbstractMonitorTemplate, ABC):
    def __init__(self, image: ToolImageManager, name, params: Dict[AnyStr, Any]):
        super().__init__(image, name, params)
        self.replayer = ReplayerConverter(self.params["replayer"], self.params["path_to_build"])
        self.translator = QTLTranslator(self.params["translator"], self.params["path_to_build"])

    def pre_processing(self, path_to_folder: AnyStr, data_file: AnyStr, signature_file: AnyStr, formula_file: AnyStr):
        self.params["folder"] = path_to_folder

        # make scratch a constant
        trimmed_data_file = os.path.basename(data_file)
        self.replayer.convert(
            path_to_folder,
            data_file,
            "dejavu-encoded",
            trimmed_data_file,
            dest=f"{path_to_folder}/scratch",
            params=["-a", "0", "-d" "e"]
        )
        trimmed_formula_file = os.path.basename(formula_file)
        self.translator.convert(
            path_to_folder,
            formula_file,
            "qtl",
            trimmed_formula_file,
            dest=f"{path_to_folder}/scratch",
            params=["-n", "-e", "e"]
        )

        self.params["data"] = f"scratch/{trimmed_data_file}.dejavu-encoded"
        self.params["formula"] = f"scratch/{trimmed_formula_file}.qtl"

    def run_offline(self, time_on=None, time_out=None) -> (AnyStr, int):
        cmd = [
            str(self.params["formula"]),
            str(self.params["data"])
        ]
        return self.image.run(self.params["folder"], cmd, time_on, time_out)

    def post_processing(self, stdout_input: AnyStr) -> list[AnyStr]:
        return stdout_input.split("\n")


