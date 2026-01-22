from typing import Dict, AnyStr, Any, Tuple

from Infrastructure.Builders.ProcessorBuilder.PolicyConverters.QTLTranslator.QTLTranslator import QTLTranslator
from Infrastructure.Builders.ToolBuilder.AbstractToolImageManager import AbstractToolImageManager
from Infrastructure.Builders.ProcessorBuilder.DataConverters.ReplayerConverter.ReplayerConverter import ReplayerConverter
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrdering, DefaultVariableOrder
from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate
import os


class DejaVu(AbstractMonitorTemplate):
    def __init__(self, image: AbstractToolImageManager, name, params: Dict[AnyStr, Any]):
        super().__init__(image, name, params)
        self.replayer = ReplayerConverter(self.params["replayer"], self.params["path_to_project"])
        self.translator = QTLTranslator(self.params["translator"], self.params["path_to_project"])

    def pre_processing(self, path_to_folder: AnyStr, data_file: AnyStr, signature_file: AnyStr, formula_file: AnyStr):
        self.params["folder"] = path_to_folder

        trimmed_data_file = os.path.basename(data_file)
        self.replayer.convert(
            path_to_folder,
            data_file,
            "dejavu-encoded",
            trimmed_data_file,
            dest=f"{path_to_folder}/scratch",
            params=["-a", "0", "-d", "e"]
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

    def run_offline(self, time_on=None, time_out=None) -> Tuple[AnyStr, int]:
        cmd = [
            str(self.params["formula"]),
            str(self.params["data"])
        ]
        return self.image.run(self.params["folder"], cmd, time_on, time_out, measure=False)

    def variable_order(self) -> VariableOrdering:
        return DefaultVariableOrder()

    def post_processing(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        prop_list = PropositionList()
        if stdout_input:
            lines = stdout_input.strip()
            for line in filter(lambda l: "violated on event number" in l, lines.split("\n")):
                if len(line) > 1:
                    num_str = line[1].strip().rstrip(":")
                    try:
                        prop_list.insert(False, int(num_str))
                    except ValueError:
                        pass
        return prop_list
