from abc import ABC
from typing import AnyStr, List, Set, Tuple, Dict

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure


class PDTSets:
    pass


class PDTSet(PDTSets):
    def __init__(self, elems: Set):
        self.set = elems


class PDTComplementSet(PDTSets):
    def __init__(self, elems: Set):
        self.complement_set = elems


class PDTComponents(ABC):
    pass


class PDTLeave(PDTComponents):
    def __init__(self, value: bool):
        self.value = value


class PDTNode(PDTComponents):
    def __init__(self, term: AnyStr, values: List[Tuple[PDTSets, PDTComponents]]):
        self.term = term
        self.values = values


class PDTTree:
    def __init__(self, tree):
        self.tree = tree


class PropositionTree(AbstractOutputStructure):
    def __init__(self):
        self.forest: Dict[int, PDTTree] = dict()
        self.tp_to_ts: Dict[int, int] = dict()

    def retrieve(self, time_point):
        tree = self.forest[time_point]
        # extract from tree

    def insert(self, value, time_point, time_stamp):
        self.tp_to_ts[time_point] = time_stamp
        self.forest[time_point] = value
