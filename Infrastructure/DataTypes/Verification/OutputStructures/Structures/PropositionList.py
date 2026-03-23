from typing import Dict, List, Optional, Tuple

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.Proposition import Proposition
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrdering


class PropositionList(AbstractOutputStructure):
    def __init__(self, variable_order: VariableOrdering):
        self.prop_list = dict()
        self.tp_to_ts = dict()
        self.variable_order = variable_order

    def retrieve_order(self) -> List[str]:
        return self.variable_order.retrieve_order()

    def time_points(self) -> Dict[int, int]:
        return self.tp_to_ts

    def as_oracle(self, other: 'AbstractOutputStructure') -> Tuple[bool, str]:
        from Infrastructure.DataTypes.Verification.OutputStructures.Compare.PropositionListComparator import as_oracle
        return as_oracle(self, other)

    def retrieve(self, time_point) -> Optional[Tuple[int, int, Proposition]]:
        if time_point in self.prop_list:
            return time_point, self.tp_to_ts[time_point], self.prop_list[time_point]
        return None

    def insert(self, value: Proposition, time_point: int, time_stamp: Optional[int] = None):
        self.tp_to_ts[time_point] = time_stamp if time_stamp else time_point
        self.prop_list[time_point] = value
