import time
from abc import ABC, abstractmethod
from typing import Dict, AnyStr, Any, Tuple, List, Optional

from Infrastructure.AutoConversion.AutoPolicyConverter import AutoPolicyConverter
from Infrastructure.AutoConversion.AutoTraceConverter import AutoTraceConverter
from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.Builders.ToolBuilder.ToolImageManager import AbstractToolImageManager
from Infrastructure.CLI.cli_args import CLIArgs
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.Monitors.MonitorExceptions import ToolException, ResultErrorException, TimedOut
from Infrastructure.Oracles.AbstractOracleTemplate import AbstractOracleTemplate
from Infrastructure.constants import SIGNATURE_KEY, FOLDER_KEY, TRACE_KEY, POLICY_KEY
from Infrastructure.printing import print_headline, print_footline


class AbstractMonitorTemplate(ABC):
    def __init__(self, image: AbstractToolImageManager, name, params: Dict[AnyStr, Any]):
        self.image = image
        self.params = params
        self.name = name

    def preprocessing(
            self, path_to_folder: str, trace_source_format: InputOutputTraceFormats,
            policy_source_format: InputOutputPolicyFormats, data_file: str, signature_file: str, policy_file: str,
            path_manager: PathManager, verbose=False
    ) -> float:
        path_manager.add_path("trace_input_path", f"{path_to_folder}")
        path_manager.add_path("intermediate_working_space", f"{path_to_folder}/scratch")
        path_manager.add_path("trace_output_path", f"{path_to_folder}/scratch")

        trace_target_format, trace_conversion_distance = find_trace_path(self, path_manager, trace_source_format)
        policy_target_format, policy_conversion_distance = find_policy_path(self, path_manager, policy_source_format)

        trace_auto_convertible = True if trace_target_format is not None else False
        policy_auto_convertible = True if policy_target_format is not None else False

        start = time.perf_counter()
        if trace_auto_convertible:
            if verbose:
                print("Automatic Trace conversion from {} to {}".format(trace_source_format, trace_target_format))

            if trace_conversion_distance == 0:
                self.params[TRACE_KEY] = data_file
            else:
                self.params[TRACE_KEY] = AutoTraceConverter(path_manager, trace_source_format, trace_target_format).convert(
                    input_file=data_file, output_file=data_file, params=self.params
                )
        else:
            if verbose:
                print("Costume Trace preprocessing for format {}".format(trace_source_format))
            self.preprocessing_data(path_to_folder, data_file, trace_source_format, path_manager)

        if policy_auto_convertible:
            if verbose:
                print("Policy conversion from {} to {}".format(policy_source_format, policy_target_format))
            self.params[SIGNATURE_KEY] = signature_file
            self.params[FOLDER_KEY] = path_to_folder

            if policy_conversion_distance == 0:
                self.params[POLICY_KEY] = policy_file
            else:
                self.params[POLICY_KEY] = AutoPolicyConverter(path_manager, policy_source_format, policy_target_format).convert(
                    input_file=policy_file, output_file=policy_file, params=self.params
                )
        else:
            if verbose:
                print("Costume Policy preprocessing for format {}".format(policy_source_format))
            self.preprocessing_policy(path_to_folder, policy_file, signature_file, policy_source_format, path_manager)
        end = time.perf_counter()
        return end - start

    @abstractmethod
    def preprocessing_data(
            self, path_to_folder: AnyStr, data_file: AnyStr,
            trace_source: InputOutputTraceFormats, path_manager: PathManager
    ):
        pass

    @abstractmethod
    def preprocessing_policy(
            self, path_to_folder: AnyStr, policy_file: AnyStr, signature_file: AnyStr,
            policy_source: InputOutputPolicyFormats, path_manager: PathManager
    ):
        pass

    """
        compile the monitor
    """
    def compile(self):
        # build tool that requires compilation
        pass

    """
        construct the command to run the monitor on an offline trace
    """
    @abstractmethod
    def construct_offline_command(self) -> Tuple[List[str], Optional[str]]:
        pass

    """
        preprocess the output format for double checking
    """
    @abstractmethod
    def post_processing(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        pass

    @staticmethod
    @abstractmethod
    def supported_policy_formats() -> List[InputOutputPolicyFormats]:
        pass

    @staticmethod
    @abstractmethod
    def supported_trace_formats() -> List[InputOutputTraceFormats]:
        pass


def run_monitor(mon: AbstractMonitorTemplate, timeout_value, path_to_folder: AnyStr, data_file: AnyStr, signature_file: AnyStr, policy_file: AnyStr,
                path_manager: PathManager, trace_source_format: InputOutputTraceFormats, policy_source_format: InputOutputPolicyFormats,
                result_file, cli_args: CLIArgs, oracle: Optional[AbstractOracleTemplate] = None) -> Tuple[float, float, float, float]:
    print_headline(f"Run {mon.name}")

    preprocessing_elapsed = mon.preprocessing(
        path_to_folder, trace_source_format, policy_source_format,
        data_file, signature_file, policy_file, path_manager, verbose=cli_args.verbose
    )

    start_compile = time.perf_counter()
    mon.compile()
    end_compile = time.perf_counter()
    compile_elapsed = end_compile - start_compile

    start = time.perf_counter()
    cmd, name = mon.construct_offline_command()
    out, code = mon.image.run(parameters=cmd, path_to_data=path_to_folder, time_on=None, time_out=timeout_value, name=name)
    end = time.perf_counter()
    run_offline_elapsed = end - start

    if code != 0:
        if code == 124:
            raise TimedOut(f"Timed out: {mon.name}")
        else:
            raise ToolException(out)

    start = time.perf_counter()
    res = mon.post_processing(out)
    end = time.perf_counter()
    postprocessing_elapsed = end - start

    print(f"Prep:        {preprocessing_elapsed}\nCompilation: {compile_elapsed}\nRuntime:     {run_offline_elapsed}\nPost:        {postprocessing_elapsed}")

    if oracle is not None:
        try:
            verified, msg = oracle.verify(path_to_folder, data_file, res, signature_file, f"scratch/{policy_file}", result_file)
        except Exception as e:
            print(f"Oracle verification failed with exception: {e}")
            raise ResultErrorException((preprocessing_elapsed, compile_elapsed, run_offline_elapsed, postprocessing_elapsed), str(e))
        print_headline(f"Verified: {verified}")
        if not verified:
            raise ResultErrorException((preprocessing_elapsed, compile_elapsed, run_offline_elapsed, postprocessing_elapsed), msg)

    print_footline()
    return preprocessing_elapsed, compile_elapsed, run_offline_elapsed, postprocessing_elapsed


def find_trace_path(mon: AbstractMonitorTemplate, path_manager: PathManager, trace_source_format: InputOutputTraceFormats) -> Tuple[Optional[InputOutputTraceFormats], Optional[int]]:
    trace_target_format = None
    conversion_distance = None
    supported_formats = mon.supported_trace_formats()
    if trace_source_format in supported_formats:
        return trace_source_format, 0

    for trace_format in supported_formats:
        res = AutoTraceConverter.reachable(path_manager, trace_source_format, trace_format)
        if res is not None:
            _, target, dist = res
            if conversion_distance is None or dist < conversion_distance:
                trace_target_format = target
                conversion_distance = dist
    return trace_target_format, conversion_distance


def find_policy_path(mon: AbstractMonitorTemplate, path_manager: PathManager, policy_source_format: InputOutputPolicyFormats) -> Tuple[Optional[InputOutputPolicyFormats], Optional[int]]:
    policy_target_format = None
    conversion_distance = None
    supported_formats = mon.supported_policy_formats()
    if policy_source_format in supported_formats:
        return policy_source_format, 0

    for policy_format in supported_formats:
        res = AutoPolicyConverter.reachable(path_manager, policy_source_format, policy_format)
        if res is not None:
            _, target, dist = res
            if conversion_distance is None or dist < conversion_distance:
                policy_target_format = target
                conversion_distance = dist
    return policy_target_format, conversion_distance
