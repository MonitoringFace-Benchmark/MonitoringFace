from abc import ABC, abstractmethod
from typing import AnyStr, List, Set, Tuple, Dict, Any

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure


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


class PDTLeave(PDTComponents):
    def __init__(self, value: bool):
        self.value = value

    def __repr__(self):
        return f"PDTLeave({repr(self.value)})"


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
        self.terms = self.collect_terms()

    def collect_terms(self) -> Set[AnyStr]:
        def _inner_collect_terms(tree_: PDTComponents) -> Set[AnyStr]:
            if isinstance(tree_, PDTLeave):
                return set()
            else:
                term_set = {tree_.term}
                for (_, sub_tree_) in tree_.values:
                    term_set = term_set.union(_inner_collect_terms(sub_tree_))
                return term_set
        return _inner_collect_terms(self.tree)

    def walk_tree(self, term_assignment: List[Tuple[AnyStr, Any]]):
        def _get_value(terms_vals, term):
            for (key, value) in terms_vals:
                if key == term:
                    return value

            if term in self.terms:
                _, last = terms_vals[-1]
                return last
            raise InvalidPDTTerm(f"Term {term} not in Assignment")

        def _make_choice(value, choices: List[Tuple[PDTSets, PDTComponents]]):
            for (pdt_set, sub_tree) in choices:
                if pdt_set.is_member(value):
                    return sub_tree
            raise InvalidPDTChoice(f"{value} not in Domain")

        def _inner_walk_tree(tree_: PDTNode, term_assignment_: List[Tuple[AnyStr, Any]]) -> bool:
            if isinstance(tree_, PDTLeave):
                return tree_.value
            value = _get_value(term_assignment_, tree_.term)
            choice = _make_choice(value, tree_.values)
            return _inner_walk_tree(choice, term_assignment_)

        if isinstance(self.tree, PDTLeave):
            return self.tree.value
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


if __name__ == "__main__":
    leave = PDTLeave(value=True)
    tree = PDTTree(leave)
    print(tree.walk_tree([]))

    root = PDTNode(term="t1", values=[
        (PDTSet({1, 2}), PDTLeave(value=False)),
        (PDTComplementSet({1, 2}), PDTLeave(value=True))
    ])

    tree = PDTTree(root)
    print(tree.walk_tree([("t1", 3)]))
    print(tree.walk_tree([("t1", 1)]))
    print(tree.terms)

    root = PDTNode(term="t1", values=[
        (PDTSet({1, 2}),
            PDTNode(term="t2",
                    values=[
                        (PDTSet({5, 10}), PDTLeave(value=True)),

                        (PDTComplementSet({5, 10}),
                         PDTNode(term="x", values=[
                             (PDTSet({12}), PDTLeave(value=True)),
                             (PDTComplementSet({5, 10}), PDTLeave(value=False))
                        ])
                    )
                ]
            )
        ),
        (PDTComplementSet({1, 2}), PDTLeave(value=True))
    ])

    tree = PDTTree(root)
    print(tree.walk_tree([("t1", 1), ("t2", 12)]))
