from abc import ABC, abstractmethod
from typing import AnyStr, Tuple

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure


class AbstractOracleTemplate(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def pre_process_data(
            self, path_to_folder: str, trace_source_format: InputOutputTraceFormats,
            policy_source_format: InputOutputPolicyFormats, data_file: str, signature_file: str, policy_file: str,
            path_manager: PathManager
    ):
        pass

    @abstractmethod
    def compute_result(self, time_on: int = None, time_out: int = None) -> Tuple[AnyStr, int]:
        pass

    @abstractmethod
    def post_process_data(self, std_out_str: AnyStr, output_file_name: AnyStr):
        pass

    @abstractmethod
    def verify(self, path_to_result_folder: AnyStr, data_file: AnyStr, tool_verdicts: AbstractOutputStructure, sig_file, formula_file, case_study_mapper=None) -> Tuple[bool, AnyStr]:
        pass
