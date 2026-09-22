from typing import Union

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Strength import Comparison, Strength
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.DatagolfVerdicts import DatagolfVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.OooVerdicts import OooVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PropositionTree
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts


def as_oracle(oracle: DatagolfVerdicts, other: AbstractOutputStructure) -> Comparison:
    if isinstance(other, OooVerdicts) or isinstance(other, Verdicts):
        return datagolf_to_verdicts_comp(oracle, other)
    elif isinstance(other, PropositionList):
        return datagolf_to_prop_comp(oracle, other)
    elif isinstance(other, PropositionTree):
        return datagolf_to_pdt_comp(oracle, other)
    else:
        raise Exception(f"Unknown type compare with type {other}")


def datagolf_to_verdicts_comp(oracle: DatagolfVerdicts, other: Union[Verdicts, OooVerdicts]) -> Comparison:
    strength = Strength.CONSISTENT
    time_points = 0
    values = 0
    for time_point in sorted(oracle.time_points().keys()):
        pos = oracle.pos_verdicts.get(time_point, [])
        neg = oracle.neg_verdicts.get(time_point, [])

        other_pos = other.retrieve(time_point)
        if other_pos is None:
            return Comparison(False, f"Time point {time_point} missing",
                              strength, time_points, values)

        other_v = other_pos[2]
        time_points += 1
        for v in pos:
            values += 1
            if v not in other_v:
                return Comparison(False, f"Positive verdict {v} at time point {time_point} missing",
                                  strength, time_points, values)

        for v in neg:
            values += 1
            if v in other_v:
                return Comparison(False, f"Negative verdict {v} at time point {time_point} present",
                                  strength, time_points, values)
    return Comparison(True, "Checked", strength, time_points, values)


def datagolf_to_prop_comp(oracle: DatagolfVerdicts, other: PropositionList) -> Comparison:
    return Comparison(False, "Closed Formulas are not supported", Strength.UNSUPPORTED)


def datagolf_to_pdt_comp(oracle: DatagolfVerdicts, other: PropositionTree) -> Comparison:
    strength = Strength.CONSISTENT
    time_points = 0
    values = 0
    for time_point in sorted(oracle.time_points().keys()):
        pos = oracle.pos_verdicts.get(time_point, [])
        neg = oracle.neg_verdicts.get(time_point, [])

        tree = other.retrieve(time_point)
        if tree is None:
            return Comparison(False, f"Time point {time_point} missing",
                              strength, time_points, values)

        time_points += 1
        for v in pos:
            values += 1
            if not tree.check_assignment(v):
                return Comparison(False, f"Positive verdict {v} at time point {time_point} missing",
                                  strength, time_points, values)

        for v in neg:
            values += 1
            if tree.check_assignment(v):
                return Comparison(False, f"Negative verdict {v} at time point {time_point} present",
                                  strength, time_points, values)
    return Comparison(True, "Checked", strength, time_points, values)
