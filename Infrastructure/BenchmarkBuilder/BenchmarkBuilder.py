import dataclasses
import os.path
from abc import ABC, abstractmethod
from dataclasses import asdict
from typing import AnyStr, Any, List

import pandas
import pandas as pd

from Infrastructure.BenchmarkBuilder.BenchmarkBuilderException import BenchmarkCreationFailed
from Infrastructure.Builders.ProcessorBuilder.CaseStudiesGenerators.CaseStudyGenerator import \
    CaseStudyGenerator
from Infrastructure.Builders.ProcessorBuilder.DataGenerators.SignatureGenerator.SignatureGenerator import SignatureGenerator
from Infrastructure.Builders.ProcessorBuilder.DataGenerators.DataGolfGenerator.DataGolfGenerator import DataGolfGenerator
from Infrastructure.Builders.ProcessorBuilder.PolicyGenerators.MfotlPolicyGenerator.MfotlPolicyGenerator import \
    MfotlPolicyGenerator
from Infrastructure.Builders.ProcessorBuilder.PolicyGenerators.PatternPolicyGenerator.PatternPolicyGenerator import PatternPolicyGenerator
from Infrastructure.DataTypes.Contracts.BenchmarkContract import CaseStudyBenchmarkContract, PolicyGenerators, \
    DataGenerators
from Infrastructure.DataTypes.Contracts.SubContracts.CaseStudyContract import construct_case_study
from Infrastructure.DataTypes.Contracts.SubContracts.SyntheticContract import SyntheticExperiment, \
    construct_synthetic_experiment_sig, construct_synthetic_experiment_pattern, TimeGuarded
from Infrastructure.DataTypes.FileRepresenters.ScratchFolderHandler import ScratchFolderHandler
from Infrastructure.DataTypes.FileRepresenters.StatsHandler import StatsHandler
from Infrastructure.DataTypes.Types.custome_type import ExperimentType

from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate, run_monitor
from Infrastructure.Monitors.MonitorExceptions import TimedOut, ToolException, ResultErrorException


class BenchmarkBuilderTemplate(ABC):
    @abstractmethod
    def _build(self):
        pass

    @abstractmethod
    def run(self, tools: list[AbstractMonitorTemplate],
            parameters: dict[AnyStr, dict[AnyStr, Any]]) -> pandas.DataFrame:
        pass


@dataclasses.dataclass
class TimeGuard:
    lower_time: int
    upper_time: int
    time_guard: AnyStr


def init_policy_generator(name: PolicyGenerators, path_to_build_inner):
    if name == PolicyGenerators.MFOTLGENERATOR:
        return MfotlPolicyGenerator("gen_mfotl", path_to_build_inner)
    elif name == PolicyGenerators.PATTERNS:
        return PatternPolicyGenerator()
    else:
        print("Not implemented yet")


def init_data_generator(tag: DataGenerators, path_to_build_inner):
    if tag == DataGenerators.DATAGOLF:
        return DataGolfGenerator("datagolf", path_to_build_inner)
    elif tag == DataGenerators.DATAGENERATOR:
        return SignatureGenerator("gen_data", path_to_build_inner)
    else:
        print("Not implemented yet")


