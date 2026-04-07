from typing import Tuple

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractComparator import time_point_pdt_pdt_check, pdt_to_verdicts_inner, time_point_pdt_check
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.PDTHelper import equality_between_pdts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.OooVerdicts import OooVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PropositionTree
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts


def as_oracle(pdt: PropositionTree, other: AbstractOutputStructure) -> Tuple[bool, str]:
    if isinstance(other, PropositionTree):
        return pdt_to_pdt_comp(pdt, other)
    elif isinstance(other, OooVerdicts):
        return pdt_to_ooo_verdicts_comp(pdt, other)
    elif isinstance(other, Verdicts):
        return pdt_to_verdicts_comp(pdt, other)
    elif isinstance(other, PropositionList):
        return pdt_to_prop_comp(pdt, other)
    else:
        raise Exception(f"Unknown type compare with type {other}")


def pdt_to_pdt_comp(oracle: PropositionTree, other: PropositionTree) -> Tuple[bool, str]:
    verdict, txt = time_point_pdt_pdt_check(oracle, other)
    if not verdict: return False, txt

    for oracle_tp in oracle.time_points():
        oracle_pdt = oracle.retrieve(oracle_tp)
        other_pdt = other.retrieve(oracle_tp)
        if other_pdt is None and oracle_pdt is None:
            continue
        elif other_pdt is None and oracle_pdt is not None:
            return False, f"Tool is missing PDT at time point {oracle_tp}"
        elif other_pdt is not None and oracle_pdt is None:
            return False, f"Tool has additional PDT at time point {oracle_tp}"
        try:
            if not equality_between_pdts(len(oracle_pdt.terms), oracle_pdt, other_pdt):
                return False, "Structures are not equivalent"
        except Exception as e: return False, str(e)
    return True, "Verified: Structures are equivalent"


def pdt_to_verdicts_comp(oracle: PropositionTree, other: Verdicts) -> Tuple[bool, str]:
    return pdt_to_verdicts_inner(oracle, other)


def pdt_to_ooo_verdicts_comp(oracle: PropositionTree, other: OooVerdicts) -> Tuple[bool, str]:
    return pdt_to_verdicts_inner(oracle, other)


def pdt_to_prop_comp(oracle: PropositionTree, other: PropositionList) -> Tuple[bool, str]:
    verdict, txt = time_point_pdt_check(oracle, other)
    if not verdict: return False, txt

    intersection_set = set(oracle.time_points().keys()) & set(other.time_points().keys())
    for tp in intersection_set:
        oracle_pdt = oracle.retrieve(tp)
        other_prop = other.retrieve(tp)
        if other_prop is None and oracle_pdt is None:
            continue
        elif other_prop is None and oracle_pdt is not None:
            return False, f"Tool is missing PDT at time point {tp}"
        if oracle_pdt.is_false_leave():
            return False, f"Tool has additional PDT at time point {tp}"

    return True, "Check: Tool output is a subset"
