import copy
import os
from typing import List, Tuple, Optional

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.BenchmarkBuilder.Coordinator.CaseStudyCoordinator import RunOracleException, TimedOut
from Infrastructure.BenchmarkBuilder.Coordinator.Coordinator import Coordinator
from Infrastructure.DataTypes.Contracts.SubContracts.SyntheticContract import SyntheticExperiment
from Infrastructure.DataTypes.Contracts.SubContracts.TimeBounds import TimeConstraints, ConstructionConstraints, TimeGuardingTool
from Infrastructure.DataTypes.FileRepresenters.ScratchFolderHandler import ScratchFolderHandler
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate
from Infrastructure.Oracles.AbstractOracleTemplate import AbstractOracleTemplate
from Infrastructure.constants import ORACLE_KEY, SEEDS_KEY, PATH_KEY, SIZE_KEY, FREE_VARIABLES_KEY, PLACEHOLDER_EVENT, \
    SIGNATURE_FILE, SIGNATURE_FILE_ENDING, POLICY_FILE, POLICY_FILE_ENDING, TRACE_LENGTH_KEY, SIGNATURE_KEY
from Infrastructure.DataTypes.FileRepresenters.SeedHandler import SeedHandler
from Infrastructure.DataTypes.FileRepresenters.FileHandling import to_file
from Infrastructure.Monitors.MonitorExceptions import ToolException
from Infrastructure.AutoConversion.InputOutputTraceFormats import trace_inout_format_to_str


class SyntheticCoordinator(Coordinator):
    def __init__(
        self, experiment: SyntheticExperiment, data_setup, data_source, policy_setup, policy_source,
        oracle: Optional[AbstractOracleTemplate], constraints: TimeConstraints, path_manager: PathManager, seeds=None
    ):
        self.experiment = experiment
        self.path_manager = path_manager
        self.path_to_folder = self.path_manager.get_path("path_to_folder")

        self.data_setup = copy.copy(data_setup)
        self.data_source = data_source
        self.policy_setup = copy.copy(policy_setup)
        self.policy_source = policy_source

        self.oracle = oracle
        self.constraints = constraints
        self.seeds = seeds

        self.instructions = []

    def build(self):
        index = 0
        for num_ops in self.experiment.num_operators:
            ops_path = f"{self.path_to_folder}/operators_{num_ops}"
            os.makedirs(ops_path, exist_ok=True)

            for num_fv in self.experiment.num_fvs:
                fvs_path = f"{ops_path}/free_vars_{num_fv}"
                os.makedirs(fvs_path, exist_ok=True)

                for num_set in self.experiment.num_setting:

                    num_path = f"{fvs_path}/num_{num_set}"
                    self.data_setup[PATH_KEY] = num_path
                    os.makedirs(num_path, exist_ok=True)

                    if self.oracle is not None or self.data_setup.get(ORACLE_KEY):
                        os.makedirs(f"{num_path}/result", exist_ok=True)

                    # todo seed handling better access and support fine grained settings
                    if self.seeds:
                        gen_seed, policy_seed = self.seeds[str([num_ops, num_fv, num_set])]
                        if policy_seed:
                            self.policy_setup[SEEDS_KEY] = policy_seed
                        if gen_seed:
                            self.data_setup[SEEDS_KEY] = gen_seed
                    # todo unify seed handling and support fine grained settings
                    if self.seeds:
                        gen_seed, _ = self.seeds[str([num_ops, num_set])]
                        if gen_seed:
                            self.data_setup[SEEDS_KEY] = gen_seed

                    print(f"    Build {num_path}")
                    trace_format = self.data_source.output_format()
                    policy_format = self.policy_source.output_format()
                    constraint = self.constraints.construction_constraint()
                    if constraint is not None and (constraint.lower_bound is not None or constraint.upper_bound is not None):
                        data_file, policy_file, sig_file, result_file = guarded_synthetic_experiment(
                            num_path=num_path, num_ops=num_ops, num_fv=num_fv, policy_setup=self.policy_setup,
                            policy_source=self.policy_source, data_setup=self.data_setup, data_source=self.data_source,
                            num_data_set_sizes=self.experiment.num_data_set_sizes, oracle=self.oracle,
                            constraints=constraint, path_manager=self.path_manager
                        )
                    else:
                        data_file, policy_file, sig_file, result_file = guarded_synthetic_experiment(
                            num_path=num_path, num_ops=num_ops, num_fv=num_fv, policy_setup=self.policy_setup,
                            policy_source=self.policy_source, data_setup=self.data_setup, data_source=self.data_source,
                            num_data_set_sizes=self.experiment.num_data_set_sizes, oracle=self.oracle,
                            constraints=None, path_manager=self.path_manager
                        )
                    self.instructions.append((index, data_file, trace_format, policy_file, policy_format, sig_file, result_file))
                    index += 1

    def iterate_settings(self) -> List[Tuple[int, str, InputOutputTraceFormats, str, InputOutputPolicyFormats, Optional[str], Optional[str]]]:
        return self.instructions


