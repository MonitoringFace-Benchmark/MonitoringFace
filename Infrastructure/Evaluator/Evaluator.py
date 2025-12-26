import os.path
import subprocess
import urllib.request

from Infrastructure.Builders.ProcessorBuilder.DataGenerators.DataGolfGenerator.DataGolfContract import DataGolfContract
from Infrastructure.Builders.ProcessorBuilder.DataGenerators.PatternGenerator.PatternGeneratorContract import Patterns
from Infrastructure.Builders.ProcessorBuilder.PolicyGenerators.MfotlPolicyGenerator.MfotlPolicyContract import MfotlPolicyContract
from Infrastructure.Builders.ToolBuilder.ToolManager import ToolManager
from Infrastructure.DataTypes.Contracts.BenchmarkContract import DataGenerators, SyntheticBenchmarkContract, \
    PolicyGenerators, CaseStudyBenchmarkContract
from Infrastructure.Builders.ProcessorBuilder.DataGenerators.SignatureGenerator.SignatureGeneratorContract import Signature
from Infrastructure.DataTypes.Contracts.SubContracts.SyntheticContract import SyntheticExperiment
from Infrastructure.DataTypes.Contracts.SubContracts.TimeBounds import TimeGuarded, TimeGuardingTool
from Infrastructure.DataTypes.Types.custome_type import ExperimentType, BranchOrRelease

from Infrastructure.BenchmarkBuilder.BenchmarkBuilder import BenchmarkBuilder

from Infrastructure.Monitors.MonitorManager import MonitorManager
from Infrastructure.Oracles.OracleManager import OracleManager
from Infrastructure.Parser.ParserComponents import construct_tool_manager, construct_data_setup, construct_policy_setup, \
    construct_benchmark_contract, construct_monitor_manager, construct_oracle_manager, construct_time_guarded, \
    construct_benchmark, deconstruct_benchmark, deconstruct_time_guarded, deconstruct_oracle_manager, \
    deconstruct_monitor_manager, deconstruct_tool_manager, deconstruct_data_setup, deconstruct_benchmark_contract


