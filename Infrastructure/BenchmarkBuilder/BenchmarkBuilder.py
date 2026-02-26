import os.path
from enum import Enum
from typing import AnyStr, List, Optional

from Infrastructure.Analysis.ResultAggregator import ResultAggregator
from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.BenchmarkBuilder.BenchmarkBuilderException import BenchmarkCreationFailed
from Infrastructure.BenchmarkBuilder.Coordinator.Coordinator import Coordinator
from Infrastructure.CLI.cli_args import CLIArgs
from Infrastructure.DataTypes.FileRepresenters.FingerPrintHandler import FingerPrintHandler
from Infrastructure.DataTypes.FileRepresenters.ScratchFolderHandler import ScratchFolderHandler
from Infrastructure.DataTypes.FileRepresenters.StatsHandler import StatsHandler

from Infrastructure.Monitors.AbstractMonitorTemplate import run_monitor
from Infrastructure.Monitors.MonitorExceptions import TimedOut, ToolException, ResultErrorException
from Infrastructure.Monitors.MonitorManager import InvalidReturnType, GetMonitorsReturnType, ValidReturnType
from Infrastructure.constants import LENGTH
from Infrastructure.printing import print_headline, print_footline, normal_line


class RunToolResult(Enum):
    OK = 1
    TIMEOUT = 2
    TOOL_ERROR = 3
    VALIDATION_ERROR = 4


class BenchmarkBuilder:
    def __init__(self, experiment_name, coordinator: Coordinator, tools_to_build, repeat_runs, cli_args: CLIArgs):
        print_headline("(Starting) Init Benchmark")
        self.coordinator = coordinator

        self.experiment_name = experiment_name
        self.cli_args = cli_args
        self.repeat_runs = repeat_runs
        self.tools_to_build = tools_to_build

        path_to_project = self.coordinator.get_path("path_to_project")
        path_to_infrastructure = path_to_project + "/Infrastructure"
        self.coordinator.add_path("path_to_infrastructure", path_to_infrastructure)
        named_experiment_path = path_to_infrastructure + "/experiments/" + experiment_name
        self.coordinator.add_path("path_to_experiment", f"{path_to_infrastructure}/experiments")
        self.coordinator.add_path("path_to_named_experiment", named_experiment_path)
        self.coordinator.add_path("path_to_debug", named_experiment_path + "/debug")

        os.makedirs(self.coordinator.get_path("path_to_experiment"), exist_ok=True)
        os.makedirs(self.coordinator.get_path("path_to_named_experiment"), exist_ok=True)

        fingerprint_location = self.coordinator.get_path("path_to_named_experiment") + "/fingerprint"
        finger_print = self.coordinator.finger_print()

        print_footline("(Finished) Init Benchmark")
        if os.path.exists(fingerprint_location):
            fph = FingerPrintHandler.from_file(fingerprint_location)
            if not FingerPrintHandler.compare(fph, finger_print):
                self._build()
        else:
            self._build()
            FingerPrintHandler(finger_print).to_file(fingerprint_location)

    def _build(self):
        print_headline("(Starting) building Benchmark")
        try:
            self.coordinator.build()
            print_footline("(Finished) building Benchmark")
        except Exception as e:
            raise BenchmarkCreationFailed(e)

    def run(self, tools: List[GetMonitorsReturnType]) -> ResultAggregator:
        print("\n" + "-" * LENGTH)
        normal_line("Run Experiments")
        print("-" * LENGTH)
        result_aggregator = ResultAggregator()

        path_to_debug = self.coordinator.get_path("path_to_debug")
        if os.path.exists(path_to_debug):
            ScratchFolderHandler(path_to_debug).remove_folder()

        for (index, path_to_folder, data_file, data_type, policy_file, policy_type, signature, result) in self.coordinator.iterate_settings():
            sfh = ScratchFolderHandler(path_to_folder)

            data_file_name = str(path_to_folder.removeprefix(path_to_folder))
            policy_file_name = str(path_to_folder.removeprefix(path_to_folder))

            tmp_setting = f"index_{index}_{data_file_name}_{policy_file_name}"
            for i in range(0, self.repeat_runs):
                tmp_setting_id = f"{tmp_setting}_{i}"
                for tool in tools:
                    if isinstance(tool, InvalidReturnType):
                        print_headline(f"Missing {tool.name}")
                        result_aggregator.add_missing(tool.name, tmp_setting_id)
                        print_footline()
                    elif isinstance(tool, ValidReturnType):
                        """if tool.tool.name in time_out_dict and self.short_cut:
                            print_headline(f"Short cutting {tool.tool.name}")
                            result_aggregator.add_timeout(tool.tool.name, tmp_setting_id, self.time_guard.upper_bound)
                            print_footline()
                        else:
                            res = run_tools(
                                result_aggregator=result_aggregator, tool=tool.tool, time_guard=self.time_guard,
                                oracle=self.oracle, path_to_folder=path_to_folder, setting_id=tmp_setting_id,
                                data_file=data_file, signature_file=signature_file, formula_file=formula_file,
                                sfh=sfh, cli_args=self.cli_args, path_manager=self.path_manager
                            )
                            if res == RunToolResult.TIMEOUT:
                                time_out_dict.add(tool.tool.name)"""
                        # todo short cutting must be done by the coordinator
                        res = run_tools(
                            result_aggregator=result_aggregator, path_to_folder=path_to_folder, tool=tool.tool,
                            result_file=result, setting_id=tmp_setting_id,
                            data_file=data_file, signature_file=signature, policy_file=policy_file,
                            sfh=sfh, cli_args=self.cli_args,
                            coordinator=self.coordinator, policy_type=policy_type, data_type=data_type
                        )
                    else:
                        raise NotImplemented(f"Not implemented for object {tool}")

            sfh.remove_folder()
        return result_aggregator

    def seed_retriever(self):
        operator_prefix = "operators_"
        free_vars_prefix = "free_vars_"
        num_prefix = "num_"

        def _read_file(path_) -> int:
            with open(path_, "r") as f:
                return int(f.read())

        def _apply_decoders(string: AnyStr) -> Optional[int]:
            if string.startswith(operator_prefix):
                return int(string.removeprefix(operator_prefix))
            elif string.startswith(free_vars_prefix):
                return int(string.removeprefix(free_vars_prefix))
            elif string.startswith(num_prefix):
                return int(string.removeprefix(num_prefix))
            else:
                return None

        seed_dict = dict()
        path_to_named_experiment = self.path_manager.get_path("path_to_named_experiment")
        for (_, path_to_data, _, _, _, _, _, _) in self.coordinator.iterate_settings():
            gen_seed_path = f"{path_to_data}/Seeds/generator.seed"
            policy_seed_path = f"{path_to_data}/Seeds/policy.seed"
            gen_seed = _read_file(gen_seed_path) if os.path.exists(gen_seed_path) else None
            policy_seed = _read_file(policy_seed_path) if os.path.exists(policy_seed_path) else None

            if gen_seed is None and policy_seed is None:
                continue

            clean_path = path_to_data.removeprefix(path_to_named_experiment)
            clean_list = list(filter(None, clean_path.split("/")))
            setting_raw = list(filter(lambda x: x is not None, map(lambda x: _apply_decoders(x), clean_list)))
            setting_key = str(setting_raw)
            seed_dict[setting_key] = (gen_seed, policy_seed)


