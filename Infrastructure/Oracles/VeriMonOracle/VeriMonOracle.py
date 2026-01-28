import copy
import os
import re
from pathlib import Path
from typing import AnyStr, Optional, Tuple

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Compare.Comparing import comparing
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts
from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate
from Infrastructure.Oracles.AbstractOracleTemplate import AbstractOracleTemplate


class VeriMonOracle(AbstractOracleTemplate):
    def __init__(self, veri_mon: AbstractMonitorTemplate, parameters):
        super().__init__()
        self.verimon = copy.deepcopy(veri_mon)
        self.verimon.name = "VeriMon"
        self.parameters = parameters

    def pre_process_data(self, path_to_folder_inner: AnyStr, data_file: AnyStr, signature_file: AnyStr, formula_file: AnyStr):
        self.verimon.pre_processing(path_to_folder_inner, data_file, signature_file, formula_file)

    def compute_result(self, time_on=None, time_out=None) -> Tuple[AnyStr, int]:
        cmd = [
            "-sig", str(self.verimon.logic.params["signature"]),
            "-formula", str(self.verimon.logic.params["formula"]),
            "-log", str(self.verimon.logic.params["data"]),
            "-verified"
        ]
        return self.verimon.logic.image.run(self.verimon.logic.params["folder"], cmd, time_on, time_out)

    def post_process_data(self, std_out_str, output_file_name):
        with open(output_file_name, "w") as file:
            file.write(std_out_str)

    def verify(self, path_to_result_folder: AnyStr, data_file: AnyStr, tool_verdicts: AbstractOutputStructure, sig_file, formula_file, case_study_mapper=None) -> Tuple[bool, AnyStr]:
        oracle_verdicts = self.get_oracle_verdicts(path_to_result_folder, data_file, sig_file, formula_file, case_study_mapper)
        return comparing(oracle_verdicts, tool_verdicts)

    def get_oracle_verdicts(self, path_to_result_folder, data_file, sig_file, formula_file, case_study_mapper=None) -> AbstractOutputStructure:
        def extract_data_number(path: str) -> Optional[int]:
            m = re.compile(r"^data_(\d+)\.csv$", re.IGNORECASE).match(Path(path).name)
            return int(m.group(1)) if m else None

        if case_study_mapper:
            data_file_size = case_study_mapper.result_id((data_file, formula_file, sig_file))
        else:
            data_file_size = extract_data_number(data_file)
        self.verimon.logic.params["folder"] = path_to_result_folder
        self.verimon.logic.params["signature"] = sig_file
        self.verimon.logic.params["formula"] = formula_file
        variable_order = self.verimon.variable_order()

        result_file = path_to_result_folder + f"/result/result_{data_file_size}.res"
        if os.path.exists(result_file):
            with open(result_file, "r") as file:
                return self.verimon.post_processing(file.read())
        else:
            return Verdicts(variable_order=variable_order)
