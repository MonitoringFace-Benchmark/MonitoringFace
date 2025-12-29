import dataclasses
import os.path
from typing import AnyStr

from Infrastructure.DataTypes.FileRepresenters.ScratchFolderHandler import ScratchFolderHandler
from Infrastructure.Monitors.MonitorExceptions import InstructionMissing, TimedOut
from Infrastructure.Oracles.AbstractOracleTemplate import AbstractOracleTemplate
from Infrastructure.Oracles.OracleExceptions import RunOracleException
from Infrastructure.constants import BENCHMARK_BUILDING_OFFSET


# case studies are a collection of data, formulas and signatures
# a relation mapping data, formula and signature to one experiment and their respective location
# the case study is then conducted by iterating over the results of the mapping, running all tools on it
# the data is added in the form of a folder into the experiment work space
# the mapping describes the relative path from the top level of the case study folder to the files

# the case study Image manager equivalent will get the correct folder within it volumes and is allowed to read and write
# then it will also write the experiment setup list, the paring of data, formula, signature

@dataclasses.dataclass
class CaseStudyContract:
    path: AnyStr


def construct_case_study(data_gen, data_setup, path_to_named_experiment, oracle: AbstractOracleTemplate, time_out):
    data_setup["path"] = path_to_named_experiment
    print(f"{BENCHMARK_BUILDING_OFFSET} Begin: Unpacking Data")
    data_gen.run_generator(data_setup)
    print(f"{BENCHMARK_BUILDING_OFFSET} Finished: Unpacking Data\n")

    named_path_to_data = f"{path_to_named_experiment}/data"

    sfh = ScratchFolderHandler(named_path_to_data)

    mapper = CaseStudyMapper(
        path_to_data=named_path_to_data,
        path_to_instructions=f"{path_to_named_experiment}/instructions.txt"
    )
    data_setup["case_study_mapper"] = mapper

    if oracle:
        result_folder = f"{named_path_to_data}/result"
        os.makedirs(result_folder, exist_ok=True)

        print(f"{BENCHMARK_BUILDING_OFFSET} Begin: Verifying with Oracle")
        num_settings = len(mapper.settings)
        i = 1
        for setting in mapper.iterate_settings():
            print(f"{BENCHMARK_BUILDING_OFFSET} Verifying setting {i}/{num_settings}")
            num, (data_file, formula, sig) = setting
            try:
                oracle.pre_process_data(named_path_to_data, data_file=data_file, formula_file=formula, signature_file=sig)
            except TimedOut:
                raise TimedOut(f"Oracle {oracle} timed out ({time_out} seconds)")

            out, code = oracle.compute_result(None, time_out=time_out)

            if code != 0:
                raise RunOracleException(out)

            with open(f"{result_folder}/result_{num}.res", "w") as file:
                file.write(out)
            i += 1

            sfh.clean_up_folder()
        print(f"{BENCHMARK_BUILDING_OFFSET} Finished: Verifying with Oracle\n")
    sfh.remove_folder()


class CaseStudyMapper:
    def __init__(self, path_to_data, path_to_instructions):
        self.data_path = path_to_data
        self.instruction_path = path_to_instructions
        self.settings = list(enumerate(self._parse_instructions()))

    def iterate_settings(self):
        return self.settings

    def _parse_instructions(self):
        if not os.path.exists(self.instruction_path):
            raise InstructionMissing()

        settings = []
        with open(self.instruction_path, "r") as f:
            for line in f.readlines():
                settings.append([l.split()[0] for l in line.split(",")])
        return settings
