from abc import ABC, abstractmethod
from typing import AnyStr, Tuple

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure


class AbstractOracleTemplate(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def pre_process_data(self, path_to_folder: AnyStr, data_file: AnyStr, signature_file: AnyStr, formula_file: AnyStr):
        pass

    @abstractmethod
    def compute_result(self, time_on: int = None, time_out: int = None) -> Tuple[AnyStr, int]:
        pass

    @abstractmethod
    def post_process_data(self, std_out_str: AnyStr, output_file_name: AnyStr):
        pass

    @abstractmethod
    def verify(self, ath_to_result_folder: AnyStr, data_file: AnyStr, tool_verdicts: AbstractOutputStructure) -> Tuple[bool, AnyStr]:
        pass
