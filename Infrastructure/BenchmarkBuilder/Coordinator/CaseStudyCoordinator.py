import os
from typing import Optional, List, Tuple, Dict

from Infrastructure.AutoConversion.InputOutputPolicyFormats import str_to_policy_inout_format, InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import str_to_trace_inout_format, InputOutputTraceFormats
from Infrastructure.BenchmarkBuilder.Coordinator.Coordinator import Coordinator
from Infrastructure.Builders.ProcessorBuilder.CaseStudiesGenerators.CaseStudyGenerator import CaseStudyGenerator
from Infrastructure.DataTypes.FileRepresenters.ScratchFolderHandler import ScratchFolderHandler
from Infrastructure.DataTypes.FingerPrint.FingerPrint import data_class_to_finger_print
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.Oracles.AbstractOracleTemplate import AbstractOracleTemplate
from Infrastructure.constants import TRACE_KEY, POLICY_KEY, VALUE_KEY, PATH_KEY, BENCHMARK_BUILDING_OFFSET, \
    SIGNATURE_KEY, FINGERPRINT_EXPERIMENT, FINGERPRINT_DATA
from Infrastructure.DataTypes.Contracts.SubContracts.TimeBounds import TimeConstraints, TimeGuardingTool


class TimedOut(Exception):
    pass


class RunOracleException(Exception):
    pass


class CaseStudyCoordinator(Coordinator):
    def __init__(self, generator: CaseStudyGenerator, data_setup, path_manager: PathManager, constraints: TimeConstraints,
                 oracle: Optional[AbstractOracleTemplate] = None):
        self.generator = generator
        self.data_setup = data_setup
        self.oracle = oracle
        self.constraints = constraints
        self.path_manager = path_manager
        self.results = {}
        self.header, self.instructions = self._init_instr()

    def finger_print(self) -> Dict[str, str]:
        new_data_setup_fingerprint = data_class_to_finger_print(self.data_setup)
        new_experiment_fingerprint = self.generator.name
        return {FINGERPRINT_EXPERIMENT: new_experiment_fingerprint, FINGERPRINT_DATA: new_data_setup_fingerprint}

    def time_out(self) -> Optional[int]:
        constraint = self.constraints.runtime_constraint()
        if constraint is not None:
            return constraint.upper_bound
        return None

    def _init_instr(self):
        with open(self.path_manager.get_path("instructions"), "r") as f:
            raw_instructions = f.readlines()

        header = [h.strip().lower() for h in raw_instructions[0].strip().split(",")]
        for field in {TRACE_KEY, POLICY_KEY}:
            if field not in header:
                raise Exception(f"Mandatory field {field} missing from instructions")

        instructions = []
        for (i, line) in enumerate(raw_instructions[1:]):
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

        if self.oracle is None and self.constraints.construction_constraint() is None:
            return

        named_path_to_data = f"{path_to_named_experiment}/data"
        self.path_manager.add_path("named_path_to_data", named_path_to_data)
        sfh = ScratchFolderHandler(named_path_to_data)

        result_folder = f"{named_path_to_data}/result"
        os.makedirs(result_folder, exist_ok=True)

        construction_constraint = self.constraints.construction_constraint()
        run_time_out = construction_constraint.upper_bound
        if run_time_out is None:
            print("Warning: No upper bound for construction time provided, oracle verification or time guard may run indefinitely!")

        print(f"{BENCHMARK_BUILDING_OFFSET} Begin: Verifying with Oracle")
        for (i, setting) in enumerate(self.instructions):
            print(f"{BENCHMARK_BUILDING_OFFSET} Verifying setting {i + 1}/{len(self.instructions)}")

            (data_file, data_type) = setting[TRACE_KEY]
            (policy_file, policy_type) = setting[POLICY_KEY]
            sig = setting.get(SIGNATURE_KEY, None)

            if self.oracle is not None:
                try:
                    self.oracle.pre_process_data(
                        named_path_to_data, data_type, policy_type, data_file, sig, policy_file, self.path_manager
                    )
                    out, code = self.oracle.compute_result(time_on=None, time_out=run_time_out)
                    if code != 0:
                        raise RunOracleException(out)
                    self.results[i] = _inner_write(result_folder, i)
                except TimedOut:
                    raise TimedOut(f"Oracle {self.oracle} timed out ({run_time_out} seconds)")

            if construction_constraint is not None and construction_constraint.guard_type == TimeGuardingTool.Monitor:
                try:
                    mon = construction_constraint.guard
                    mon.preprocessing(
                        named_path_to_data, data_type, policy_type, data_file, sig, policy_file,
                        self.path_manager, verbose=False
                    )
                    cmd, name = mon.run_offline_command()
                    out, code = mon.image.run(
                        parameters=cmd, path_to_data=sfh.folder, time_on=None, timeout=run_time_out, name=name
                    )
                except TimedOut:
                    raise TimedOut(f"Monitor {self.oracle} timed out ({run_time_out} seconds)")
            sfh.clean_up_folder()
        print(f"{BENCHMARK_BUILDING_OFFSET} Finished: Verifying with Oracle\n")
        sfh.remove_folder()

    def iterate_settings(self) -> List[Tuple[int, str, InputOutputTraceFormats, str, InputOutputPolicyFormats, Optional[str], Optional[str]]]:
        res = []
        path_to_data = self.path_manager.get_path("named_path_to_data")
        for (i, setting) in enumerate(self.instructions):
            (data_file, data_type) = setting[TRACE_KEY]
            (policy_file, policy_type) = setting[POLICY_KEY]
            sig = setting.get(SIGNATURE_KEY, None)
            result = self.results.get(i, None)
            res.append((i, path_to_data, data_file, data_type, policy_file, policy_type, sig, result))
        return res

    def short_cutting(self):
        pass
