from abc import ABC, abstractmethod
from typing import Tuple

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure


class AbstractComparator(ABC):
    @abstractmethod
    def as_oracle(self, other: AbstractOutputStructure) -> Tuple[bool, str]:
        pass


def time_point_check(oracle: AbstractOutputStructure, other: AbstractOutputStructure) -> Tuple[bool, str]:
    oracle_tps = set(oracle.time_points())
    other_tps = set(other.time_points())

    if oracle_tps != other_tps:
        missing_from_tool = oracle_tps - other_tps
        missing_from_oracle = other_tps - oracle_tps
        if missing_from_tool:
            return False, f"Tool is missing time points from oracle: {missing_from_tool}"
        if missing_from_oracle:
            return False, f"Oracle is missing time points from tool: {missing_from_oracle}"
    return True, "Verified"