def guarded_synthetic_experiment(
    num_path: str, num_ops: int, num_fv: int, policy_setup, policy_source, data_setup, data_source,
    num_data_set_sizes: List[int], oracle: Optional[AbstractOracleTemplate], constraints: Optional[ConstructionConstraints],
    path_manager: PathManager
):
    lower_time_bound = None if constraints is None else constraints.lower_bound
    upper_time_bound = None if constraints is None else constraints.upper_bound

    guard_type = None if constraints is None else constraints.guard_type
    guard = None if constraints is None else constraints.guard

    trace_seed = data_setup.get(SEEDS_KEY, None)
    policy_seed = policy_setup.get(SEEDS_KEY, None)

    while True:
        policy_file, sig_file = synthetic_policy_creation(
            inner_path=num_path, num_ops=num_ops, num_fv=num_fv, policy_setup=policy_setup,
            policy_source=policy_source, data_setup=data_setup, data_source=data_source
        )

        time_out_in_for_loop, data_file, result_file = synthetic_trace_creation(
            num_path=num_path, signature_file=sig_file, policy_file=policy_file, data_source=data_source, data_setup=data_setup,
            policy_format=policy_source.output_format(), num_data_set_sizes=num_data_set_sizes, oracle=oracle, path_manager=path_manager,
            time_on=lower_time_bound, time_out=upper_time_bound, guard_type=guard_type, guard=guard
        )

        sfh = ScratchFolderHandler(num_path)
        if not time_out_in_for_loop:
            sfh.remove_folder()
            return data_file, policy_file, sig_file, result_file
        else:
            sfh.clean_up_folder()
            if trace_seed is not None and policy_seed is not None:
                raise Exception("Error: The selected time constraints and seeds prevent the construction in time!")
            elif trace_seed is not None or policy_seed is not None:
                print("Warning: The selected time constraints and seeds may prevent the construction in time!")


def synthetic_policy_creation(
    inner_path: str, num_ops: int, num_fv: int, policy_setup, policy_source, data_setup, data_source,
):
    sh = SeedHandler(inner_path)
    while True:
        policy_setup[SIZE_KEY] = num_ops
        policy_setup[FREE_VARIABLES_KEY] = num_fv

        seed, policy, sig = policy_source.generate_policy(policy_setup)
        sh.add_seed_policy(seed)

        if sig is not None:
            sig += f"\n{PLACEHOLDER_EVENT}"
            to_file(inner_path, sig, SIGNATURE_FILE, SIGNATURE_FILE_ENDING)
        to_file(inner_path, policy, POLICY_FILE, POLICY_FILE_ENDING)

        signature = None if sig is None else f"{SIGNATURE_FILE}.{SIGNATURE_FILE_ENDING}"
        if data_source.check_policy(inner_path, signature, f"{POLICY_FILE}.{POLICY_FILE_ENDING}"):
            data_setup[SIGNATURE_KEY] = sig
            return f"{POLICY_FILE}.{POLICY_FILE_ENDING}", signature


def synthetic_trace_creation(
        num_path: str, signature_file: Optional[str], policy_file: str, data_source, data_setup,
        policy_format: InputOutputPolicyFormats, num_data_set_sizes: List[int],
        oracle: Optional[AbstractOracleTemplate], path_manager: PathManager,
        time_on: Optional[int], time_out: Optional[int], guard_type: TimeGuardingTool,
        guard: Optional[AbstractMonitorTemplate]
):
    time_out_in_for_loop = False
    data_file = None
    result_file = None

    for (num_len, num_name) in num_data_set_sizes:
        data_setup[TRACE_LENGTH_KEY] = num_len
        sh = SeedHandler(num_path)
        if guard_type is not None and guard_type == TimeGuardingTool.Generator:
            try:
                seed, result_csv = data_source.run_generator(data_setup, time_on, time_out)
                sh.add_seed_generator(seed)
            except TimedOut:
                time_out_in_for_loop = True
                break
        else:
            seed, result_csv = data_source.run_generator(data_setup)
            sh.add_seed_generator(seed)

        trace_format = data_source.output_format()
        trace_ending = trace_inout_format_to_str(trace_format)
        to_file(num_path, result_csv, f"data_{num_name}", trace_ending)
        data_file = f"data_{num_name}.{trace_ending}"

        if oracle is not None:
            oracle.pre_process_data(
                path_to_folder=num_path, data_file=data_file, policy_file=policy_file, signature_file=signature_file,
                trace_source_format=trace_format, policy_source_format=policy_format, path_manager=path_manager
            )
            if guard_type is not None and guard_type == TimeGuardingTool.Oracle:
                try:
                    out, code = oracle.compute_result(time_on, time_out)
                    if code != 0:
                        if code == 124:
                            raise TimedOut()
                        else:
                            raise RunOracleException(out)
                except TimedOut:
                    time_out_in_for_loop = True
                    break
            else:
                out, code = oracle.compute_result()
                if code != 0:
                    raise RunOracleException(out)
            result_file = f"{num_path}/result/result_{num_name}.res"
            oracle.post_process_data(out, result_file)

        if guard_type is not None and guard_type == TimeGuardingTool.Monitor and guard is not None:
            guard.preprocessing(
                path_to_folder=num_path, data_file=data_file, policy_file=policy_file, signature_file=signature_file,
                trace_source_format=trace_format, policy_source_format=policy_format, path_manager=path_manager,
                verbose=False
            )
            try:
                cmd, name = guard.run_offline_command()
                out, code = guard.image.run(parameters=cmd, path_to_data=num_path, time_on=time_on, timeout=time_out, name=name)
                if code != 0:
                    if code == 124:
                        raise TimedOut()
                    elif code == 137:
                        raise ToolException("OOM Killer activated")
                    else:
                        raise ToolException(code)
            except TimedOut:
                time_out_in_for_loop = True
                break
    return time_out_in_for_loop, data_file, result_file