def validate_setup():
    try:
        urllib.request.urlopen('https://www.google.com', timeout=3).getcode()
    except Exception:
        raise RuntimeError("Network connection is not available!")

    docker_ok = subprocess.call(['docker', 'info'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
    if not docker_ok:
        raise RuntimeError("Docker is not available!")


# must be the entry point, either creating or recreating experiments, organizing bootstrapping and so on
# first make a synthetic one work! can hard code the values for now
class Evaluator:
    def __init__(self, structure=None):
        validate_setup()

        # setup folders todo generalize
        your_path_to_project = os.path.dirname(os.path.dirname(os.getcwd()))
        self.path_to_project = your_path_to_project
        self.path_to_build = self.path_to_project + "/Infrastructure/build"
        self.path_to_archive = self.path_to_project + "/Archive"
        if not os.path.exists(self.path_to_build):
            os.mkdir(self.path_to_build)

        self.path_to_experiments = self.path_to_project + "/Infrastructure/experiments"
        if not os.path.exists(self.path_to_experiments):
            os.mkdir(self.path_to_experiments)

        if structure:
            self.build_from_structure(structure)
            return

        tool_manager = ToolManager([
            #("TimelyMon", "input_optims", BranchOrRelease.Branch),
            #("TimelyMon", "development", BranchOrRelease.Branch),
            ("MonPoly", "master", BranchOrRelease.Branch),
            #("WhyMon", "main", BranchOrRelease.Branch),
            #("EnfGuard", "enfguard", BranchOrRelease.Branch),
        ], self.path_to_project)

        data_setup = Patterns(
            trace_length=1000, seed=None, event_rate=1000, index_rate=None, time_stamp=None, linear=1, interval=None,
            star=None, triangle=None, pattern=None, violations=1.0, zipf="x=1.5+3,z=2", prob_a=0.2, prob_b=0.3,
            prob_c=0.5
        )

        data_setup = DataGolfContract(
            path=self.path_to_experiments, sig_file="signature.sig", formula="formula.mfotl", seed=None,
            tup_ts=[0, 1, 2, 3, 4, 5, 6], tup_amt=100, tup_val=1,
            oracle=True, no_rewrite=None, trace_length=5
        )

        #data_setup = Signature(
        #    trace_length=1000, seed=None, event_rate=10000, index_rate=None, time_stamp=None,
        #    sig="", sample_queue=None, string_length=None, fresh_value_rate=None, domain=None
        #)

        # rethink practicals, lattice of operations
        # comparing to the fragments


        policy_setup = MfotlPolicyContract().default_contract()
        policy_setup.num_preds = 4
        policy_setup.prob_eand = 0
        policy_setup.prob_rand = 0
        policy_setup.prob_and = 0.4
        policy_setup.prob_let = 0
        policy_setup.prob_matchF = 0
        policy_setup.prob_matchP = 0

        init = CaseStudyBenchmarkContract(experiment_name="Nokia", case_study_name="Nokia")

        init1 = SyntheticBenchmarkContract(
            "testtest", DataGenerators.DATAGOLF, PolicyGenerators.MFOTLGENERATOR, policy_setup,
            SyntheticExperiment(num_operators=[2], num_fvs=[2], num_setting=[0, 1], num_data_set_sizes=[50])
        )

        monitor_manager = MonitorManager(
            tool_manager=tool_manager,
            monitors_to_build=[
                #("TimelyMon", "TimelyMon 1", "development", {"worker": 1, "output_mode": 1}),
                #("TimelyMon", "TimelyMon 6", "development", {"worker": 6, "output_mode": 1}),
                ("MonPoly", "MonPoly", "master", {"replayer": "gen_data", "path_to_project": self.path_to_project}),
                ("MonPoly", "VeriMon", "master", {"replayer": "gen_data", "verified": (), "path_to_project": self.path_to_project}),
                #("WhyMon", "WhyMon", "main", {"replayer": "gen_data", "path_to_project": self.path_to_project}),
                #("EnfGuard", "EnfGuard", "enfguard", {"replayer": "gen_data", "path_to_build": self.path_to_project})
            ]
        )

        oracle_manager = OracleManager(
            oracles_to_build=[("VeriMonOracle", "VeriMonOracle", "MonPoly",
                               {"replayer": "gen_data", "verified": (), "path_to_project": self.path_to_project})],
            monitor_manager=monitor_manager
        )

        time_guarded = TimeGuarded(
            time_guarded=False, lower_bound=None, upper_bound=200, monitor_manager=monitor_manager,
            guard_type=TimeGuardingTool.Generator
        )

        # todo data_setup to experiment type

        benchmark = BenchmarkBuilder(
            init, self.path_to_project,
            data_setup, ExperimentType.CaseStudy,
            time_guarded,
            ["TimelyMon 1", "MonPoly", "VeriMon"],
            (oracle_manager, "VeriMonOracle")
        )

        res = benchmark.run(monitor_manager.get_monitors(["VeriMon", "MonPoly"]), {})
        print(res)

        x = self.export_to_structure(
            synthetic_contract=init, data_setup=data_setup, tool_manager=tool_manager, monitor_manager=monitor_manager,
            oracle_manager=oracle_manager, time_guarded=time_guarded, benchmark=benchmark
        )
        print(x)

        # performance
        #   offline peak mem and latency    (ok)
        #   measure different stages pre/exec/post (ok)
        #   online (not implemented)

        # correction
        #  conversion to VeriMon for correctness (is the format)
        #  Oracle (implement VeriMon and test datagolf)

        # store and load experiments

        # dejavu(?)

        # stream rv side quest (lola)

        # do analysis

    @staticmethod
    def export_to_structure(
        synthetic_contract, data_setup, tool_manager, monitor_manager,
        oracle_manager, time_guarded, benchmark
    ):
        benchmark_contract_structure = deconstruct_benchmark_contract(benchmark_contract=synthetic_contract)
        data_setup_structure = deconstruct_data_setup(data_setup=data_setup)
        tool_manager_structure = deconstruct_tool_manager(tool_manager=tool_manager)
        monitor_manager_structure = deconstruct_monitor_manager(monitor_manager=monitor_manager)
        oracle_manager_structure = deconstruct_oracle_manager(oracle_manager=oracle_manager)
        time_guarded_structure = deconstruct_time_guarded(time_guarded=time_guarded)
        benchmark_deconstructed = deconstruct_benchmark(benchmark=benchmark)

        structure = benchmark_contract_structure | data_setup_structure | tool_manager_structure | monitor_manager_structure
        return structure | oracle_manager_structure | time_guarded_structure | benchmark_deconstructed

    def build_from_structure(self, structure):
        tool_manager = construct_tool_manager(structure, self.path_to_project)
        data_setup = construct_data_setup(structure)

        benchmark_contract = construct_benchmark_contract(structure)
        monitor_manager = construct_monitor_manager(structure, tool_manager, self.path_to_project)
        oracle_manager = construct_oracle_manager(structure, monitor_manager, self.path_to_project)
        time_guarded = construct_time_guarded(structure, monitor_manager)

        benchmark = construct_benchmark(structure, benchmark_contract, self.path_to_project, data_setup, time_guarded, oracle_manager)
        res = benchmark.run(monitor_manager.get_monitors(benchmark.tools_to_build), {})
        print(res)


if __name__ == "__main__":
    structure = {'benchmark_contract': {'SyntheticBenchmarkContract': {'experiment_name': 'test2', 'data_source': 'DataGenerators.DATAGENERATOR', 'policy_source': 'PolicyGenerators.MFOTLGENERATOR', 'policy_setup': {'policy_setup': {'PolicyGeneratorContract': {'sig_file': None, 'out_file': None, 'seed': None, 'size': None, 'num_preds': 4, 'max_arity': 4, 'non_zero': False, 'aggregation': False, 'prob_and': 0.4, 'prob_or': None, 'prob_eand': 0, 'prob_nand': None, 'prob_rand': 0, 'prob_prev': None, 'prob_once': None, 'prob_next': None, 'prob_eventually': None, 'prob_since': None, 'prob_until': None, 'prob_exists': None, 'prob_let': 0, 'prob_aggreg': None, 'regex': False, 'prob_matchP': 0, 'prob_matchF': 0}}}, 'experiment': '{"num_operators": [5], "num_fvs": [2], "num_setting": [0, 1], "num_data_set_sizes": [50]}'}}, 'data_setup': {'Signature': {'trace_length': 1000, 'seed': None, 'event_rate': 10000, 'index_rate': None, 'time_stamp': None, 'sig': '', 'sample_queue': None, 'fresh_value_rate': None, 'domain': None, 'string_length': None}}, 'tool_manager': {'0': {'name': 'TimelyMon', 'branch': 'input_optims', 'release': 'BranchOrRelease.Branch'}, '1': {'name': 'TimelyMon', 'branch': 'development', 'release': 'BranchOrRelease.Branch'}, '2': {'name': 'MonPoly', 'branch': 'master', 'release': 'BranchOrRelease.Branch'}}, 'monitors': {'TimelyMon 1': {'identifier': 'TimelyMon', 'name': 'TimelyMon 1', 'branch': 'development', 'params': '{"worker": 1, "output_mode": 1, "folder": "/Users/krq770/PycharmProjects/MonitoringFace_curr/Infrastructure/experiments/test2/operators_5/free_vars_2/num_1", "data": "data_50.csv", "signature": "signature.sig", "formula": "formula.mfotl"}'}, 'TimelyMon 6': {'identifier': 'TimelyMon', 'name': 'TimelyMon 6', 'branch': 'development', 'params': '{"worker": 6, "output_mode": 1, "folder": "/Users/krq770/PycharmProjects/MonitoringFace_curr/Infrastructure/experiments/test2/operators_5/free_vars_2/num_1", "data": "data_50.csv", "signature": "signature.sig", "formula": "formula.mfotl"}'}, 'MonPoly': {'identifier': 'MonPoly', 'name': 'MonPoly', 'branch': 'master', 'params': '{"replayer": "gen_data", "path_to_project": "/Users/krq770/PycharmProjects/MonitoringFace_curr", "folder": "/Users/krq770/PycharmProjects/MonitoringFace_curr/Infrastructure/experiments/test2/operators_5/free_vars_2/num_1", "signature": "signature.sig", "formula": "formula.mfotl", "data": "scratch/data_50.csv.monpoly"}'}, 'VeriMon': {'identifier': 'MonPoly', 'name': 'VeriMon', 'branch': 'master', 'params': '{"replayer": "gen_data", "verified": [], "path_to_project": "/Users/krq770/PycharmProjects/MonitoringFace_curr", "folder": "/Users/krq770/PycharmProjects/MonitoringFace_curr/Infrastructure/experiments/test2/operators_5/free_vars_2/num_1", "signature": "signature.sig", "formula": "formula.mfotl", "data": "scratch/data_50.csv.verimon"}'}}, 'oracles': {'VeriMonOracle': {'identifier': 'VeriMonOracle', 'name': 'VeriMon', 'params': '{"replayer": "gen_data", "verified": [], "path_to_project": "/Users/krq770/PycharmProjects/MonitoringFace_curr"}'}}, 'time_guard': {'time_guarded': 'False', 'guard_type': 'Generator', 'lower_bound': None, 'upper_bound': 200, 'guard_name': None}, 'benchmark_builder': {'experiment_type': 'ExperimentType.Signature', 'tools_to_build': ['TimelyMon 1', 'TimelyMon 6', 'MonPoly', 'VeriMon'], 'oracle_name': 'VeriMonOracle', 'seeds': {'[5, 2, 0]': (314159265, 36899), '[5, 2, 1]': (314159265, 34548)}}}
    Evaluator()
