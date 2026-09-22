from typing import Union

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractComparator import time_point_check, \
    time_point_pdt_check, prop_list_to_verdicts_inner
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Strength import Comparison, Strength
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.OooVerdicts import OooVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PropositionTree
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts


def as_oracle(prop: PropositionList, other: AbstractOutputStructure) -> Comparison:
    if isinstance(other, PropositionList):
        return prop_to_prop_comp(prop, other)
    elif isinstance(other, OooVerdicts) or isinstance(other, Verdicts):
        return prop_to_verdicts_comp(prop, other)
    elif isinstance(other, PropositionTree):
        return prop_to_pdt_comp(prop, other)
    else:
        raise Exception(f"Unknown type compare with type {other}")


def prop_to_pdt_comp(oracle: PropositionList, other: PropositionTree) -> Comparison:
    strength = Strength.CONSISTENT
    ok, txt = time_point_pdt_check(oracle, other)
    if not ok:
        return Comparison(False, txt, strength)

    time_points = 0
    values = 0
    for time_point in sorted(oracle.time_points().keys()):
        tree = other.retrieve(time_point)
        if tree is None:
            return Comparison(False, f"Time point {time_point} missing in PropositionTree",
                              strength, time_points, values)
        time_points += 1
        values += 1
        if tree.is_false_leave():
            return Comparison(False, f"Time point {time_point} has no satisfaction",
                              strength, time_points, values)
    return Comparison(True, "Checked", strength, time_points, values)


def prop_to_verdicts_comp(oracle: PropositionList, other: Union[Verdicts, OooVerdicts]) -> Comparison:
    return prop_list_to_verdicts_inner(oracle, other)


def prop_to_prop_comp(oracle: PropositionList, other: PropositionList) -> Comparison:
    strength = Strength.EQUIVALENT
    oracle_len = len(oracle.prop_list)
    other_len = len(other.prop_list)

    if oracle_len != other_len:
        return Comparison(
            False,
            f"Length of proposition lists differ! Oracle length: {oracle_len}, Tool length: {other_len}",
            strength)

    ok, txt = time_point_check(oracle, other)
    if not ok:
        return Comparison(False, txt, strength)

    time_points = 0
    values = 0
    for time_point in sorted(oracle.time_points().keys()):
        oracle_value = oracle.prop_list[time_point]
        other_value = other.prop_list[time_point]

        time_points += 1
        values += 1
        if oracle_value != other_value:
            return Comparison(
                False,
                f"Value mismatch at time point {time_point}: Oracle value: {oracle_value}, Tool value: {other_value}",
                strength, time_points, values)
    return Comparison(True, "Verified", strength, time_points, values)
