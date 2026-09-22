from Infrastructure.DataTypes.Verification.OutputStructures.AbstractComparator import time_point_pdt_pdt_check, pdt_to_verdicts_inner, time_point_pdt_check
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.PDTHelper import equality_between_pdts
from Infrastructure.DataTypes.Verification.OutputStructures.Strength import Comparison, Strength
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.OooVerdicts import OooVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PropositionTree
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts


def as_oracle(pdt: PropositionTree, other: AbstractOutputStructure) -> Comparison:
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


def pdt_to_pdt_comp(oracle: PropositionTree, other: PropositionTree) -> Comparison:
    strength = Strength.EQUIVALENT
    ok, txt = time_point_pdt_pdt_check(oracle, other)
    if not ok:
        return Comparison(False, txt, strength)

    time_points = 0
    values = 0
    for oracle_tp in sorted(oracle.time_points()):
        oracle_pdt = oracle.retrieve(oracle_tp)
        other_pdt = other.retrieve(oracle_tp)
        if other_pdt is None and oracle_pdt is None:
            continue
        elif other_pdt is None and oracle_pdt is not None:
            return Comparison(False, f"Tool is missing PDT at time point {oracle_tp}",
                              strength, time_points, values)
        elif other_pdt is not None and oracle_pdt is None:
            return Comparison(False, f"Tool has additional PDT at time point {oracle_tp}",
                              strength, time_points, values)

        time_points += 1
        values += 1
        if not equality_between_pdts(oracle_pdt.terms, oracle_pdt, other_pdt):
            return Comparison(False, f"Structures are not equivalent at time point {oracle_tp}",
                              strength, time_points, values)
    return Comparison(True, "Structures are equivalent", strength, time_points, values)


def pdt_to_verdicts_comp(oracle: PropositionTree, other: Verdicts) -> Comparison:
    return pdt_to_verdicts_inner(oracle, other)


def pdt_to_ooo_verdicts_comp(oracle: PropositionTree, other: OooVerdicts) -> Comparison:
    return pdt_to_verdicts_inner(oracle, other)


def pdt_to_prop_comp(oracle: PropositionTree, other: PropositionList) -> Comparison:
    strength = Strength.CONSISTENT
    ok, txt = time_point_pdt_check(oracle, other)
    if not ok:
        return Comparison(False, txt, strength)

    intersection_set = set(oracle.time_points().keys()) & set(other.time_points().keys())
    time_points = 0
    values = 0
    for tp in sorted(intersection_set):
        oracle_pdt = oracle.retrieve(tp)
        other_prop = other.prop_list.get(tp)
        if other_prop is None and oracle_pdt is None:
            continue
        elif other_prop is None and oracle_pdt is not None:
            return Comparison(False, f"Tool is missing PDT at time point {tp}",
                              strength, time_points, values)
        elif other_prop is not None and oracle_pdt is None:
            return Comparison(False, f"Oracle has no tree at time point {tp}",
                              strength, time_points, values)

        time_points += 1
        values += 1
        if oracle_pdt.is_false_leave():
            return Comparison(False, f"Tool has additional PDT at time point {tp}",
                              strength, time_points, values)
    return Comparison(True, "Tool output is a subset", strength, time_points, values)
