import os.path

from Infrastructure.Builders.ToolBuilder.ToolManager import ToolManager
from Infrastructure.DataTypes.Contracts.BenchmarkContract import DataGenerators, CaseStudyBenchmarkContract, \
    SyntheticBenchmarkContract, PolicyGenerators
from Infrastructure.DataTypes.Contracts.SubContracts.DataGeneratorContract import Signature
from Infrastructure.DataTypes.Contracts.SubContracts.PolicyGeneratorContract import PolicyGeneratorContract
from Infrastructure.DataTypes.Contracts.SubContracts.SyntheticContract import SyntheticExperiment
from Infrastructure.DataTypes.Contracts.SubContracts.TimeBounds import TimeGuarded, TimeGuardingTool
from Infrastructure.DataTypes.Types.custome_type import GeneratorMode, BranchOrRelease

from Infrastructure.BenchmarkBuilder.BenchmarkBuilder import BenchmarkBuilder

from Infrastructure.Monitors.MonPoly import MonPoly
from Infrastructure.Monitors.TimelyMon import TimelyMon
from Infrastructure.Oracles.VeriMonOracle import VeriMonOracle


# must be the entry point, either creating or recreating experiments, organizing bootstrapping and so on
# first make a synthetic one work! can hard code the values for now
class Evaluator:

    def __init__(self):
        # very important directional values
        your_path_to_mfb = "/Users/krq770/PycharmProjects/MonitoringFace"
        path_to_build = f"{your_path_to_mfb}/Infrastructure/build"
        if not os.path.exists(path_to_build):
            os.mkdir(path_to_build)
            os.mkdir(f"{path_to_build}/Monitor")

        path_to_experiments = f"{your_path_to_mfb}/Infrastructure/experiments"
        if not os.path.exists(path_to_experiments):
            os.mkdir(path_to_experiments)

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

        formula_setup = PolicyGeneratorContract()
        formula_setup.num_preds = 4
        formula_setup.prob_eand = None
        formula_setup.prob_rand = None

        synthetic_experiment = SyntheticExperiment(num_operators=[5],
                                                   num_fvs=[2],
                                                   num_setting=[0, 1],
                                                   num_data_set_sizes=[50])

        #init = CaseStudyBenchmarkContract("Nokia", DataGenerators.CASESTUDY, "Nokia")
        init = SyntheticBenchmarkContract("test", DataGenerators.DATAGENERATOR, PolicyGenerators.MFOTLGENERATOR, formula_setup)
        #data_setup = {}

        # Store and reload Benchmark: (tools and parameters, experiments) list

        d = {"worker": 6, "output_mode": 1}
        tm6 = TimelyMon(tool_manager.get_image("TimelyMon", "development"), "TimelyMon 6", d)

        time_guarded = TimeGuarded(time_guarded=False, lower_bound=None, upper_bound=200,
                                   guard_type=TimeGuardingTool.Monitor, guard=tm6)
        oracle = VeriMonOracle(MonPoly(tool_manager.get_image("MonPoly", "master"), "oracle",
                                        {"replayer": "gen_data", "path_to_build": path_to_build}), {})
        #oracle = DataGolfOracle()
        benchmark = BenchmarkBuilder(init, path_to_build, path_to_experiments,
                                     data_setup, synthetic_experiment, GeneratorMode.Signature, time_guarded, oracle)

        d = {"worker": 1, "output_mode": 1}
        tm = TimelyMon(tool_manager.get_image("TimelyMon", "development"), "TimelyMon 1", d)

        d = {"replayer": "gen_data", "path_to_build": path_to_build}
        mp = MonPoly(tool_manager.get_image("MonPoly", "master"), "MonPoly", d)

        d = {"replayer": "gen_data", "verified": (), "path_to_build": path_to_build}
        vm = MonPoly(tool_manager.get_image("MonPoly", "master"), "VeriMon", d)

        # oracle needs timeout and potential lower bound

        x = benchmark.run([tm, tm6, mp, vm], {})
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
