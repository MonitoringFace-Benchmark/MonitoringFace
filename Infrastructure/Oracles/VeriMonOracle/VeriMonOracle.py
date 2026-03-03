import copy
import os
from typing import AnyStr, Tuple

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Compare.Comparing import comparing
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrder, DefaultVariableOrder
from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate
from Infrastructure.Monitors.SharedFunctions import parse_variable_order_monpoly
from Infrastructure.Oracles.AbstractOracleTemplate import AbstractOracleTemplate
from Infrastructure.constants import SIGNATURE_KEY, POLICY_KEY, FOLDER_KEY, TRACE_KEY


class VeriMonOracle(AbstractOracleTemplate):
    def __init__(self, veri_mon: AbstractMonitorTemplate, parameters):
        super().__init__()
        self.verimon = copy.deepcopy(veri_mon)
        self.verimon.name = "VeriMon"
        self.parameters = parameters

    def pre_process_data(
            self, path_to_folder: str, trace_source_format: InputOutputTraceFormats,
            policy_source_format: InputOutputPolicyFormats, data_file: str, signature_file: str, policy_file: str,
            path_manager: PathManager
    ):
        self.verimon.preprocessing(
            path_to_folder, trace_source_format, policy_source_format, data_file, signature_file, policy_file, path_manager
        )

    def compute_result(self, time_on=None, time_out=None) -> Tuple[AnyStr, int]:
        cmd = [
            "-sig", str(self.verimon.params[SIGNATURE_KEY]),
            "-formula", str(self.verimon.params[POLICY_KEY]),
            "-log", str(self.verimon.params[TRACE_KEY]),
            "-verified"
        ]
        return self.verimon.image.run(self.verimon.params[FOLDER_KEY], cmd, time_on, time_out)

    def post_process_data(self, std_out_str, output_file_name):
        with open(output_file_name, "w") as file:
            file.write(std_out_str)

    def verify(self, path_to_result_folder: AnyStr, data_file: AnyStr, tool_verdicts: AbstractOutputStructure, sig_file, formula_file, result_file) -> Tuple[bool, AnyStr]:
        oracle_verdicts = self.get_oracle_verdicts(path_to_result_folder, sig_file, formula_file, result_file)
        return comparing(oracle_verdicts, tool_verdicts)

    def get_oracle_verdicts(self, path_to_result_folder, sig_file, formula_file, result_file) -> AbstractOutputStructure:
        self.verimon.params[FOLDER_KEY] = path_to_result_folder
        self.verimon.params[SIGNATURE_KEY] = sig_file
        self.verimon.params[POLICY_KEY] = formula_file
        cmd = ["-sig", str(self.verimon.params[SIGNATURE_KEY]), "-formula", str(self.verimon.params[POLICY_KEY]), "-check"]
        logs, code = self.verimon.image.run(self.verimon.params[FOLDER_KEY], cmd, measure=False)
        variable_order = VariableOrder(parse_variable_order_monpoly(logs)) if code == 0 else DefaultVariableOrder()

        if os.path.exists(result_file):
            with open(result_file, "r") as file:
                return self.verimon.post_processing(file.read())
        else:
            return Verdicts(variable_order=variable_order)
