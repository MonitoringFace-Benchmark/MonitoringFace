import dataclasses
import os.path
import sys
from abc import ABC, abstractmethod
from dataclasses import asdict
from typing import AnyStr, Any, List, Optional

import pandas

from Infrastructure.Analysis.ResultAggregator import ResultAggregator
from Infrastructure.BenchmarkBuilder.BenchmarkBuilderException import BenchmarkCreationFailed
from Infrastructure.Builders.ProcessorBuilder.CaseStudiesGenerators.CaseStudyGenerator import CaseStudyGenerator
from Infrastructure.DataTypes.Contracts.BenchmarkContract import CaseStudyBenchmarkContract
from Infrastructure.DataTypes.Contracts.SubContracts.CaseStudyContract import construct_case_study, CaseStudyMapper
from Infrastructure.DataTypes.Contracts.SubContracts.SyntheticContract import construct_synthetic_experiment_sig, construct_synthetic_experiment_pattern, TimeGuarded
from Infrastructure.DataTypes.FileRepresenters.FingerPrintHandler import FingerPrintHandler
from Infrastructure.DataTypes.FileRepresenters.ScratchFolderHandler import ScratchFolderHandler
from Infrastructure.DataTypes.FileRepresenters.StatsHandler import StatsHandler
from Infrastructure.DataTypes.FingerPrint.FingerPrint import data_class_to_finger_print
from Infrastructure.DataTypes.Types.custome_type import ExperimentType

from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate, run_monitor
from Infrastructure.Monitors.MonitorExceptions import TimedOut, ToolException, ResultErrorException
from Infrastructure.Monitors.MonitorManager import InvalidReturnType, GetMonitorsReturnType, ValidReturnType
from Infrastructure.constants import FINGERPRINT_DATA, FINGERPRINT_EXPERIMENT, LENGTH
from Infrastructure.printing import print_headline, print_footline, normal_line


class BenchmarkBuilderTemplate(ABC):
    @abstractmethod
    def _build(self):
        pass

    @abstractmethod
    def run(self, tools: list[AbstractMonitorTemplate], parameters: dict[AnyStr, dict[AnyStr, Any]]) -> pandas.DataFrame:
        pass


@dataclasses.dataclass
class TimeGuard:
    lower_time: int
    upper_time: int
    time_guard: str


