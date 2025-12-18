import dataclasses
import os.path
from abc import ABC, abstractmethod
from dataclasses import asdict
from enum import Enum
from typing import AnyStr, Any, List, Optional

import pandas
import pandas as pd

from Infrastructure.Analysis.Formatting import parse_wall_time
from Infrastructure.BenchmarkBuilder.BenchmarkBuilderException import BenchmarkCreationFailed
from Infrastructure.Builders.ProcessorBuilder.CaseStudiesGenerators.CaseStudyGenerator import \
    CaseStudyGenerator
from Infrastructure.Builders.ProcessorBuilder.DataGenerators.SignatureGenerator.SignatureGenerator import SignatureGenerator
from Infrastructure.Builders.ProcessorBuilder.DataGenerators.DataGolfGenerator.DataGolfGenerator import DataGolfGenerator
from Infrastructure.Builders.ProcessorBuilder.DataGenerators.PatternGenerator.PatternGenerator import PatternsGenerator
from Infrastructure.Builders.ProcessorBuilder.PolicyGenerators.MfotlPolicyGenerator.MfotlPolicyGenerator import \
    MfotlPolicyGenerator
from Infrastructure.Builders.ProcessorBuilder.PolicyGenerators.PatternPolicyGenerator.PatternPolicyGenerator import PatternPolicyGenerator
from Infrastructure.DataTypes.Contracts.BenchmarkContract import CaseStudyBenchmarkContract, PolicyGenerators, \
    DataGenerators
from Infrastructure.DataTypes.Contracts.SubContracts.CaseStudyContract import construct_case_study, CaseStudyMapper
from Infrastructure.DataTypes.Contracts.SubContracts.SyntheticContract import SyntheticExperiment, \
    construct_synthetic_experiment_sig, construct_synthetic_experiment_pattern, TimeGuarded
from Infrastructure.DataTypes.FileRepresenters.FingerPrintHandler import FingerPrintHandler
from Infrastructure.DataTypes.FileRepresenters.ScratchFolderHandler import ScratchFolderHandler
from Infrastructure.DataTypes.FileRepresenters.StatsHandler import StatsHandler
from Infrastructure.DataTypes.FingerPrint.FingerPrint import data_class_to_finger_print
from Infrastructure.DataTypes.Types.custome_type import ExperimentType

from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate, run_monitor
from Infrastructure.Monitors.MonitorExceptions import TimedOut, ToolException, ResultErrorException
from Infrastructure.constants import FINGERPRINT_DATA, FINGERPRINT_EXPERIMENT
from Infrastructure.printing import print_headline, print_footline


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
    print(f"-> Attempting to initialize Policy Generator {name}")
    if name == PolicyGenerators.MFOTLGENERATOR:
        mfotl_gen = MfotlPolicyGenerator("gen_mfotl", path_to_build_inner)
        print("    -> (Success)")
        return mfotl_gen
    elif name == PolicyGenerators.PATTERNS:
        pattern_policy = PatternPolicyGenerator()
        print("    -> (Success)")
        return pattern_policy
    else:
        print("Not implemented yet")


def init_data_generator(tag: DataGenerators, path_to_project):
    print(f"-> Attempting to initialize Data Generator {tag}")
    if tag == DataGenerators.DATAGOLF:
        data_golf = DataGolfGenerator("datagolf", path_to_project)
        print("    -> (Success)")
        return data_golf
    elif tag == DataGenerators.DATAGENERATOR:
        sig_gen = SignatureGenerator("gen_data", path_to_project)
        print("    -> (Success)")
        return sig_gen
    elif tag == DataGenerators.PATTERNS:
        pattern_gen = PatternsGenerator("gen_data", path_to_project)
        print("    -> (Success)")
        return pattern_gen
    else:
        raise NotImplemented("Not implemented yet()")


