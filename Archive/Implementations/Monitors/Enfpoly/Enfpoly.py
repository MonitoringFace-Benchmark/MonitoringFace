from typing import Dict, AnyStr, Any, Tuple, List, Optional

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.Builders.ToolBuilder.ToolImageManager import AbstractToolImageManager
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.Monitors.BaseMonitorTemplate import BaseMonitorTemplate, OnlineRunnable


class Enfpoly(BaseMonitorTemplate, OnlineRunnable):
    """MonPoly's enforcement mode (`-enforce`, branch `enfpoly`); shares MonPoly's build."""

    def __init__(self, image: AbstractToolImageManager, name, params: Dict[AnyStr, Any]):
        super().__init__(image, name, params)

    def preprocessing_data(
            self, path_to_folder: AnyStr, data_file: AnyStr,
            trace_source: InputOutputTraceFormats, path_manager: PathManager
    ):
        raise NotImplementedError("Enfpoly does not support non-automatic preprocessing for data")

    def preprocessing_policy(
            self, path_to_folder: AnyStr, policy_file: AnyStr, signature_file: AnyStr,
            policy_source: InputOutputPolicyFormats, path_manager: PathManager
    ):
        raise NotImplementedError("Enfpoly does not support non-automatic preprocessing for policies")

    def construct_online_command(self) -> Tuple[List[str], Optional[str]]:
        cmd = [
            "-enforce",
            "-sig", "additional/signature.sig",
            "-formula", "additional/policy.policy"
        ]
        if "ignore_parse_errors" in self.params: cmd += ["-ignore_parse_errors"]
        return cmd, None

    @staticmethod
    def latency_marker() -> Optional[str]:
        pass

    def post_processing_online(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        pass

    @staticmethod
    def supported_policy_formats() -> List[InputOutputPolicyFormats]:
        return [InputOutputPolicyFormats.MFOTL]

    @staticmethod
    def supported_trace_formats() -> List[InputOutputTraceFormats]:
        return [InputOutputTraceFormats.MONPOLY]
