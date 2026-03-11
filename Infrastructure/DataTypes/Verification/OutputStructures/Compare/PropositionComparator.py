from typing import Tuple, Union

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractComparator import AbstractComparator, time_point_check
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.OooVerdicts import OooVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PropositionTree
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts


class PropositionComparator(AbstractComparator):
    def __init__(self, prop):
        self.prop = prop
        pass

    def as_oracle(self, other: AbstractOutputStructure) -> Tuple[bool, str]:
        if isinstance(other, PropositionList):
            return prop_to_prop_comp(self.prop, other)
        elif isinstance(other, OooVerdicts) or isinstance(other, Verdicts):
            return prop_to_verdicts_comp(self.prop, other)
        elif isinstance(other, PropositionTree):
            return prop_to_pdt_comp(self.prop, other)
        else:
            raise Exception(f"Unknown type compare with type {other}")


def prop_to_pdt_comp(oracle: PropositionList, other: PropositionTree) -> Tuple[bool, str]:
    oracle_tps = set(oracle.prop_list.keys())
    other_tps = set(other.tp_to_ts.keys())

    complement = other_tps - oracle_tps
    for c_tp in complement:
        if not other.retrieve(c_tp).is_false_leave():
            return False, f"PropositionTree has verdicts at time point {c_tp}"

    for time_point in oracle_tps:
        tree = other.retrieve(time_point)
        if tree is None:
            return False, f"Time point {time_point} missing in PropositionTree"

        if not tree.is_false_leave():
            return False, f"Time point {time_point} has no satisfaction"
    return True, "Checked"


def prop_to_verdicts_comp(oracle: PropositionList, other: Union[Verdicts, OooVerdicts] ) -> Tuple[bool, str]:
    (verdict, txt) = time_point_check(oracle, other)
    if not verdict:
        return False, txt

    for time_point in oracle.prop_list.keys():
        if other.retrieve(time_point) is None:
            return False, f"Time point {time_point} missing in Verdicts"

    return True, "Checked"


def prop_to_prop_comp(oracle: PropositionList, other: PropositionList) -> Tuple[bool, str]:
    oracle_len = len(oracle.prop_list)
    other_len = len(other.prop_list)

    if oracle_len != other_len:
        return False, f"Length of proposition lists differ! Oracle length: {oracle_len}, Tool length: {other_len}"

    (verdict, txt) = time_point_check(oracle, other)
    if not verdict:
        return False, txt

    for time_point in oracle.time_points():
        oracle_value = oracle.prop_list[time_point]
        other_value = other.prop_list[time_point]

        if oracle_value != other_value:
            return False, f"Value mismatch at time point {time_point}: Oracle value: {oracle_value}, Tool value: {other_value}"

    return True, "Verified"
