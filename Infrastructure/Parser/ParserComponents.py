import json
from dataclasses import asdict

from Infrastructure.BenchmarkBuilder.BenchmarkBuilder import BenchmarkBuilder
from Infrastructure.Builders.ProcessorBuilder.DataGenerators.DataGolfGenerator.DataGolfContract import DataGolfContract
from Infrastructure.Builders.ProcessorBuilder.DataGenerators.PatternGenerator.PatternGeneratorContract import Patterns
from Infrastructure.Builders.ProcessorBuilder.DataGenerators.SignatureGenerator.SignatureGeneratorContract import \
    Signature
from Infrastructure.Builders.ProcessorBuilder.PolicyGenerators.MfotlPolicyGenerator.MfotlPolicyContract import \
    PolicyGeneratorContract
from Infrastructure.Builders.ProcessorBuilder.PolicyGenerators.PatternPolicyGenerator.PatternPolicyContract import \
    PatternPolicyContract
from Infrastructure.Builders.ToolBuilder.ToolManager import ToolManager
from Infrastructure.DataTypes.Contracts.BenchmarkContract import CaseStudyBenchmarkContract, SyntheticBenchmarkContract, \
    DataGenerators, PolicyGenerators
from Infrastructure.DataTypes.Contracts.SubContracts.SyntheticContract import SyntheticExperiment
from Infrastructure.DataTypes.Contracts.SubContracts.TimeBounds import TimeGuarded, TimeGuardingTool
from Infrastructure.DataTypes.Types.custome_type import BranchOrRelease, ExperimentType
from Infrastructure.Monitors.MonPoly.MonPoly import MonPoly
from Infrastructure.Monitors.MonitorManager import MonitorManager
from Infrastructure.Monitors.TimelyMon.TimelyMon import TimelyMon
from Infrastructure.Monitors.WhyMon.WhyMon import WhyMon
from Infrastructure.Oracles.DataGolfOracle.DataGolfOracle import DataGolfOracle
from Infrastructure.Oracles.OracleManager import OracleManager
from Infrastructure.Oracles.VeriMonOracle.VeriMonOracle import VeriMonOracle
from Infrastructure.Parser.ParserConstants import TOOL_MANAGER, MONITORS, ORACLES, TIME_GUARD, DATA_SETUP, POLICY_SETUP, \
    BENCHMARK_CONTRACT, BENCHMARK_BUILDER


def deconstruct_tool_manager(tool_manager: ToolManager):
    tools = dict()
    for index, image in enumerate(tool_manager.images.values()):
        tools[str(index)] = {
            "name": str(image.name),
            "branch": str(image.branch),
            "release": str(image.release)
        }
    return {TOOL_MANAGER: tools}


def construct_tool_manager(json_dump, path_to_project):
    def parse_branch_or_release(val_):
        if val_ == "BranchOrRelease.Branch":
            return BranchOrRelease.Branch
        else:
            return BranchOrRelease.Release

    tools = json_dump[TOOL_MANAGER]
    tools_to_build = [[items["name"], items["branch"], parse_branch_or_release(items["release"])] for items in tools.values()]
    return ToolManager(tools_to_build=tools_to_build, path_to_project=path_to_project)


def deconstruct_monitor_manager(monitor_manager: MonitorManager):
    def monitor_to_identifier(monitor_):
        if isinstance(monitor_, TimelyMon):
            return "TimelyMon"
        elif isinstance(monitor_, MonPoly):
            return "MonPoly"
        elif isinstance(monitor_, WhyMon):
            return "WhyMon"
        else:
            raise NotImplemented()

    monitors = dict()
    for key in monitor_manager.monitors.keys():
        print(key)
        monitor = monitor_manager.monitors[key]
        print(monitor)
        print(monitor.image)
        monitors[key] = {
            "identifier": monitor_to_identifier(monitor), "name": key,
            "branch": monitor.image.branch, "params": json.dumps(monitor.params)
        }
    return {MONITORS: monitors}