class BenchmarkBuilder(BenchmarkBuilderTemplate):
    def __init__(
            self, contract, path_to_project, data_setup,
            gen_mode: ExperimentType, time_guard: TimeGuarded,
            tools_to_build, repeat_runs, oracle=None, seeds=None, debug_mode=False
    ):
        print_headline("(Starting) Init Benchmark")
        self.contract = contract
        self.seeds = seeds
        self.debug_mode = debug_mode
        self.repeat_runs = repeat_runs

        self.path_to_build = path_to_project + "/Infrastructure/build"
        self.path_to_experiment = path_to_project + "/Infrastructure/experiments"
        self.path_to_named_experiment = self.path_to_experiment + "/" + self.contract.experiment_name
        self.path_to_debug = self.path_to_named_experiment + "/debug"

        # Initialize oracle to None by default
        self.oracle = None
        self.oracle_name = None
        if oracle:
            self.oracle_name = oracle[1]
            self.oracle = oracle[0].get_oracle(self.oracle_name)
        self.gen_mode = gen_mode

        self.time_guard = time_guard
        self.time_out = self.time_guard.upper_bound if self.time_guard else None
        self.tools_to_build = tools_to_build

        os.makedirs(self.path_to_experiment, exist_ok=True)
        os.makedirs(self.path_to_named_experiment, exist_ok=True)

        data_setup = data_setup if data_setup else {}
        self.data_setup = data_setup if isinstance(data_setup, dict) else asdict(data_setup)
        fingerprint_location = self.path_to_named_experiment + "/fingerprint"
        new_experiment_fingerprint = data_class_to_finger_print(contract)
        if isinstance(contract, CaseStudyBenchmarkContract):
            self.data_gen = CaseStudyGenerator(contract.case_study_name, path_to_project)
            self.data_setup["path"] = f"{self.path_to_named_experiment}/{contract.experiment_name}"
            print_footline("(Finished) Init Benchmark")
            if os.path.exists(fingerprint_location):
                fph = FingerPrintHandler.from_file(fingerprint_location)
                old_experiment_fingerprint = fph.get_attr(FINGERPRINT_EXPERIMENT)
                if not new_experiment_fingerprint == old_experiment_fingerprint:
                    self._build()
                else:
                    self.data_setup["case_study_mapper"] = CaseStudyMapper(
                        path_to_data=f"{self.path_to_named_experiment}/data",
                        path_to_instructions=f"{self.path_to_named_experiment}/instructions.txt"
                    )
            else:
                self._build()
                fph = FingerPrintHandler({FINGERPRINT_EXPERIMENT: new_experiment_fingerprint})
                fph.to_file(fingerprint_location)
        else:
            self.data_gen = contract.data_source
            self.policy_gen = contract.policy_source
            self.policy_setup = asdict(contract.policy_setup)
            self.experiment = contract.experiment
            print_footline("(Finished) Init Benchmark")
            if os.path.exists(fingerprint_location):
                fph = FingerPrintHandler.from_file(fingerprint_location)
                old_data_setup_fingerprint = fph.get_attr(FINGERPRINT_DATA)
                old_experiment_fingerprint = fph.get_attr(FINGERPRINT_EXPERIMENT)
                new_data_setup_fingerprint = data_class_to_finger_print(data_setup)
                if not (old_experiment_fingerprint == new_experiment_fingerprint and old_data_setup_fingerprint == new_data_setup_fingerprint):
                    self._build()
                    fph = FingerPrintHandler({FINGERPRINT_DATA: new_data_setup_fingerprint, FINGERPRINT_EXPERIMENT: new_experiment_fingerprint})
                    fph.to_file(fingerprint_location)

            else:
                self._build()
                new_data_setup_fingerprint = data_class_to_finger_print(data_setup)
                fph = FingerPrintHandler({FINGERPRINT_DATA: new_data_setup_fingerprint, FINGERPRINT_EXPERIMENT: new_experiment_fingerprint})
                fph.to_file(fingerprint_location)

    def _build(self):
        print_headline("(Starting) building Benchmark")
        try:
            if self.gen_mode == ExperimentType.Signature:
                print(" ... Build Signature-based Setup")
                construct_synthetic_experiment_sig(
                    self.experiment, self.path_to_named_experiment, self.data_setup, self.data_gen,
                    self.policy_setup, self.policy_gen, self.oracle, self.time_guard, self.seeds
                )
            elif self.gen_mode == ExperimentType.Pattern:
                print(" ... Build Pattern-based Setup")
                construct_synthetic_experiment_pattern(
                    self.experiment, self.path_to_named_experiment,
                    self.data_setup, self.data_gen, self.oracle, self.time_guard, self.seeds
                )
            elif self.gen_mode == ExperimentType.CaseStudy:
                print(" ... Build Case Study Setup")
                construct_case_study(self.data_gen, self.data_setup, self.path_to_named_experiment, self.oracle, self.time_out)
            else:
                raise BenchmarkCreationFailed("Not implemented")
            print_footline("(Finished) building Benchmark")
        except (BaseException, FileNotFoundError):
            raise BenchmarkCreationFailed()

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
        for path in path_generator(self.gen_mode, self.experiment, self.path_to_named_experiment):
            gen_seed = _read_file(f"{path}/Seeds/generator.seed")
            policy_seed = _read_file(f"{path}/Seeds/policy.seed")

            clean_path = path.removeprefix(self.path_to_named_experiment)
            clean_list = list(filter(None, clean_path.split("/")))
            setting_raw = list(filter(lambda x: x is not None, map(lambda x: _apply_decoders(x), clean_list)))
            setting_key = str(setting_raw)
            seed_dict[setting_key] = (gen_seed, policy_seed)
        return seed_dict

    def run(self, tools: List[GetMonitorsReturnType], parameters: dict[AnyStr, dict[AnyStr, Any]]) -> ResultAggregator:
        print("\n" + "-" * LENGTH)
        normal_line("Run Experiments")
        print("-" * LENGTH)
        result_aggregator = ResultAggregator()

        if self.gen_mode == ExperimentType.CaseStudy:
            path_to_folder = f"{self.path_to_named_experiment}/data"
            sfh = ScratchFolderHandler(path_to_folder)
            for (num, (data, formula, sig)) in self.data_setup["case_study_mapper"].iterate_settings():
                setting_id = f"{num} -> Data: {data}, Formula: {formula}, Signature: {sig}"
                for tool in tools:
                    if isinstance(tool, InvalidReturnType):
                        print_headline(f"Missing {tool.name}")
                        result_aggregator.add_missing(tool.name, setting_id)
                        print_footline()
                    elif isinstance(tool, ValidReturnType):
                        run_tools(result_aggregator=result_aggregator, tool=tool.tool, time_guard=self.time_guard,
                                  oracle=self.oracle, path_to_folder=path_to_folder, setting_id=setting_id,
                                  data_file=data, signature_file=sig, formula_file=formula,
                                  sfh=sfh, debug_mode=self.debug_mode, debug_path=self.path_to_debug)
                    else:
                        raise NotImplemented(f"Not implemented for object {tool}")

                sfh.clean_up_folder()
            sfh.remove_folder()
            return result_aggregator

        signature_file = f"signature.sig"
        formula_file = f"formula.mfotl"

        for path_to_folder in path_generator(self.gen_mode, self.experiment, self.path_to_named_experiment):
            sfh = ScratchFolderHandler(path_to_folder)
            for num_len in self.experiment.num_data_set_sizes:
                setting_id = str(path_to_folder.removeprefix(self.path_to_named_experiment)) + f"/{num_len}"
                data_file = f"data_{num_len}.csv"
                for i in range(0, self.repeat_runs):
                    tmp_setting_id = f"{setting_id}_{i}"
                    for tool in tools:
                        if isinstance(tool, InvalidReturnType):
                            print_headline(f"Missing {tool.name}")
                            result_aggregator.add_missing(tool.name, tmp_setting_id)
                            print_footline()
                        elif isinstance(tool, ValidReturnType):
                            run_tools(
                                result_aggregator=result_aggregator, tool=tool.tool, time_guard=self.time_guard,
                                oracle=self.oracle, path_to_folder=path_to_folder, setting_id=tmp_setting_id,
                                data_file=data_file, signature_file=signature_file, formula_file=formula_file,
                                sfh=sfh, debug_mode=self.debug_mode, debug_path=self.path_to_debug
                            )
                        else:
                            raise NotImplemented(f"Not implemented for object {tool}")
                        sfh.clean_up_folder()
            sfh.remove_folder()
        return result_aggregator


