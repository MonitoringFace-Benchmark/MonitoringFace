from Infrastructure.DataTypes.Verification.OutputStructures.Strength import Comparison
from abc import ABC, abstractmethod
from typing import AnyStr, Optional, List

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.Builders.BuilderUtilities import ContainerRun
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure


class AbstractOracleTemplate(ABC):
    def __init__(self, monitor, params):
        pass

    def supported_policy_formats(self) -> Optional[List[InputOutputPolicyFormats]]:
        return None

    @abstractmethod
    def pre_process_data(
            self, path_to_folder: str, trace_source_format: InputOutputTraceFormats,
            policy_source_format: InputOutputPolicyFormats, data_file: str, signature_file: str, policy_file: str,
            path_manager: PathManager
    ):
        pass

    @abstractmethod
    def compute_result(self, time_on: int = None, time_out: int = None) -> ContainerRun:
        """The oracle tool's run. post_process_data receives its stdout, the
        verdicts; a failed run's error message shows both streams."""
        pass

    @abstractmethod
    def post_process_data(self, std_out_str: AnyStr, output_file_name: AnyStr):
        pass

    @abstractmethod
    def verify(
            self, path_to_result_folder: str, data_file: str, tool_verdicts: AbstractOutputStructure,
            sig_file: Optional[str], policy_file: str, result_file: str) -> Comparison:
        pass
