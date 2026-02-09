import time
from abc import ABC, abstractmethod
from typing import Dict, AnyStr, Any, Tuple, List, Optional

from Infrastructure.AutoConversion.AutoPolicyConverter import AutoPolicyConverter
from Infrastructure.AutoConversion.AutoTraceConverter import AutoTraceConverter
from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.Builders.ToolBuilder.ToolImageManager import AbstractToolImageManager
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.Monitors.MonitorExceptions import ToolException, ResultErrorException, TimedOut
from Infrastructure.printing import print_headline, print_footline


class AbstractMonitorTemplate(ABC):
    def __init__(self, image: AbstractToolImageManager, name, params: Dict[AnyStr, Any]):
        self.image = image
        self.params = params
        self.name = name

    """
        compile the monitor
    """
    def compile(self):
        # build tool that requires compilation
        pass

    """
        transform csv into the tool format, e.g. sorted
        @param path_to_data:      path to the initial data in the standard csv format 
        @param path_to_signature: path to the signature 
        @param path_to_formula:   path to the formula 
    """
    @abstractmethod
    def pre_processing(
            self, path_to_folder: AnyStr, data_file: AnyStr, signature_file: AnyStr, formula_file: AnyStr,
            trace_source: InputOutputTraceFormats, policy_source: InputOutputPolicyFormats, path_manager: PathManager
    ):
        pass

    """
        construct the command to run the monitor on an offline trace
    """
    @abstractmethod
    def run_offline_command(self) -> Tuple[List[str], Optional[str]]:
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


def run_monitor(mon: AbstractMonitorTemplate, guarded,
                path_to_folder: AnyStr, data_file: AnyStr,
                signature_file: AnyStr, formula_file: AnyStr,
                path_manager: PathManager, trace_source_format: InputOutputTraceFormats, policy_source_format: InputOutputPolicyFormats,
                oracle=None, case_study_mapper=None) -> Tuple[float, float, float, float]:
    print_headline(f"Run {mon.name}")
    path_manager.add_path("trace_input_path", f"{path_to_folder}")
    path_manager.add_path("intermediate_working_space", f"{path_to_folder}/scratch")
    path_manager.add_path("trace_output_path", f"{path_to_folder}/scratch")

    trace_target_format = None
    conversion_distance = None
    for trace_format in mon.supported_trace_formats():
        res = AutoTraceConverter.reachable(path_manager, trace_source_format, trace_format)
        if res is not None:
            _, target, dist = res
            if conversion_distance is None or dist < conversion_distance:
                trace_target_format = target
                conversion_distance = dist

    policy_target_format = None
    conversion_distance = None
    for policy_format in mon.supported_policy_formats():
        res = AutoPolicyConverter.reachable(path_manager, policy_source_format, policy_format)
        if res is not None:
            _, target, dist = res
            if conversion_distance is None or dist < conversion_distance:
                policy_target_format = target
                conversion_distance = dist

    trace_auto_convertible = True if trace_target_format is not None else False
    policy_auto_convertible = True if policy_target_format is not None else False

    start = time.perf_counter()
    if trace_auto_convertible and policy_auto_convertible:
        print("Auto conversion")
        mon.params["signature"] = signature_file
        mon.params["folder"] = path_to_folder

        mon.params["data"] = AutoTraceConverter(path_manager, trace_source_format, trace_target_format).convert(
            input_file=data_file, output_file=data_file, params=mon.params
        )
        mon.params["formula"] = AutoPolicyConverter(path_manager, policy_source_format, policy_target_format).convert(
            input_file=formula_file, output_file=formula_file, params=mon.params
        )
    else:
        mon.pre_processing(
            path_to_folder, data_file, signature_file, formula_file, trace_source_format, policy_source_format, path_manager
        )
    end = time.perf_counter()
    preprocessing_elapsed = end - start

    start_compile = time.perf_counter()
    mon.compile()
    end_compile = time.perf_counter()
    compile_elapsed = end_compile - start_compile

    start = time.perf_counter()
    timeout_value = guarded.upper_bound if guarded else None
    cmd, name = mon.run_offline_command()
    out, code = mon.image.run(parameters=cmd, path_to_data=path_to_folder, time_on=None, timeout=timeout_value, name=name)
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
            verified, msg = oracle.verify(path_to_folder, data_file, res, signature_file, formula_file, case_study_mapper=case_study_mapper)
        except Exception as e:
            print(f"Oracle verification failed with exception: {e}")
            raise ResultErrorException((preprocessing_elapsed, compile_elapsed, run_offline_elapsed, postprocessing_elapsed), str(e))
        print_headline(f"Verified: {verified}")
        if not verified:
            raise ResultErrorException((preprocessing_elapsed, compile_elapsed, run_offline_elapsed, postprocessing_elapsed), msg)

    print_footline()
    return preprocessing_elapsed, compile_elapsed, run_offline_elapsed, postprocessing_elapsed
