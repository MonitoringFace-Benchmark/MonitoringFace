from typing import AnyStr

from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate
from Infrastructure.Oracles.AbstractOracleTemplate import AbstractOracleTemplate


class VeriMonOracle(AbstractOracleTemplate):
    def __init__(self, veri_mon: AbstractMonitorTemplate, parameters):
        super().__init__()
        self.verimon = veri_mon
        self.verimon.name = "VeriMon"
        self.parameters = parameters

    def pre_process_data(self, path_to_folder_inner: AnyStr, data_file: AnyStr, signature_file: AnyStr, formula_file: AnyStr):
        self.verimon.pre_processing(path_to_folder_inner, data_file, signature_file, formula_file)

    def compute_result(self, time_on=None, time_out=None) -> (AnyStr, int):
        cmd = [
            "-sig", str(self.verimon.params["signature"]),
            "-formula", str(self.verimon.params["formula"]),
            "-log", str(self.verimon.params["data"]),
            "-verified"
        ]
        return self.verimon.image.run(self.verimon.params["folder"], cmd, time_on, time_out)

    def post_process_data(self, std_out_str, output_file_name):
        with open(output_file_name, "w") as file:
            file.write(std_out_str)

    def verify(self, path_to_data, result_file_oracle, tool_input):
        pass