def run_tools(result_aggregator, tool, setting_id, time_guard, oracle, path_to_folder, data_file, signature_file, formula_file, sfh=None, debug_mode=False, debug_path=None):
    try:
        prep, runtime, prop = run_monitor(
            tool, time_guard, path_to_folder, data_file,
            signature_file, formula_file, oracle
        )

        if debug_mode and sfh is not None and debug_path is not None:
            sfh.copy_to_debug(debug_path, setting_id, tool.name)

        stats = StatsHandler(path_to_folder).get_stats()
        if stats is not None:
            wall_time, max_mem, cpu = stats
        else:
            wall_time, max_mem, cpu = "", "", ""

        result_aggregator.add_valid(
            tool.name, setting_id, prep, runtime, prop,
            wall_time, max_mem, cpu
        )
    except TimedOut as e:
        print(f"Monitor {tool.name} timed out: {e}")
        if debug_mode and sfh is not None and debug_path is not None:
            sfh.copy_to_debug(debug_path, setting_id, tool.name)
        timeout_value = time_guard.upper_bound if time_guard else None
        result_aggregator.add_timeout(tool.name, setting_id, timeout_value)
    except ToolException as e:
        print(f"ToolException for monitor {tool.name}: {e}")
        if debug_mode and sfh is not None and debug_path is not None:
            sfh.copy_to_debug(debug_path, setting_id, tool.name)
        result_aggregator.add_tool_error(tool.name, setting_id, str(e))
    except ResultErrorException as e:
        print(f"ResultErrorException for monitor {tool.name}: {e.args[1]}")
        if debug_mode and sfh is not None and debug_path is not None:
            sfh.copy_to_debug(debug_path, setting_id, tool.name)
        stats = StatsHandler(path_to_folder).get_stats()
        if stats is not None:
            wall_time, max_mem, cpu = stats
        else:
            wall_time, max_mem, cpu = "", "", ""

        (prep, runtime, prop) = e.args[0]
        result_aggregator.add_result_error(
            tool.name, setting_id, prep, runtime, prop,
            wall_time, max_mem, cpu, str(e.args[1])
        )
    except Exception as e:
        if debug_mode and sfh is not None and debug_path is not None:
            sfh.copy_to_debug(debug_path, setting_id, tool.name)
        result_aggregator.add_tool_error(tool.name, setting_id, str(e))


def path_generator(mode: ExperimentType, experiment, path_to_named_experiment: AnyStr) -> list[AnyStr]:
    paths = []
    if mode == ExperimentType.Pattern:
        for num_ops in experiment.num_operators:
            for num_set in experiment.num_setting:
                paths += [f"{path_to_named_experiment}/operators_{num_ops}/num_{num_set}"]
    elif mode == ExperimentType.Signature:
        for num_ops in experiment.num_operators:
            for num_fv in experiment.num_fvs:
                for num_set in experiment.num_setting:
                    paths += [f"{path_to_named_experiment}/operators_{num_ops}/free_vars_{num_fv}/num_{num_set}"]
    return paths
