import re
from pathlib import Path
from typing import AnyStr, Optional, Tuple

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Compare.Comparing import comparing
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.DatagolfVerdicts import DatagolfVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import DefaultVariableOrder, VariableOrder
from Infrastructure.Oracles.AbstractOracleTemplate import AbstractOracleTemplate


class DataGolfOracle(AbstractOracleTemplate):
    def pre_process_data(self, path_to_folder: AnyStr, data_file: AnyStr, signature_file: AnyStr, formula_file: AnyStr):
        pass

    def compute_result(self, time_on=None, time_out=None) -> Tuple[AnyStr, int]:
        pass

    def post_process_data(self, std_out_str, output_file_name):
        pass

    def verify(self, path_to_result_folder: AnyStr, data_file: AnyStr, tool_verdicts: AbstractOutputStructure) -> bool:
        oracle_verdicts = get_oracle_verdicts(path_to_result_folder, data_file)
        return comparing(oracle_verdicts, tool_verdicts)


def get_oracle_verdicts(path_to_result_folder, data_file) -> AbstractOutputStructure:
    data_file_size = extract_data_number(data_file)
    prefix = path_to_result_folder + f"/prefix_{data_file_size}"
    result = path_to_result_folder + f"/result_{data_file_size}.res"

    if Path(prefix).exists() and Path(result).exists():
        with open(result, "r") as f:
            output = f.read()

        lines = [ln for ln in (l.rstrip() for l in output.splitlines()) if ln != ""]
        variable_order = VariableOrder(lines[0].strip().split(","))
        verdicts = DatagolfVerdicts(variable_order)

        current_ts = None
        time_point_counter = 0
        for line in lines[1:]:
            if line.startswith("@"):
                m = re.match(r"^@\s*(\d+)", line)
                current_ts = int(m.group(1)) if m else None
                continue

            if line.startswith('pos'):
                verdicts.insert_positive_verdict(_parse_assignment_values(line), time_point_counter, current_ts)
            else:
                verdicts.insert_negative_verdict(_parse_assignment_values(line), time_point_counter, current_ts)
        return verdicts
    else:
        return DatagolfVerdicts(variable_order=DefaultVariableOrder())


def extract_data_number(path: str) -> Optional[int]:
    m = re.compile(r"^data_(\d+)\.csv$", re.IGNORECASE).match(Path(path).name)
    return int(m.group(1)) if m else None


def _parse_assignment_values(line: str):
    s = line.strip()
    if s.endswith(";"):
        s = s[:-1].rstrip()

    prefix_match = re.match(r"^\s*(pos|neg)\b[:\s-]*", s, re.IGNORECASE)
    if prefix_match:
        s = s[prefix_match.end():].lstrip()

    return [[num.strip() for num in tup.split(',') if num.strip()] for tup in re.findall(r"\(([^)]*)\)", s)]