def run_tools(
        result_aggregator: ResultAggregator, tool, setting_id: str, path_to_folder: str,
        data_file: str, data_type: InputOutputTraceFormats, policy_file: str, policy_type: InputOutputPolicyFormats,
        signature_file: str, result_file: str, cli_args: CLIArgs, coordinator: Coordinator, sfh=None
) -> RunToolResult:
    debug_path = coordinator.get_path("path_to_debug")
    timeout_value = coordinator.time_out()
    try:
        prep, compiled, runtime, prop = run_monitor(
            mon=tool, path_to_folder=path_to_folder, data_file=data_file, signature_file=signature_file,
            policy_file=policy_file, cli_args=cli_args, trace_source_format=data_type, policy_source_format=policy_type,
            result_file=result_file, timeout_value=timeout_value,
            oracle=coordinator.get_oracle(), path_manager=coordinator.get_path_manager()
        )

        if cli_args.debug and sfh is not None:
            sfh.copy_to_debug(debug_path, setting_id, tool.name)

        stats = StatsHandler(path_to_folder).get_stats()
        if stats is not None:
            wall_time, max_mem, cpu = stats
        else:
            if cli_args.measure:
                wall_time, max_mem, cpu = "", "", ""
            else:
                wall_time, max_mem, cpu = None, None, None

        result_aggregator.add_valid(
            tool.name, setting_id, prep, compiled, runtime, prop, wall_time, max_mem, cpu
        )
        return RunToolResult.OK
    except TimedOut as e:
        print(f"Monitor {tool.name} timed out: {e}")
        if cli_args.debug and sfh is not None:
            sfh.copy_to_debug(debug_path, setting_id, tool.name)
        result_aggregator.add_timeout(tool.name, setting_id, timeout_value)
        return RunToolResult.TIMEOUT
    except ToolException as e:
        print(f"ToolException for monitor {tool.name}: {e}")
        if cli_args.debug and sfh is not None:
            sfh.copy_to_debug(debug_path, setting_id, tool.name)
        result_aggregator.add_tool_error(tool.name, setting_id, str(e))
        return RunToolResult.TOOL_ERROR
    except ResultErrorException as e:
        print(f"ResultErrorException for monitor {tool.name}: {e.args[1]}")
        if cli_args.debug and sfh is not None:
            sfh.copy_to_debug(debug_path, setting_id, tool.name)
        stats = StatsHandler(path_to_folder).get_stats()
        if stats is not None:
            wall_time, max_mem, cpu = stats
        else:
            if cli_args.measure:
                wall_time, max_mem, cpu = "", "", ""
            else:
                wall_time, max_mem, cpu = None, None, None
        (prep, compiled, runtime, prop) = e.args[0]
        result_aggregator.add_result_error(
            tool.name, setting_id, prep, compiled, runtime, prop,
            wall_time, max_mem, cpu, str(e.args[1])
        )
        return RunToolResult.VALIDATION_ERROR
    except Exception as e:
        if cli_args.debug and sfh is not None:
            sfh.copy_to_debug(debug_path, setting_id, tool.name)
        result_aggregator.add_tool_error(tool.name, setting_id, str(e))
        return RunToolResult.TOOL_ERROR