def construct_monitor_manager(json_dump, tool_manager: ToolManager, path_to_project):
    monitors_to_build = []
    monitors = json_dump[MONITORS]
    for key in monitors.keys():
        items = monitors[key]
        params = json.loads(items["params"])
        params["path_to_project"] = path_to_project
        monitors_to_build.append([items["identifier"], items["name"], items["branch"], params])
    return MonitorManager(tool_manager=tool_manager, monitors_to_build=monitors_to_build)


def deconstruct_oracle_manager(oracle_manager: OracleManager):
    def oracle_to_identifier(oracle_):
        if isinstance(oracle_, VeriMonOracle):
            return "VeriMonOracle", oracle_.verimon.name, json.dumps(oracle.parameters)
        elif isinstance(oracle_, DataGolfOracle):
            return "DataGolfOracle", "", json.dumps(dict())

    oracles = dict()
    for oracle_key in oracle_manager.oracles.keys():
        oracle = oracle_manager.oracles[oracle_key]
        identifier, name, params = oracle_to_identifier(oracle)
        oracles[oracle_key] = {
            "identifier": identifier,
            "name": name,
            "params": params
        }
    return {ORACLES: oracles}


def construct_oracle_manager(json_dump, monitor_manager: MonitorManager, path_to_project):
    oracles_to_build = []
    oracles_dump = json_dump[ORACLES]
    for key in oracles_dump.keys():
        items = oracles_dump[key]
        params = items["params"]
        params = json.loads(params)
        params["path_to_project"] = path_to_project
        oracles_to_build.append([key, items["identifier"], items["name"], params])
    return OracleManager(monitor_manager=monitor_manager, oracles_to_build=oracles_to_build)


def deconstruct_time_guarded(time_guarded: TimeGuarded):
    def guard_type_to_str(gt):
        if gt == TimeGuardingTool.Monitor:
            return "Monitor"
        elif gt == TimeGuardingTool.Oracle:
            return "Oracle"
        else:
            return "Generator"

    return {
        TIME_GUARD: {
            "time_guarded": str(time_guarded.time_guarded),
            "guard_type": guard_type_to_str(time_guarded.guard_type),
            "lower_bound": time_guarded.lower_bound,
            "upper_bound": time_guarded.upper_bound,
            "guard_name": time_guarded.guard_name
        }
    }


def construct_time_guarded(json_dump, monitor_manager: MonitorManager):
    def str_to_guard_type(gt):
        if gt == "Monitor":
            return TimeGuardingTool.Monitor
        elif gt == "Oracle":
            return TimeGuardingTool.Oracle
        else:
            return TimeGuardingTool.Generator

    vals = json_dump[TIME_GUARD]
    return TimeGuarded(
        time_guarded=vals["time_guarded"], lower_bound=vals["lower_bound"], upper_bound=vals["upper_bound"],
        guard_type=str_to_guard_type(vals["guard_type"]), guard_name=vals["guard_name"], monitor_manager=monitor_manager
    )


def deconstruct_data_setup(data_setup):
    def data_setup_to_str(data_setup_):
        if isinstance(data_setup_, Patterns):
            return "Patterns"
        elif isinstance(data_setup_, Signature):
            return "Signature"
        elif isinstance(data_setup_, DataGolfContract):
            return "DataGolfContract"
        else:
            raise NotImplemented()

    return {DATA_SETUP: {
        data_setup_to_str(data_setup): asdict(data_setup)
    }}


def construct_data_setup(json_dump):
    def str_to_data_setup(contract_name_, vals_):
        if contract_name_ == "Patterns":
            return Patterns(**vals_)
        elif contract_name_ == "Signature":
            return Signature(**vals_)
        elif contract_name_ == "DataGolfContract":
            return DataGolfContract(**vals_)

    contract_name = list(json_dump[DATA_SETUP].keys())[0]
    vals = json_dump[DATA_SETUP][contract_name]
    return str_to_data_setup(contract_name, vals)


def deconstruct_policy_setup(policy_setup):
    def policy_setup_to_str(data_setup_):
        if isinstance(data_setup_, PolicyGeneratorContract):
            return "PolicyGeneratorContract"
        elif isinstance(data_setup_, PatternPolicyContract):
            return "PatternPolicyContract"
        else:
            raise NotImplemented()

    return {POLICY_SETUP: {
        policy_setup_to_str(policy_setup): asdict(policy_setup)
    }}


