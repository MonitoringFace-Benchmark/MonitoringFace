from typing import Dict, AnyStr, Any, Tuple

from Infrastructure.Builders.ToolBuilder.AbstractToolImageManager import AbstractToolImageManager
from Infrastructure.Builders.ProcessorBuilder.DataConverters.ReplayerConverter.ReplayerConverter import ReplayerConverter
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PropositionTree
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrdering, DefaultVariableOrder
from Infrastructure.DataTypes.Verification.PDTParser import str_to_proposition_tree
from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate
import os


class WhyMon(AbstractMonitorTemplate):
    def __init__(self, image: AbstractToolImageManager, name, params: Dict[AnyStr, Any]):
        super().__init__(image, name, params)
        self.replayer = ReplayerConverter(self.params["replayer"], self.params["path_to_project"])

    def pre_processing(self, path_to_folder: AnyStr, data_file: AnyStr, signature_file: AnyStr, formula_file: AnyStr):
        self.params["folder"] = path_to_folder
        self.params["signature"] = signature_file
        self.params["formula"] = formula_file

        if "preprocessing" in self.params:
            if not self.params["preprocessing"]:
                self.params["data"] = data_file
                return

        trimmed_data_file = os.path.basename(data_file)
        self.replayer.convert(
            path_to_folder,
            data_file,
            "monpoly",
            trimmed_data_file,
            dest=f"{path_to_folder}/scratch",
            params=["-a", "0"]
        )

        self.params["data"] = f"scratch/{trimmed_data_file}.monpoly"

    def run_offline(self, time_on=None, time_out=None) -> Tuple[AnyStr, int]:
        cmd = [
            "-sig", str(self.params["signature"]),
            "-formula", str(self.params["formula"]),
            "-log", str(self.params["data"])
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

        out, code = self.image.run(self.params["folder"], cmd, time_on, time_out)
        return out, code

    def variable_order(self) -> VariableOrdering:
        return DefaultVariableOrder()

    def post_processing(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        if not stdout_input:
            return PropositionTree(self.variable_order())
        else:
            return str_to_proposition_tree(stdout_input.strip())
