from Infrastructure.DataTypes.Verification.OutputStructures.AbstractComparator import verdicts_to_prop_list_inner, \
    verdicts_to_verdicts_inner
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Compare.VerdictsComparator import verdicts_to_pdt_inner
from Infrastructure.DataTypes.Verification.OutputStructures.Strength import Comparison
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.OooVerdicts import OooVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PropositionTree
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts


def as_oracle(verdict: OooVerdicts, other: AbstractOutputStructure) -> Comparison:
    if isinstance(other, Verdicts):
        return ooo_verdicts_to_verdicts_comp(verdict, other)
    elif isinstance(other, OooVerdicts):
        return ooo_verdicts_to_ooo_verdicts_comp(verdict, other)
    elif isinstance(other, PropositionTree):
        return ooo_verdicts_to_proposition_tree_comp(verdict, other)
    elif isinstance(other, PropositionList):
        return ooo_verdicts_to_proposition_list_comp(verdict, other)
    else:
        raise Exception(f"Unknown type compare with type {other}")


def ooo_verdicts_to_ooo_verdicts_comp(oracle: OooVerdicts, other: OooVerdicts) -> Comparison:
    return verdicts_to_verdicts_inner(oracle, other)


def ooo_verdicts_to_verdicts_comp(oracle: OooVerdicts, other: Verdicts) -> Comparison:
    return verdicts_to_verdicts_inner(oracle, other)


def ooo_verdicts_to_proposition_list_comp(oracle: OooVerdicts, other: PropositionList) -> Comparison:
    return verdicts_to_prop_list_inner(oracle, other)


def ooo_verdicts_to_proposition_tree_comp(oracle: OooVerdicts, other: PropositionTree) -> Comparison:
    return verdicts_to_pdt_inner(oracle, other)
