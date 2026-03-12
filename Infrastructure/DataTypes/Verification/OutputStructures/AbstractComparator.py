from abc import ABC, abstractmethod
from typing import Tuple, List

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PDTLeaf, PDTComplementSet, PDTSet, PDTNode, PropositionTree, PDTTree
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.Assignment import Assignment
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.Proposition import Proposition
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrdering


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


def time_point_pdt_check(oracle: AbstractOutputStructure, other: AbstractOutputStructure) -> Tuple[bool, str]:
    oracle_tps = set(oracle.time_points())
    other_tps = set(other.time_points())

    complement = other_tps - oracle_tps
    for c_tp in complement:
        if not other.retrieve(c_tp).is_false_leave():
            return False, f"PropositionTree has verdicts at time point {c_tp}"
    return True, "Verified"


def verdicts_to_proposition_tree(verdicts: Verdicts, new_order: VariableOrdering):
    pdt = PropositionTree(new_order)
    return to_tree_inner(verdicts.verdict, pdt)


def ooo_verdicts_to_proposition_tree(ooo_verdicts: Verdicts, new_order: VariableOrdering):
    values = []
    for tp in sorted(ooo_verdicts.tp_to_ts.keys()):
        values.append([
            ooo_verdicts.tp_to_ts[tp],
            tp,
            [val for (val_tp, val_ts, vals) in ooo_verdicts.ooo_verdict if tp == val_tp for val in vals]
        ])

    pdt = PropositionTree(new_order)
    return to_tree_inner(values, pdt)


def to_tree_inner(values, pdt: PropositionTree):
    for (ts, tp, val) in values:
        pdt.tp_to_ts[tp] = ts
        if isinstance(val, Proposition):
            pdt.forest[tp] = PDTTree(PDTLeaf(value=val.value))
        else:
            assignments = list(map(lambda ass: ass.retrieve_order(new_order=pdt.retrieve_order()), val))
            pdt.forest[tp] = PDTTree(_pdt_subtree_recurse(vars_=pdt.retrieve_order(), assignments=assignments))
    return pdt


def _pdt_subtree_recurse(vars_: List[str], assignments: List[Assignment]):
    if not vars_:
        return PDTLeaf(len(assignments) > 0)

    var_ = vars_[0]
    remaining = vars_[1:]

    value_to_assignments = {}
    for assignment in assignments:
        val = assignment.retrieve_value(var_)
        if val not in value_to_assignments:
            value_to_assignments[val] = []
        value_to_assignments[val].append(assignment)

    choices = []
    for elem, matching in value_to_assignments.items():
        subtree = _pdt_subtree_recurse(remaining, matching)
        choices.append((PDTSet({elem}), subtree))

    choices.append((PDTComplementSet(set(value_to_assignments.keys())), PDTLeaf(False)))
    return PDTNode(var_, choices)
