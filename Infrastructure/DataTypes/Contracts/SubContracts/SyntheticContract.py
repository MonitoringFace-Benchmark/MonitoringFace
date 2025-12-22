import copy
import math
import os

from dataclasses import dataclass
from typing import AnyStr, Optional

from Infrastructure.Builders.ProcessorBuilder.PolicyGenerators.PatternPolicyGenerator.PatternPolicyGenerator import PatternPolicyGenerator
from Infrastructure.DataTypes.Contracts.SubContracts.TimeBounds import TimeGuarded, TimeGuardingTool
from Infrastructure.DataTypes.FileRepresenters.FileHandling import to_file
from Infrastructure.DataTypes.FileRepresenters.ScratchFolderHandler import ScratchFolderHandler
from Infrastructure.DataTypes.FileRepresenters.SeedHandler import SeedHandler
from Infrastructure.Monitors.MonitorExceptions import GeneratorException, TimedOut, ToolException
from Infrastructure.Oracles.AbstractOracleTemplate import AbstractOracleTemplate
from Infrastructure.Oracles.OracleExceptions import RunOracleException
from Infrastructure.constants import ORACLE_KEY, PLACEHOLDER_EVENT


@dataclass
class SyntheticExperiment:
    num_operators: list[int]
    num_fvs: list[int]
    num_setting: list[int]
    num_data_set_sizes: list[int]


def construct_synthetic_experiment_pattern(
        experiment: SyntheticExperiment,
        path_to_folder: AnyStr, data_setup_, data_source,
        oracle: Optional[AbstractOracleTemplate], time_guard, seeds
):
    policy_source = PatternPolicyGenerator()
    sh = SeedHandler(path_to_folder)
    data_setup = copy.copy(data_setup_)
    for num_ops in experiment.num_operators:
        ops_path = path_to_folder + "/" + f"operators_{num_ops}"
        if not os.path.exists(ops_path):
            os.mkdir(ops_path)

        for num_set in experiment.num_setting:
            num_path = ops_path + "/" + f"num_{num_set}"
            data_setup["path"] = num_path
            if not os.path.exists(num_path):
                os.mkdir(num_path)

            (seed, sig, formula), _ = policy_source.generate_policy(data_setup)
            sh.add_seed_policy(seed)

            to_file(num_path, sig, "signature", "sig")
            to_file(num_path, formula, "formula", "mfotl")

            if oracle is not None or data_setup.get("oracle"):
                if not os.path.exists(f"{num_path}/result"):
                    os.mkdir(f"{num_path}/result")

            if seeds:
                gen_seed, policy_seed = seeds[str([num_ops, num_set])]
                if gen_seed:
                    data_setup["seed"] = gen_seed

            print(f"    Build {num_path}")
            if not time_guard.time_guarded:
                unguarded_synthetic_experiment_pattern(num_path, experiment.num_data_set_sizes,
                                                       data_source, data_setup, oracle, None)
            else:
                guarded_synthetic_experiment_pattern(num_path, data_source, data_setup,
                                                     experiment.num_data_set_sizes, oracle, time_guard)


def guarded_synthetic_experiment_pattern(
        num_path, data_source, data_setup,
        num_data_set_sizes, oracle, time_guard
):
    time_on = time_guard.lower_bound
    time_out = time_guard.upper_bound

    guard_type = time_guard.guard_type
    guard = time_guard.guard

    num_data_set_sizes = [(l, str(l)) for l in num_data_set_sizes]
    i = 1

    while True:
        sfh = ScratchFolderHandler(num_path)

        time_out_in_for_loop = guarded_synthetic_experiment_inner(
            num_path, data_source, data_setup, num_data_set_sizes, oracle, time_on, time_out, guard_type, guard
        )

        print("        Attempting policy {i}")
        i += 1

        if not time_out_in_for_loop:
            sfh.remove_folder()
            break
        else:
            # reduce the size to make it pass
            num_data_set_sizes = [(math.ceil(l * 0.85), ls) for (l, ls) in num_data_set_sizes]
            sfh.clean_up_folder()


def construct_synthetic_experiment_sig(
        experiment: SyntheticExperiment, path_to_folder: AnyStr, data_setup_, data_source,
        policy_setup_, policy_source,
        oracle: Optional[AbstractOracleTemplate], time_guard: TimeGuarded, seeds=None
):
    data_setup = copy.copy(data_setup_)
    policy_setup = copy.copy(policy_setup_)
    for num_ops in experiment.num_operators:
        ops_path = path_to_folder + "/" + f"operators_{num_ops}"
        if not os.path.exists(ops_path):
            os.mkdir(ops_path)

        for num_fv in experiment.num_fvs:
            fvs_path = ops_path + "/" + f"free_vars_{num_fv}"
            if not os.path.exists(fvs_path):
                os.mkdir(fvs_path)

            for num_set in experiment.num_setting:
                num_path = fvs_path + "/" + f"num_{num_set}"
                data_setup["path"] = num_path
                if not os.path.exists(num_path):
                    os.mkdir(num_path)

                if oracle is not None or data_setup.get(ORACLE_KEY):
                    if not os.path.exists(f"{num_path}/result"):
                        os.mkdir(f"{num_path}/result")

                if seeds:
                    gen_seed, policy_seed = seeds[str([num_ops, num_fv, num_set])]
                    if policy_seed:
                        policy_setup["seed"] = policy_seed
                    if gen_seed:
                        data_setup["seed"] = gen_seed

                print(f"    Build {num_path}")
                if not time_guard.time_guarded:
                    unguarded_synthetic_experiment_sig(num_path, num_ops, num_fv, policy_setup, policy_source,
                                                       data_source, data_setup, experiment.num_data_set_sizes.copy(),
                                                       oracle, None)
                else:
                    guarded_synthetic_experiment_sig(num_path, num_ops, num_fv, policy_setup, policy_source,
                                                     data_source, data_setup, experiment.num_data_set_sizes.copy(),
                                                     oracle, time_guard)


