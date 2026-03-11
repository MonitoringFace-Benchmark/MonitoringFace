from typing import Tuple

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractComparator import AbstractComparator, time_point_check
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.OooVerdicts import OooVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PropositionTree
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts


class VerdictsComparator(AbstractComparator):
    def __init__(self, verdict: Verdicts):
        self.verdict = verdict

    def as_oracle(self, other: AbstractOutputStructure) -> Tuple[bool, str]:
        if isinstance(other, Verdicts):
            return verdicts_to_verdicts_comp(self.verdict, other)
        elif isinstance(other, OooVerdicts):
            return verdicts_to_oooverdicts_comp(self.verdict, other)
        elif isinstance(other, PropositionTree):
            pass
        elif isinstance(other, PropositionList):
            pass
        else:
            raise Exception(f"Unknown type compare with type {other}")


def verdicts_to_verdicts_comp(oracle: Verdicts, other: Verdicts) -> Tuple[bool, str]:
    (verdict, txt) = time_point_check(oracle, other)
    if not verdict:
        return False, txt

    oracle_len = len(oracle.verdict)
    other_len = len(other.verdict)

    if oracle_len != other_len:
        return False, f"Verdict lengths differ! Oracle length: {oracle_len}, Tool length: {other_len}"

    for (oracle_val, tuple_val) in zip(oracle.verdict, other.verdict):
        s_oracle = sorted(oracle_val)
        s_tuple = sorted(tuple_val)

        if oracle_val != tuple_val:
            return False, f"Verdict values differ at time point {oracle_val.tp} =>\nOracle {s_oracle}\nTool {s_tuple}"
    return True, "Verified"


def verdicts_to_oooverdicts_comp(oracle: Verdicts, other: OooVerdicts) -> Tuple[bool, str]:
    (verdict, txt) = time_point_check(oracle, other)
    if not verdict:
        return False, txt

    for time_point in oracle.time_points():
        other_val = other.retrieve(time_point)
        oracle_val = oracle.retrieve(time_point)
        s_oracle = sorted(oracle_val)
        s_tuple = sorted(other_val)

        if oracle_val != other_val:
            return False, f"Verdict values differ at time point {oracle_val.tp} =>\nOracle {s_oracle}\nTool {s_tuple}"
    return True, "Verified"


def verdicts_to_proposition_list_comp(oracle: Verdicts, other: PropositionList) -> Tuple[bool, str]:
    (verdict, txt) = time_point_check(oracle, other)
    if not verdict:
        return False, txt

    for time_point in oracle.time_points():
        other_val = other.retrieve(time_point)
        oracle_val = oracle.retrieve(time_point)

        if other_val is None:
            return False, f"Proposition list missing output at time point {oracle_val.tp}"
    return True, "Verified"
