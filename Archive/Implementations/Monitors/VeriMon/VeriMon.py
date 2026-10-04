from dataclasses import replace
from typing import Dict, AnyStr, Any, Tuple, List, Optional

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.Builders.ToolBuilder.ToolImageManager import AbstractToolImageManager
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrder, DefaultVariableOrder
from Infrastructure.Monitors.BaseMonitorTemplate import BaseMonitorTemplate, OfflineRunnable, OnlineRunnable
from Archive.Implementations.Monitors.BoundedFuture import bound_policy_to_trace
from Archive.Implementations.Monitors.SharedFunctions import parse_variable_order_monpoly, parse_monpoly_output
from Infrastructure.Provenance.Provenance import PreprocessingResult
from Infrastructure.constants import SIGNATURE_KEY, POLICY_KEY, TRACE_KEY


class VeriMon(BaseMonitorTemplate, OfflineRunnable, OnlineRunnable):
    def __init__(self, image: AbstractToolImageManager, name, params: Dict[AnyStr, Any]):
        super().__init__(image, name, params)

    def preprocessing(
            self, path_to_folder: str, trace_source_format: InputOutputTraceFormats,
            policy_source_format: InputOutputPolicyFormats, data_file: str, signature_file: str, policy_file: str,
            path_manager: PathManager, verbose=False
    ) -> PreprocessingResult:
        """Bounds the policy's unbounded future operators by the trace's
        timestamp span (see BoundedFuture), which VeriMon would otherwise reject.
        `bound_unbounded_future: false` in the params turns this off."""
        result = super().preprocessing(
            path_to_folder, trace_source_format, policy_source_format, data_file, signature_file, policy_file,
            path_manager, verbose
        )
        if not self.params.get("bound_unbounded_future", True):
            return result
        step = bound_policy_to_trace(self.params, path_to_folder)
        if step is None:
            return result
        if verbose:
            print(f"Unbounded future operators bounded by the trace's timestamp span {step.params['horizon']}")
        records = [
            replace(record, steps=record.steps + [step], as_seen_by_tool=self.params[POLICY_KEY])
            if record.kind == "policy" else record
            for record in result.records
        ]
        return replace(result, records=records)

    def preprocessing_data(
            self, path_to_folder: AnyStr, data_file: AnyStr,
            trace_source: InputOutputTraceFormats, path_manager: PathManager
    ):
        raise NotImplementedError("VeriMon does not support non-automatic preprocessing for data")

    def preprocessing_policy(
            self, path_to_folder: AnyStr, policy_file: AnyStr, signature_file: AnyStr,
            policy_source: InputOutputPolicyFormats, path_manager: PathManager
    ):
        raise NotImplementedError("VeriMon does not support non-automatic preprocessing for policies")

    def construct_offline_command(self) -> Tuple[List[str], Optional[str]]:
        cmd = [
            "-sig", str(self.params[SIGNATURE_KEY]),
            "-formula", str(self.params[POLICY_KEY]),
            "-log", str(self.params[TRACE_KEY])
        ]

        cmd += ["-verified"]
        if "no_mw" in self.params:
            cmd += ["-no_mw"]

        if "negate" in self.params:
            cmd += ["-negate"]

        if "no_trigger" in self.params:
            cmd += ["-no_trigger"]

        if "unfold_let" in self.params:
            val = self.params["unfold_let"]
            cmd += ["-unfold_let"]
            if val == "full":
                cmd += ["full"]
            elif val == "smart":
                cmd += ["smart"]
            else:
                cmd += ["no"]

        if "nonewlastts" in self.params:
            cmd += ["-nonewlastts"]

        if "no_rw" in self.params:
            cmd += ["-no_rw"]
        return cmd, None

    def post_processing_offline(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        cmd = ["-sig", str(self.params[SIGNATURE_KEY]), "-formula", str(self.params[POLICY_KEY]), "-check"]
        logs, code = self.image.run_offline(self.params["folder"], cmd, measure=False)
        variable_order = VariableOrder(parse_variable_order_monpoly(logs)) if code == 0 else DefaultVariableOrder()
        return parse_monpoly_output(Verdicts(variable_order=variable_order), stdout_input)

    @staticmethod
    def supported_policy_formats() -> List[InputOutputPolicyFormats]:
        return [InputOutputPolicyFormats.MFOTL, InputOutputPolicyFormats.NEGATED_MFOTL]

    @staticmethod
    def supported_trace_formats() -> List[InputOutputTraceFormats]:
        return [InputOutputTraceFormats.MONPOLY, InputOutputTraceFormats.MONPOLY_LINEAR]

    def construct_online_command(self) -> Tuple[List[str], Optional[str]]:
        cmd = [
            "-sig", "additional/signature.sig",
            "-formula", "additional/policy.policy",
            "-verified"
        ]

        if "negate" in self.params: cmd += ["-negate"]
        if "no_trigger" in self.params: cmd += ["-no_trigger"]

        if "unfold_let" in self.params:
            val = self.params["unfold_let"]
            cmd += ["-unfold_let"]
            if val == "full":
                cmd += ["full"]
            elif val == "smart":
                cmd += ["smart"]
            else:
                cmd += ["no"]

        if "nonewlastts" in self.params: cmd += ["-nonewlastts"]
        if "no_rw" in self.params: cmd += ["-no_rw"]
        cmd += ["-verbose", "-nofilteremptytp", "-nofilterrel"]
        return cmd, None

    @staticmethod
    def latency_marker() -> Optional[str]:
        pass

    def post_processing_online(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        pass
