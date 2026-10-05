from typing import Dict, AnyStr, Any, Tuple, List, Optional

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.Builders.ToolBuilder.ToolImageManager import AbstractToolImageManager
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.Monitors.BaseMonitorTemplate import BaseMonitorTemplate, OnlineRunnable


class Dogwood(BaseMonitorTemplate, OnlineRunnable):
    """Dogwood's reference authorizer, fed MonPoly-format logs by EnfFlash's
    `dogwood-enforce` replayer: the policy is a Dogwood policy set whose
    `// decide:` header names the predicates that are authorization requests."""

    def __init__(self, image: AbstractToolImageManager, name, params: Dict[AnyStr, Any]):
        super().__init__(image, name, params)

    def preprocessing_data(
            self, path_to_folder: AnyStr, data_file: AnyStr,
            trace_source: InputOutputTraceFormats, path_manager: PathManager
    ):
        raise NotImplementedError("Dogwood does not support non-automatic preprocessing for data")

    def preprocessing_policy(
            self, path_to_folder: AnyStr, policy_file: AnyStr, signature_file: AnyStr,
            policy_source: InputOutputPolicyFormats, path_manager: PathManager
    ):
        raise NotImplementedError("Dogwood does not support non-automatic preprocessing for policies")

    def construct_online_command(self) -> Tuple[List[str], Optional[str]]:
        return [
            "-sig", "additional/signature.sig",
            "-formula", "additional/policy.policy"
        ], None

    @staticmethod
    def latency_marker() -> Optional[str]:
        pass

    def post_processing_online(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        pass

    @staticmethod
    def supported_policy_formats() -> List[InputOutputPolicyFormats]:
        return [InputOutputPolicyFormats.DOGWOOD]

    @staticmethod
    def supported_trace_formats() -> List[InputOutputTraceFormats]:
        return [InputOutputTraceFormats.MONPOLY]
