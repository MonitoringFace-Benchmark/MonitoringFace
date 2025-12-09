from typing import AnyStr

from Infrastructure.DataTypes.Verification.OutputStructures.Structures.OooVerdicts import OooVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts
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
    def from_PropositionTree(cls, proposition_list: PropositionList):
        values = [[tp, [Proposition(proposition_list.prop_list[tp])]] for tp in sorted(proposition_list.tp_to_ts.keys())]
        return cls(values, proposition_list.variable_order)
