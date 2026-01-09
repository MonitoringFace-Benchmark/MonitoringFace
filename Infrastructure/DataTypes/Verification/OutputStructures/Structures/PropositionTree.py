from abc import ABC, abstractmethod
from typing import AnyStr, List, Set, Tuple, Dict, Any

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.Assignment import Assignment
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrder


class InvalidPDTTerm(Exception):
    pass


class InvalidPDTChoice(Exception):
    pass


class PDTSets:
    @abstractmethod
    def is_member(self, value) -> bool:
        pass


class PDTSet(PDTSets):
    def __init__(self, elems: Set):
        self.set = elems

    def __repr__(self):
        return f"PDTSet({repr(self.set)})"

    def is_member(self, value) -> bool:
        return value in self.set


class PDTComplementSet(PDTSets):
    def __init__(self, elems: Set):
        self.complement_set = elems

    def __repr__(self):
        return f"PDTComplementSet({repr(self.complement_set)})"

    def is_member(self, value) -> bool:
        return value not in self.complement_set


class PDTComponents(ABC):
    pass


class PDTLeaf(PDTComponents):
    def __init__(self, value: bool):
        self.value = value

    def __repr__(self):
        return f"PDTLeaf({repr(self.value)})"


class PDTNode(PDTComponents):
    def __init__(self, term: AnyStr, values: List[Tuple[PDTSets, PDTComponents]]):
        self.term = term
        self.values = values

    def __repr__(self):
        vals = [f"({repr(s)}, {repr(val)})" for (s, val) in self.values]
        joint = ", ".join(vals)
        return f"PDTNode({self.term}, [{joint}])"


class PDTTree:
    def __init__(self, root: PDTComponents):
        self.tree = root
        self.terms = self._collect_terms_list()

    def _collect_terms_list(self) -> List[AnyStr]:
        result: List[AnyStr] = []
        seen: Set[AnyStr] = set()

        def _inner_collect_terms_list(tree_: PDTComponents):
            if isinstance(tree_, PDTLeaf):
                return
            elif isinstance(tree_, PDTNode):
                term = tree_.term
                if term not in seen:
                    seen.add(term)
                    result.append(term)
                for (_, sub_tree_) in tree_.values:
                    _inner_collect_terms_list(sub_tree_)
            else:
                raise ValueError(f"Not well-formed PDT tree at node {repr(tree_)}")
        _inner_collect_terms_list(self.tree)
        return result

    def check_assignment(self, assignment: Assignment) -> bool:
        reordered_assignment = assignment.retrieve_order(VariableOrder(self.terms))
        try:
            return self.walk_tree(reordered_assignment.to_representation())
        except InvalidPDTTerm:
            return False

    def walk_tree(self, term_assignment: List[Tuple[Any, AnyStr]]) -> bool:
        def _get_value(terms_vals: List[Tuple[Any, AnyStr]], term: AnyStr):
            for (value, var) in terms_vals:
                if var == term:
                    return value
            raise InvalidPDTTerm(f"Term {term} not in Assignment")

        def _make_choice(value, choices: List[Tuple[PDTSets, PDTComponents]]):
            for (pdt_set, sub_tree) in choices:
                if pdt_set.is_member(value):
                    return sub_tree
            raise InvalidPDTChoice(f"{value} not in Domain")  # implies construction error

        def _inner_walk_tree(tree_: PDTComponents, term_assignment_: List[Tuple[AnyStr, Any]]) -> bool:
            if isinstance(tree_, PDTLeaf):
                return tree_.value
            elif isinstance(tree_, PDTNode):
                value = _get_value(term_assignment_, tree_.term)
                choice = _make_choice(value, tree_.values)
                return _inner_walk_tree(choice, term_assignment_)
            else:
                raise ValueError(f"Not well-formed PDT tree at node {repr(tree_)}")

        return _inner_walk_tree(self.tree, term_assignment)


class PropositionTree(AbstractOutputStructure):
    def __init__(self, variable_order=None):
        self.forest: Dict[int, PDTTree] = dict()
        self.tp_to_ts: Dict[int, int] = dict()
        self.variable_order = variable_order

    def retrieve(self, time_point: int):
        if time_point in self.forest:
            return self.forest[time_point]
        return None

    def insert(self, value, time_point: int, time_stamp: int):
        self.tp_to_ts[time_point] = time_stamp
        self.forest[time_point] = value
