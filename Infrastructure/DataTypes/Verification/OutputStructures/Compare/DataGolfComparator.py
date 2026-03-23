from typing import Tuple, Union

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.DatagolfVerdicts import DatagolfVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.OooVerdicts import OooVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PropositionTree
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts


def as_oracle(oracle: DatagolfVerdicts, other: AbstractOutputStructure) -> Tuple[bool, str]:
    if isinstance(other, OooVerdicts) or isinstance(other, Verdicts):
        return datagolf_to_verdicts_comp(oracle, other)
    elif isinstance(other, PropositionList):
        return datagolf_to_prop_comp(oracle, other)
    elif isinstance(other, PropositionTree):
        return datagolf_to_pdt_comp(oracle, other)
    else:
        raise Exception(f"Unknown type compare with type {other}")


def datagolf_to_verdicts_comp(oracle: DatagolfVerdicts, other: Union[Verdicts, OooVerdicts]) -> Tuple[bool, str]:
    for time_point in sorted(oracle.time_points().keys()):
        pos = oracle.retrieve_positive_verdict(time_point)[2]
        neg = oracle.retrieve_negative_verdict(time_point)[2]

        other_pos = other.retrieve(time_point)
        if other_pos is None:
            return False, f"Time point {time_point} missing"

        other_v = other_pos[2]
        for v in pos:
            if v not in other_v:
                return False, f"Positive verdict {v} at time point {time_point} missing"

        for v in neg:
            if v in other_v:
                return False, f"Negative verdict {v} at time point {time_point} present"
    return True, "Checked"


def datagolf_to_prop_comp(oracle: DatagolfVerdicts, other: PropositionList) -> Tuple[bool, str]:
    return False, "Closed Formulas are not supported"


def datagolf_to_pdt_comp(oracle: DatagolfVerdicts, other: PropositionTree) -> Tuple[bool, str]:
    for time_point in oracle.time_points().keys():
        pos = oracle.retrieve_positive_verdict(time_point)
        neg = oracle.retrieve_negative_verdict(time_point)

        other = other.retrieve(time_point)
        if other is None:
            return False, f"Time point {time_point} missing"

        for v in pos:
            if v not in other.check_assignment(v):
                return False, f"Positive verdict {v} at time point {time_point} missing"

        for v in neg:
            if v in other.check_assignment(v):
                return False, f"Negative verdict {v} at time point {time_point} present"
    return True, "Checked"

