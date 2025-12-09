from typing import AnyStr, List

from Infrastructure.DataTypes.Verification.OutputStructures.Structures.OooVerdicts import OooVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PropositionTree, PDTLeave, \
    PDTComplementSet, PDTSet
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.Assignment import Assignment
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.Proposition import Proposition
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.ValueType import ValueType


class IntermediateList:
    def __init__(self, values, variable_ordering: list[AnyStr]):
        self.values: list[int, list[ValueType]] = values
        self.variable_ordering = variable_ordering

    @classmethod
    def from_OOOVerdicts(cls, ooo_verdicts: OooVerdicts):
        values = []
        for tp in sorted(ooo_verdicts.tp_to_ts.keys()):
            values.append([
                tp, [val for (val_tp, _, vals) in ooo_verdicts.ooo_verdict if tp == val_tp for val in vals]
            ])
        return cls(values, ooo_verdicts.variable_order)

    @classmethod
    def from_Verdicts(cls, verdicts: Verdicts):
        return cls(verdicts.verdict, verdicts.variable_order)

    @classmethod
    def from_PropositionList(cls, proposition_list: PropositionList):
        values = [[tp, [Proposition(proposition_list.prop_list[tp])]] for tp in sorted(proposition_list.tp_to_ts.keys())]
        return cls(values, proposition_list.variable_order)

    def to_proposition_tree(self, new_variable_order: List[AnyStr]) -> PropositionTree:
        def _assignment_list(value_):
            if isinstance(value_[0], Assignment):
                return True
            return False

        tree = PropositionTree(new_variable_order)

        for (tp, vals) in self.values:
            if _assignment_list(vals):
                new_assignments = map(lambda val: val.retrieve_order(new_variable_order), vals)
                set_complement_list = extract_sets(new_assignments, new_variable_order)


            else:
                tree.insert(tp, tp, PDTLeave(value=vals[0]).value)

        return tree


def extract_sets(new_assignment, order):
    collect_vals = []
    for i in range(0, len(order)):
        vals = set([val[i] for val in new_assignment])
        collect_vals.append((PDTSet(vals), PDTComplementSet(vals)))
    return collect_vals


if __name__ == "__main__":
    print(extract_sets([(1, 2), (3, 4), (5, 6), (7, 8)], ["x", "y"]))