class BenchmarkBuilder(BenchmarkBuilderTemplate, ABC):
    def __init__(
            self, contract, path_to_project, data_setup,
            gen_mode: ExperimentType, time_guard: TimeGuarded,
            tools_to_build, oracle=None, seeds=None
    ):
        print_headline("(Starting) Init Benchmark")
        self.contract = contract
        self.seeds = seeds

        self.path_to_build = path_to_project + "/Infrastructure/build"
        self.path_to_experiment = path_to_project + "/Infrastructure/experiments"
        self.path_to_named_experiment = self.path_to_experiment + "/" + self.contract.experiment_name

        # Initialize oracle to None by default
        self.oracle = None
        self.oracle_name = None
        if oracle:
            self.oracle_name = oracle[1]
            self.oracle = oracle[0].get_oracle(self.oracle_name)
        self.gen_mode = gen_mode

        self.time_guard = time_guard
        self.time_out = self.time_guard.upper_bound
        self.tools_to_build = tools_to_build

        if not os.path.exists(self.path_to_experiment):
            os.mkdir(self.path_to_experiment)

        if not os.path.exists(self.path_to_named_experiment):
            os.mkdir(self.path_to_named_experiment)

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
                fph = FingerPrintHandler({FINGERPRINT_EXPERIMENT: new_experiment_fingerprint}).to_file(fingerprint_location)
                fph.to_file(fingerprint_location)
        else:
            self.data_gen = init_data_generator(contract.data_source, path_to_project)
            self.policy_gen = init_policy_generator(contract.policy_source, path_to_project)
            self.policy_setup = asdict(contract.policy_setup)
            self.experiment = contract.experiment
            print_footline("(Finished) Init Benchmark")
            if os.path.exists(fingerprint_location):
                fph = FingerPrintHandler.from_file(fingerprint_location)
                old_data_setup_fingerprint = fph.get_attr(FINGERPRINT_DATA)
                old_experiment_fingerprint = fph.get_attr(FINGERPRINT_EXPERIMENT)
                new_data_setup_fingerprint = data_class_to_finger_print(data_setup)
                if not (old_experiment_fingerprint == new_experiment_fingerprint
                        and old_data_setup_fingerprint == new_data_setup_fingerprint):
                    self._build()
            else:
                self._build()
                new_data_setup_fingerprint = data_class_to_finger_print(data_setup)
                fph = FingerPrintHandler(
                    {FINGERPRINT_DATA: new_data_setup_fingerprint, FINGERPRINT_EXPERIMENT: new_experiment_fingerprint})
                fph.to_file(fingerprint_location)

    def _build(self):
        print("\n" + "=" * 20 + " Benchmark Build " + "=" * 20)
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
            print("\n" + "=" * 20 + " Benchmark Build (done) " + "=" * 20)
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

    def run(
            self, tools: List[AbstractMonitorTemplate],
            parameters: dict[AnyStr, dict[AnyStr, Any]]
    ) -> pandas.DataFrame:
        print("-" * 50)
        print("="*15 + "   Run Experiments  " + "="*15)
        print("-" * 50)
        settings_result = pd.DataFrame(columns=["Status", "Name", "Setting", "pre", "runtime", "post", "wall time", "max mem", "cpu"])

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

        signature_file = f"signature.sig"
        formula_file = f"formula.mfotl"

        for path_to_folder in path_generator(self.gen_mode, self.experiment, self.path_to_named_experiment):
            sfh = ScratchFolderHandler(path_to_folder)
            for num_len in self.experiment.num_data_set_sizes:
                data_file = f"data_{num_len}.csv"
                for tool in tools:
                    print(path_to_folder)
                    run_tools(
                        settings_result=settings_result, tool=tool, time_guard=self.time_guard,
                        oracle=self.oracle, path_to_folder=path_to_folder,
                        data_file=data_file, signature_file=signature_file, formula_file=formula_file
                    )
                    sfh.clean_up_folder()
            sfh.remove_folder()
        return settings_result


class Status(Enum):
    OK = "OK"
    TO = "Time out"
    TE = "Tool Error"
    RE = "Result Error"


def run_tools(settings_result, tool, time_guard, oracle, path_to_folder, data_file, signature_file, formula_file):
    setting_id = ""
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
            Status.OK, tool.name, setting_id, prep, runtime, prop,
            parse_wall_time(wall_time), max_mem, cpu
        ]
        return settings_result
    except TimedOut as e:
        print(f"Monitor {tool.name} timed out: {e}")
        settings_result.loc[len(settings_result)] = [
            Status.TO, tool.name, setting_id, None, None, None,
            None, None, None
        ]
        return settings_result
    except ToolException as e:
        print(f"ToolException for monitor {tool.name}: {e}")
        settings_result.loc[len(settings_result)] = [
            Status.TE, tool.name, setting_id, None, None, None,
            None, None, None
        ]
        return settings_result
    except ResultErrorException as e:
        print(f"ResultErrorException for monitor {tool.name}: {e.args[1]}")
        stats = StatsHandler(path_to_folder).get_stats()
        if stats is not None:
            wall_time, max_mem, cpu = stats
        else:
            wall_time, max_mem, cpu = None, None, None

        (prep, runtime, prop) = e.args[0]
        settings_result.loc[len(settings_result)] = [
            Status.RE, tool.name, setting_id, prep, runtime, prop,
            parse_wall_time(wall_time), max_mem, cpu
        ]
        return settings_result


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
