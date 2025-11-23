from typing import AnyStr

from Infrastructure.Oracles.AbstractOracleTemplate import AbstractOracleTemplate


class DataGolfOracle(AbstractOracleTemplate):

    def pre_process_data(self, path_to_folder: AnyStr, data_file: AnyStr, signature_file: AnyStr, formula_file: AnyStr):
        pass

    def compute_result(self, time_on=None, time_out=None) -> (AnyStr, int):
        pass

    def post_process_data(self, std_out_str, output_file_name):
        pass
