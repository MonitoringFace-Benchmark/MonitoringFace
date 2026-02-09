import os
from abc import abstractmethod, ABC
from enum import Enum
from typing import Optional

from Infrastructure.AutoConversion.InputOutputPolicyFormats import str_to_policy_inout_format
from Infrastructure.AutoConversion.InputOutputTraceFormats import str_to_trace_inout_format
from Infrastructure.Builders.ProcessorBuilder.CaseStudiesGenerators.CaseStudyGenerator import CaseStudyGenerator
from Infrastructure.DataTypes.FileRepresenters.ScratchFolderHandler import ScratchFolderHandler
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.Monitors.AbstractMonitorTemplate import direct_run
from Infrastructure.Oracles.AbstractOracleTemplate import AbstractOracleTemplate
from Infrastructure.constants import TRACE_KEY, POLICY_KEY, VALUE_KEY, PATH_KEY, BENCHMARK_BUILDING_OFFSET, \
    SIGNATURE_KEY
from Infrastructure.DataTypes.Contracts.SubContracts.TimeBounds import TimeConstraints, TimeGuardingTool


class SeedType(Enum):
    RANDOM = 1
    FIXED = 2
    DETERMINISTIC = 3


class Coordinator(ABC):
    @abstractmethod
    def build(self):
        pass

    @abstractmethod
    def run(self):
        pass


class TimedOut(Exception):
    pass


class RunOracleException(Exception):
    pass


class CaseStudyCoordinator(Coordinator):
    def __init__(self, generator: CaseStudyGenerator, data_setup, path_manager: PathManager, guarded: TimeConstraints,
                 oracle: Optional[AbstractOracleTemplate] = None):
        self.generator = generator
        self.data_setup = data_setup
        self.oracle = oracle
        self.guarded = guarded
        self.path_manager = path_manager
        self.results = {}
        self.header, self.instructions = self._init_instr()

    def _init_instr(self):
        with open(self.path_manager.get_path("instructions"), "r") as f:
            raw_instructions = f.readlines()

        header = [h.strip().lower() for h in raw_instructions[0].strip().split(",")]
        for field in {TRACE_KEY, POLICY_KEY}:
            if field not in header:
                raise Exception(f"Mandatory field {field} missing from instructions")

        instructions = []
        for line in raw_instructions[1:]:
            inner_res = dict()
            for (pos, raw_value) in enumerate(line.strip().split(",")):
                raw_value = raw_value.strip()
                if ":" in raw_value:
                    raw_val_type = raw_value.split(":")
                    val = raw_val_type[0].strip()
                    val_type = raw_val_type[1].strip()
                    format_type = str_to_trace_inout_format(val_type) if "data" == header[
                        pos] else str_to_policy_inout_format(val_type)
                    inner_res[VALUE_KEY] = (val, format_type)
                else:
                    inner_res[VALUE_KEY] = (raw_value, None)
            instructions.append(inner_res)
        return header, instructions

    def build(self):
        def _inner_write(folder, n):
            _out_file = f"{folder}/result_{n}.res"
            with open(_out_file, "w") as file_:
                file_.write(out)
            return _out_file

        path_to_named_experiment = self.path_manager.get_path("path_to_named_experiment")
        self.data_setup[PATH_KEY] = path_to_named_experiment
        print(f"{BENCHMARK_BUILDING_OFFSET} Begin: Unpacking Data")
        self.generator.run_generator(self.data_setup)
        print(f"{BENCHMARK_BUILDING_OFFSET} Finished: Unpacking Data\n")

        if self.oracle is None and self.guarded.construction_constraint() is None:
            return

        named_path_to_data = f"{path_to_named_experiment}/data"
        sfh = ScratchFolderHandler(named_path_to_data)
        if self.oracle is not None:
            result_folder = f"{named_path_to_data}/result"
            os.makedirs(result_folder, exist_ok=True)

        construction_constraint = self.guarded.construction_constraint()
        run_time_out = construction_constraint.upper_bound
        if run_time_out is None:
            print("Warning: No upper bound for construction time provided, oracle verification or time guard may run indefinitely!")

        print(f"{BENCHMARK_BUILDING_OFFSET} Begin: Verifying with Oracle")
        for (i, setting) in enumerate(self.instructions):
            print(f"{BENCHMARK_BUILDING_OFFSET} Verifying setting {i + 1}/{len(self.instructions)}")

            (data_file, data_type) = setting[TRACE_KEY]
            (policy_file, policy_type) = setting[POLICY_KEY]
            sig = setting[SIGNATURE_KEY]

            if self.oracle is not None:
                try:
                    # todo redefine call to oracle pipeline, reroute preprocessing
                    self.oracle.pre_process_data(named_path_to_data, data_file=data_file, formula_file=policy_file, signature_file=sig)
                    out, code = self.oracle.compute_result(time_on=None, time_out=run_time_out)
                    if code != 0:
                        raise RunOracleException(out)
                    self.results[i] = _inner_write(result_folder, i)
                except TimedOut:
                    raise TimedOut(f"Oracle {self.oracle} timed out ({run_time_out} seconds)")

            if construction_constraint is not None and construction_constraint.guard_type == TimeGuardingTool.Monitor:
                try:
                    mon = construction_constraint.guard
                    mon.auto_preprocessing(named_path_to_data, data_type, policy_type, data_file, sig, policy_file, self.path_manager, verbose=False)
                    cmd, name = mon.run_offline_command()
                    out, code = mon.image.run(parameters=cmd, path_to_data=sfh.folder, time_on=None, timeout=run_time_out, name=name)
                except TimedOut:
                    raise TimedOut(f"Monitor {self.oracle} timed out ({run_time_out} seconds)")
            sfh.clean_up_folder()
        print(f"{BENCHMARK_BUILDING_OFFSET} Finished: Verifying with Oracle\n")
        sfh.remove_folder()

    def run(self):
        pass
