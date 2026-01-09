from typing import List, Union, Tuple

from Infrastructure.DataTypes.Verification.OutputStructures.Structures.OooVerdicts import OooVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PDTLeaf, PDTComplementSet, PDTSet, PDTNode, PropositionTree, PDTTree
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.Assignment import Assignment
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.Proposition import Proposition
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrdering


class IntermediateList:
    def __init__(self, values, variable_ordering: VariableOrdering):
        self.values: list[Tuple[int, int, Union[list[Assignment], Proposition]]] = values
        self.variable_ordering = variable_ordering

    @classmethod
    def from_OOOVerdicts(cls, ooo_verdicts: OooVerdicts):
        values = []
        for tp in sorted(ooo_verdicts.tp_to_ts.keys()):
            values.append([
                ooo_verdicts.tp_to_ts[tp],
                tp,
                [val for (val_tp, val_ts, vals) in ooo_verdicts.ooo_verdict if tp == val_tp for val in vals]
            ])
        return cls(values, ooo_verdicts.variable_order)

    @classmethod
    def from_Verdicts(cls, verdicts: Verdicts):
        return cls(verdicts.verdict, verdicts.variable_order)

    @classmethod
    def from_PropositionList(cls, proposition_list: PropositionList):
        values = [
            [proposition_list.tp_to_ts[tp], tp, Proposition(proposition_list.prop_list[tp])]
            for tp in sorted(proposition_list.tp_to_ts.keys())
        ]
        return cls(values, proposition_list.variable_order)

    def to_proposition_tree(self, new_order: VariableOrdering):
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

        pdt = PropositionTree(new_order)
        for (ts, tp, val) in self.values:
            pdt.tp_to_ts[tp] = ts
            if isinstance(val, Proposition):
                pdt.forest[tp] = PDTTree(PDTLeaf(value=val.value))
            else:
                assignments = list(map(lambda ass: ass.retrieve_order(new_order=new_order), val))
                pdt.forest[tp] = PDTTree(_pdt_subtree_recurse(vars_=new_order.retrieve_order(), assignments=assignments))
        return pdt
