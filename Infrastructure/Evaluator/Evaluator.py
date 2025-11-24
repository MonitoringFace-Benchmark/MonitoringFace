import os.path

from Infrastructure.Builders.ProcessorBuilder.PolicyGenerators.MfotlPolicyGenerator.MfotlPolicyContract import PolicyGeneratorContract
from Infrastructure.Builders.ToolBuilder.ToolManager import ToolManager
from Infrastructure.DataTypes.Contracts.BenchmarkContract import DataGenerators, SyntheticBenchmarkContract, PolicyGenerators
from Infrastructure.Builders.ProcessorBuilder.DataGenerators.SignatureGenerator.SignatureGeneratorContract import Signature
from Infrastructure.DataTypes.Contracts.SubContracts.SyntheticContract import SyntheticExperiment
from Infrastructure.DataTypes.Contracts.SubContracts.TimeBounds import TimeGuarded, TimeGuardingTool
from Infrastructure.DataTypes.Types.custome_type import ExperimentType, BranchOrRelease

from Infrastructure.BenchmarkBuilder.BenchmarkBuilder import BenchmarkBuilder

from Infrastructure.Monitors.MonPoly.MonPoly import MonPoly
from Infrastructure.Monitors.MonitorManager import MonitorManager
from Infrastructure.Monitors.TimelyMon.TimelyMon import TimelyMon
from Infrastructure.Oracles.OracleManager import OracleManager
from Infrastructure.Oracles.VeriMonOracle.VeriMonOracle import VeriMonOracle
from Infrastructure.Parser.ParserTypes import deconstruct_tool_manager


# must be the entry point, either creating or recreating experiments, organizing bootstrapping and so on
# first make a synthetic one work! can hard code the values for now
class Evaluator:
    def __init__(self):
        # setup folders todo generalize
        your_path_to_mfb = "/Users/krq770/PycharmProjects/MonitoringFace"
        path_to_build = f"{your_path_to_mfb}/Infrastructure/build"
        if not os.path.exists(path_to_build):
            os.mkdir(path_to_build)

        path_to_experiments = f"{your_path_to_mfb}/Infrastructure/experiments"
        if not os.path.exists(path_to_experiments):
            os.mkdir(path_to_experiments)

        # read experiment
        # tool builder
        tool_manager = ToolManager([
            ("TimelyMon", "input_optims", BranchOrRelease.Branch),
            ("TimelyMon", "development", BranchOrRelease.Branch),
            ("MonPoly", "master", BranchOrRelease.Branch)
        ], path_to_build)

        # todo get/create and build experiment/case study

        # todo analyze

        # ------- do something to variables -------
        # the benchmark should work over multiple types of creation
        # Synthetic: instruct customizable generators (either single or multiple) to create data given a schema
        #            Including Temporal Data Golf and RV20
        # Case Study: instruct fixed generators to either download data from hosted place or run one setting



        #data_setup = Patterns(
        #    trace_length=1000,seed=None,event_rate=1000,index_rate=None, time_stamp=None,linear=1, interval=None,
        #    star=None,triangle=None,pattern=None,violations=1.0,zipf="x=1.5+3,z=2", prob_a=0.2,  prob_b=0.3, prob_c=0.5
        #)

        data_setup = Signature(
            trace_length=1000, seed=None, event_rate=1000, index_rate=None, time_stamp=None,
            sig="", sample_queue=None, string_length=None, fresh_value_rate=None, domain=None
        )

        """data_setup = DataGolfContract(
            path=path_to_experiments,
            sig_file="signature.sig",
            formula="formula.mfotl",
            tup_ts=[0, 1, 2, 3, 4, 5, 6],
            tup_amt=100,
            tup_val=1,
            oracle=True,
            no_rewrite=None,
            trace_length=5
        )"""

        # rethink practicals, lattice of operations
        # comparing to the fragments

        formula_setup = PolicyGeneratorContract().default_contract()
        formula_setup.num_preds = 4
        formula_setup.prob_eand = None
        formula_setup.prob_rand = None

        synthetic_experiment = SyntheticExperiment(
            num_operators=[5], num_fvs=[2], num_setting=[0, 1], num_data_set_sizes=[50]
        )

        #init = CaseStudyBenchmarkContract("Nokia", DataGenerators.CASESTUDY, "Nokia")
        init = SyntheticBenchmarkContract("test", DataGenerators.DATAGENERATOR, PolicyGenerators.MFOTLGENERATOR, formula_setup)
        #data_setup = {}

        # Store and reload Benchmark: (tools and parameters, experiments) list

        monitor_manager = MonitorManager(
            tool_manager=tool_manager,
            monitors_to_build=[
                ("TimelyMon", "TimelyMon 1", "development", {"worker": 1, "output_mode": 1}),
                ("TimelyMon", "TimelyMon 6", "development", {"worker": 6, "output_mode": 1}),
                ("MonPoly", "MonPoly", "master", {"replayer": "gen_data", "path_to_build": path_to_build}),
                ("MonPoly", "VeriMon", "master", {"replayer": "gen_data", "verified": (), "path_to_build": path_to_build})
            ]
        )

        # todo contract manager
        oracle_manager = OracleManager(
            oracles_to_build=[("VeriMonOracle", "VeriMonOracle", MonPoly, {"replayer": "gen_data", "verified": (), "path_to_build": path_to_build})],
            monitor_manager=monitor_manager
        )

        time_guarded = TimeGuarded(
            time_guarded=False, lower_bound=None, upper_bound=200,
            guard_type=TimeGuardingTool.Monitor, guard=monitor_manager.get_monitor("TimelyMon 6")
        )

        benchmark = BenchmarkBuilder(
            init, path_to_build, path_to_experiments,
            data_setup, synthetic_experiment, ExperimentType.Signature,
            time_guarded, oracle_manager.get_oracle("VeriMonOracle")
        )

        # oracle needs timeout and potential lower bound
        x = benchmark.run(monitor_manager.get_monitors(["TimelyMon 1", "TimelyMon 6", "VeriMon", "MonPoly"]), {})
        print(x)

        # performance
        #   online/offline peak mem and latency    (not there yet)
        #   measure different stages pre/exec/post (ok)

        # correction
        #  conversion to VeriMon for correctness (is the format)
        #  Oracle (implement VeriMon and test datagolf)

        # store and load experiments

        # dejavu/monpoly/timelymon/whymon/enfguard(?)

        # stream rv side quest

        # do analysis


if __name__ == "__main__":
    Evaluator()