def construct_policy_setup(json_dump):
    def str_to_policy_setup(contract_name_, vals_):
        if contract_name_ == "PolicyGeneratorContract":
            return PolicyGeneratorContract(**vals_)

    contract_name = list(json_dump[POLICY_SETUP].keys())[0]
    vals = json_dump[POLICY_SETUP][contract_name]
    return str_to_policy_setup(contract_name, vals)


def deconstruct_synthetic_experiment(experiment):
    return json.dumps(experiment.__dict__)


def construct_synthetic_experiment(json_dump):
    return SyntheticExperiment(**json.loads(json_dump))


def deconstruct_benchmark_contract(benchmark_contract):
    if isinstance(benchmark_contract, CaseStudyBenchmarkContract):
        return {BENCHMARK_CONTRACT: {"CaseStudyBenchmarkContract": {
            "experiment_name": benchmark_contract.experiment_name,
            "case_study_name": benchmark_contract.case_study_name
        }}}
    elif isinstance(benchmark_contract, SyntheticBenchmarkContract):
        return {BENCHMARK_CONTRACT: {"SyntheticBenchmarkContract": {
            "experiment_name": benchmark_contract.experiment_name,
            "data_source": str(benchmark_contract.data_source),
            "policy_source": str(benchmark_contract.policy_source),
            "policy_setup": deconstruct_policy_setup(benchmark_contract.policy_setup),
            "experiment": deconstruct_synthetic_experiment(benchmark_contract.experiment)
        }}}


def construct_benchmark_contract(json_dump):
    def str_data_generators(datagen):
        if datagen == "DataGenerators.DATAGOLF":
            return DataGenerators.DATAGOLF
        elif datagen == "DataGenerators.DATAGENERATOR":
            return DataGenerators.DATAGENERATOR

    def str_policy_generators(policygen):
        if policygen == "PolicyGenerators.MFOTLGENERATOR":
            return PolicyGenerators.MFOTLGENERATOR
        elif policygen == "PolicyGenerators.PATTERNS":
            return PolicyGenerators.PATTERNS

    vals = json_dump[BENCHMARK_CONTRACT]
    if "CaseStudyBenchmarkContract" in vals:
        inner_vals = vals["CaseStudyBenchmarkContract"]
        return CaseStudyBenchmarkContract(
            experiment_name=inner_vals["experiment_name"],
            case_study_name=inner_vals["case_study_name"]
        )
    else:
        inner_vals = vals["SyntheticBenchmarkContract"]
        return SyntheticBenchmarkContract(
            experiment_name=inner_vals["experiment_name"],
            experiment=construct_synthetic_experiment(inner_vals["experiment"]),
            policy_setup=construct_policy_setup(inner_vals["policy_setup"]),
            policy_source=str_policy_generators(inner_vals["policy_source"]),
            data_source=str_data_generators(inner_vals["data_source"])
        )


def deconstruct_benchmark(benchmark: BenchmarkBuilder):
    name = benchmark.oracle_name if hasattr(benchmark, "oracle") else None
    seeds = benchmark.seed_retriever()
    return {BENCHMARK_BUILDER: {
        "experiment_type": str(benchmark.gen_mode),
        "tools_to_build": benchmark.tools_to_build,
        "oracle_name": name,
        "seeds": seeds
    }}


def construct_benchmark(json_dump, benchmark, path_to_project, data_setup, time_guard, oracle_manager):
    def str_to_experiment_type(name):
        if name == "ExperimentType.Signature":
            return ExperimentType.Signature
        elif name == "ExperimentType.Signature":
            return ExperimentType.Pattern
        elif name == "ExperimentType.CaseStudy":
            return ExperimentType.CaseStudy

    vals = json_dump[BENCHMARK_BUILDER]
    experiment_type = str_to_experiment_type(vals["experiment_type"])
    oracle_name = vals["oracle_name"]
    oracle = (oracle_manager, oracle_name) if oracle_name else None
    return BenchmarkBuilder(
        benchmark, path_to_project, data_setup, experiment_type,
        time_guard, vals["tools_to_build"], oracle
    )
