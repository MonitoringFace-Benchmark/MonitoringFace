from Infrastructure.DataTypes.Verification.OutputStructures.AbstractComparator import verdicts_to_proposition_tree, time_point_pdt_check, verdicts_to_verdicts_inner, \
    verdicts_to_prop_list_inner
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.PDTHelper import equality_between_pdts
from Infrastructure.DataTypes.Verification.OutputStructures.Strength import Comparison, Strength
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.OooVerdicts import OooVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PropositionTree
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts


def as_oracle(verdict: Verdicts, other: AbstractOutputStructure) -> Comparison:
    if isinstance(other, Verdicts):
        return verdicts_to_verdicts_comp(verdict, other)
    elif isinstance(other, OooVerdicts):
        return verdicts_to_ooo_verdicts_comp(verdict, other)
    elif isinstance(other, PropositionTree):
        return verdicts_to_proposition_tree_comp(verdict, other)
    elif isinstance(other, PropositionList):
        return verdicts_to_proposition_list_comp(verdict, other)
    else:
        raise Exception(f"Unknown type compare with type {other}")


def verdicts_to_verdicts_comp(oracle: Verdicts, other: Verdicts) -> Comparison:
    oracle_len = oracle.entry_count()
    other_len = other.entry_count()
    if oracle_len != other_len:
        return Comparison(
            False,
            f"Verdict lengths differ! Oracle length: {oracle_len}, Tool length: {other_len}",
            Strength.EQUIVALENT)
    return verdicts_to_verdicts_inner(oracle, other)


def verdicts_to_ooo_verdicts_comp(oracle: Verdicts, other: OooVerdicts) -> Comparison:
    return verdicts_to_verdicts_inner(oracle, other)


def verdicts_to_proposition_list_comp(oracle: Verdicts, other: PropositionList) -> Comparison:
    return verdicts_to_prop_list_inner(oracle, other)


def verdicts_to_proposition_tree_comp(oracle: Verdicts, other: PropositionTree) -> Comparison:
    return verdicts_to_pdt_inner(oracle, other)


def verdicts_to_pdt_inner(oracle, other: PropositionTree) -> Comparison:
    strength = Strength.EQUIVALENT
    ok, txt = time_point_pdt_check(oracle, other)
    if not ok:
        return Comparison(False, txt, strength)

    oracle_pdt = verdicts_to_proposition_tree(oracle, other.variable_order)
    time_points = 0
    values = 0
    for tp in sorted(oracle.time_points().keys()):
        other_tree = other.forest.get(tp)
        if other_tree is None:
            return Comparison(False, f"Tool is missing PDT at time point {tp}",
                              strength, time_points, values)
        time_points += 1
        values += 1
        if not equality_between_pdts(oracle_pdt.retrieve_order(), oracle_pdt.forest[tp], other_tree):
            return Comparison(False, f"Structures are not equivalent at time point {tp}",
                              strength, time_points, values)
    return Comparison(True, "Verified", strength, time_points, values)