class BenchmarkBuilder(BenchmarkBuilderTemplate, ABC):
    def __init__(self, contract, path_to_build, path_to_experiment, data_setup,
                 gen_mode: ExperimentType, time_guard: TimeGuarded, tools_to_build, oracle=None):
        print("\n" + "=" * 20 + " Benchmark Init " + "=" * 20)
        self.contract = contract

        self.path_to_build = path_to_build
        self.path_to_experiment = path_to_experiment
        self.path_to_named_experiment = self.path_to_experiment + "/" + self.contract.experiment_name

        self.data_setup = data_setup if isinstance(data_setup, dict) else asdict(data_setup)

        if isinstance(contract, CaseStudyBenchmarkContract):
            self.data_gen = CaseStudyGenerator(contract.case_study_name, path_to_build)
            self.data_setup["path"] = f"{self.path_to_named_experiment}/{contract.experiment_name}"
        else:
            self.data_gen = init_data_generator(contract.data_source, path_to_build)
            self.formula_gen = init_policy_generator(contract.policy_source, path_to_build)
            self.experiment = contract.experiment

        self.oracle = oracle[0].get_oracle(oracle[1]) if oracle else None
        self.gen_mode = gen_mode

        self.time_guard = time_guard
        self.time_out = self.time_guard.upper_bound
        self.tools_to_build = tools_to_build

        print("=" * 20 + " Benchmark Init (done) " + "=" * 20)
        self._build()

    def _build(self):
        print("\n" + "=" * 20 + " Benchmark Build " + "=" * 20)
        if not os.path.exists(self.path_to_experiment):
            os.mkdir(self.path_to_experiment)

        if not os.path.exists(self.path_to_named_experiment):
            os.mkdir(self.path_to_named_experiment)
        try:
            if self.gen_mode == ExperimentType.Signature:
                construct_synthetic_experiment_sig(self.experiment, self.path_to_named_experiment,
                                                   self.data_setup, self.data_gen,
                                                   self.contract.policy_setup, self.formula_gen,
                                                   self.oracle, self.time_guard)
            elif self.gen_mode == ExperimentType.Pattern:
                construct_synthetic_experiment_pattern(self.experiment, self.path_to_named_experiment,
                                                       self.data_setup, self.data_gen, self.oracle, self.time_guard)
            elif self.gen_mode == ExperimentType.CaseStudy:
                construct_case_study(self.data_gen, self.data_setup, self.path_to_named_experiment, self.oracle, self.time_out)
            else:
                print("Not implemented")
            print("\n" + "=" * 20 + " Benchmark Build (done) " + "=" * 20)
        except (BaseException, FileNotFoundError):
            raise BenchmarkCreationFailed()

    def run(self, tools: List[AbstractMonitorTemplate],
            parameters: dict[AnyStr, dict[AnyStr, Any]]) -> pandas.DataFrame:
        print("====== Run Experiments ======")
        settings_result = pd.DataFrame(columns=["Name", "Setting", "pre", "runtime", "post", "wall time", "max mem", "cpu"])

        if self.gen_mode == ExperimentType.CaseStudy:
            path_to_folder = f"{self.path_to_named_experiment}/data"
            sfh = ScratchFolderHandler(path_to_folder)
            for (num, (data, formula, sig)) in self.data_setup["case_study_mapper"].iterate_settings():
                for tool in tools:
                    run_tools(
                        settings_result=settings_result, tool=tool, time_guard=self.time_guard,
                        oracle=self.oracle, path_to_folder=path_to_folder,
                        data_file=data, signature_file=sig, formula_file=formula
                    )
                sfh.clean_up_folder()
            sfh.remove_folder()
            return settings_result

        paths = []
        if self.gen_mode == ExperimentType.Pattern:
            for num_ops in self.experiment.num_operators:
                for num_set in self.experiment.num_setting:
                    paths.append(f"{self.path_to_named_experiment}/operators_{num_ops}/num_{num_set}")
        elif self.gen_mode == ExperimentType.Signature:
            for num_ops in self.experiment.num_operators:
                for num_fv in self.experiment.num_fvs:
                    for num_set in self.experiment.num_setting:
                        paths.append((f"{self.path_to_named_experiment}/operators_{num_ops}"
                                      + f"/free_vars_{num_fv}/num_{num_set}"))

        signature_file = f"signature.sig"
        formula_file = f"formula.mfotl"

        for path_to_folder in paths:
            sfh = ScratchFolderHandler(path_to_folder)
            for num_len in self.experiment.num_data_set_sizes:
                data_file = f"data_{num_len}.csv"
                for tool in tools:
                    run_tools(
                        settings_result=settings_result, tool=tool, time_guard=self.time_guard,
                        oracle=self.oracle, path_to_folder=path_to_folder,
                        data_file=data_file, signature_file=signature_file, formula_file=formula_file
                    )

                    sfh.clean_up_folder()
            sfh.remove_folder()
        return settings_result


def run_tools(settings_result, tool, time_guard, oracle, path_to_folder, data_file, signature_file, formula_file):
    try:
        prep, runtime, prop = run_monitor(
            tool, time_guard, path_to_folder, data_file,
            signature_file, formula_file, oracle
        )

        stats = StatsHandler(path_to_folder).get_stats()
        if stats is not None:
            wall_time, max_mem, cpu = stats
        else:
            wall_time, max_mem, cpu = None, None, None

        settings_result.loc[len(settings_result)] = [
            tool.name, "", prep, runtime, prop,
            wall_time, max_mem, cpu
        ]
        return settings_result
    except TimedOut as e:
        print(f"Monitor {tool.name} timed out: {e}")        
    except ToolException as e:
        print(f"ToolException for monitor {tool.name}: {e}")
    except ResultErrorException as e:
        print(f"ResultErrorException for monitor {tool.name}: {e}")