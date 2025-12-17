from enum import Enum
from typing import AnyStr, List, Union

from Infrastructure.DataTypes.Verification.OutputStructures.Structures.OooVerdicts import OooVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PDTLeave, PDTComplementSet, PDTSet, PDTNode
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.Assignment import Assignment
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.Proposition import Proposition


class ValueType(Enum):
    PROP = 1
    ASSIGNMENTS = 2


class IntermediateList:
    def __init__(self, values, variable_ordering: list[AnyStr], t: ValueType):
        self.values: list[int, Union[list[Assignment], Proposition]] = values
        self.variable_ordering = variable_ordering
        self.value_type = t

    @classmethod
    def from_OOOVerdicts(cls, ooo_verdicts: OooVerdicts):
        values = []
        for tp in sorted(ooo_verdicts.tp_to_ts.keys()):
            values.append([
                tp, [val for (val_tp, _, vals) in ooo_verdicts.ooo_verdict if tp == val_tp for val in vals]
            ])
        return cls(values, ooo_verdicts.variable_order, ValueType.ASSIGNMENTS)

    @classmethod
    def from_Verdicts(cls, verdicts: Verdicts):
        return cls(verdicts.verdict, verdicts.variable_order, ValueType.ASSIGNMENTS)

    @classmethod
    def from_PropositionList(cls, proposition_list: PropositionList):
        values = [[tp, Proposition(proposition_list.prop_list[tp])] for tp in sorted(proposition_list.tp_to_ts.keys())]
        return cls(values, proposition_list.variable_order, ValueType.PROP)

    def to_proposition_tree(self, new_order: List[AnyStr]):
        assignments, variables = self.values, self.variable_ordering

        if not variables:
            return PDTLeave(value=assignments[0].value)  # handle closed formulas

        def _pdt_subtree_recurse(vars_: List[str], fixed_vars, assignments: List[Assignment], current_assignment: List):
            if not vars_:
                return PDTLeave(Assignment(fixed_vars, current_assignment) in assignments)

            var_ = vars_[0]
            remaining = vars_[1:]

            domain_set = set([assignment.retrieve_value(var_) for assignment in assignments])
            choices = []
            for elem in domain_set:
                new_assignment = current_assignment.copy()
                new_assignment.append(elem)
                subtree = _pdt_subtree_recurse(remaining, fixed_vars, assignments, new_assignment)
                choices.append((PDTSet({elem}), subtree))

            choices.append((PDTComplementSet(domain_set), PDTLeave(False)))
            return PDTNode(var_, choices)

        assignments = list(map(lambda ass: ass.retrieve_order(new_order=new_order), assignments))
        return _pdt_subtree_recurse(vars_=variables, fixed_vars=variables, assignments=assignments, current_assignment=[])