def guarded_synthetic_experiment_sig(
        num_path, num_ops, num_fv, formula_setup, formula_source,
        data_source, data_setup, num_data_set_sizes, oracle, time_guard
):
    time_on = time_guard.lower_bound
    time_out = time_guard.upper_bound

    guard_type = time_guard.guard_type
    guard = time_guard.guard

    num_data_set_sizes = [(l, str(l)) for l in num_data_set_sizes]

    i = 1
    while True:
        synthetic_formula_guard(num_path, num_ops, num_fv, formula_setup, formula_source, data_source, data_setup)
        sfh = ScratchFolderHandler(num_path)

        time_out_in_for_loop = guarded_synthetic_experiment_inner(
            num_path, data_source, data_setup, num_data_set_sizes, oracle, time_on, time_out, guard_type, guard
        )

        print("        Attempting policy {i}")
        i += 1

        if not time_out_in_for_loop:
            sfh.remove_folder()
            break
        else:
            sfh.clean_up_folder()


def guarded_synthetic_experiment_inner(
        num_path, data_source, data_setup, num_data_set_sizes,
        oracle, time_on, time_out, guard_type, guard
):
    time_out_in_for_loop = False
    for (num_len, num_name) in num_data_set_sizes:
        data_setup["trace_length"] = num_len
        sh = SeedHandler(num_path)
        if guard_type == TimeGuardingTool.Generator:
            try:
                seed, result_csv, code = data_source.run_generator(data_setup, time_on, time_out)
                sh.add_seed_generator(seed)
                if code != 0:
                    raise GeneratorException(result_csv)
            except TimedOut:
                time_out_in_for_loop = True
                break
        else:
            seed, result_csv, code = data_source.run_generator(data_setup)
            sh.add_seed_generator(seed)
            if code != 0:
                raise GeneratorException(result_csv)

        to_file(num_path, result_csv, f"data_{num_name}", "csv")

        if oracle is not None:
            oracle.pre_process_data(num_path, f"data_{num_name}.csv",
                                    "signature.sig", "formula.mfotl")

            if guard_type == TimeGuardingTool.Oracle:
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
            oracle.post_process_data(out, f"{num_path}/result/result_{num_name}.res")

        if guard_type == TimeGuardingTool.Monitor:
            guard.pre_processing(num_path, f"data_{num_name}.csv", "signature.sig", "formula.mfotl")
            try:
                _, code = guard.run_offline(time_on, time_out)
                if code != 0:
                    if code == 124:
                        raise TimedOut()
                    else:
                        raise ToolException()
            except TimedOut:
                time_out_in_for_loop = True
                break
    return time_out_in_for_loop


def synthetic_formula_guard(
        inner_path, num_ops_, num_fv_, formula_setup_,
        formula_source_, data_source_, data_setup_
):
    sh = SeedHandler(inner_path)
    while True:
        formula_setup_["size"] = num_ops_
        formula_setup_["max_arity"] = num_fv_

        (seed, sig, formula), _ = formula_source_.generate_policy(formula_setup_)
        sh.add_seed_policy(seed)

        sig += f"\n{PLACEHOLDER_EVENT}"  # ensure that the placeholder event is available
        to_file(inner_path, sig, "signature", "sig")
        to_file(inner_path, formula, "formula", "mfotl")

        if data_source_.check_policy(inner_path, "signature.sig", "formula.mfotl"):
            data_setup_["sig"] = sig
            break


def unguarded_synthetic_experiment_sig(
        num_path, num_ops, num_fv, policy_setup, policy_source,
        data_source, data_setup, num_data_set_sizes, oracle, time_out
):
    synthetic_formula_guard(num_path, num_ops, num_fv, policy_setup, policy_source, data_source, data_setup)
    unguarded_synthetic_experiments_inner(num_path, num_data_set_sizes, data_source, data_setup, oracle, time_out)


def unguarded_synthetic_experiment_pattern(
        num_path, num_data_set_sizes, data_source, data_setup, oracle, time_out
):
    unguarded_synthetic_experiments_inner(num_path, num_data_set_sizes, data_source, data_setup, oracle, time_out)


def unguarded_synthetic_experiments_inner(
        num_path, num_data_set_sizes, data_source, data_setup, oracle, time_out
):
    sfh = ScratchFolderHandler(num_path)
    sh = SeedHandler(num_path)
    for num_len in num_data_set_sizes:
        data_setup["trace_length"] = num_len

        seed, result_csv, code = data_source.run_generator(data_setup)
        sh.add_seed_generator(seed)
        if code != 0:
            raise GeneratorException(result_csv)

        to_file(num_path, result_csv, f"data_{num_len}", "csv")

        if oracle is not None:
            oracle.pre_process_data(
                num_path, f"data_{num_len}.csv",
                "signature.sig", "formula.mfotl"
            )
            out, code = oracle.compute_result(time_out)
            if code != 0:
                raise RunOracleException(out)
            oracle.post_process_data(out, f"{num_path}/result/result_{num_len}.res")
    sfh.remove_folder()
