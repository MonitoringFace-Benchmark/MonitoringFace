import os
import re
import ast
import sys

from typing import AnyStr, List, Tuple

from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PDTSets, PDTComplementSet, \
    PDTSet, PDTNode, PDTLeaf, PropositionTree, PDTTree
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrdering, VariableOrder, DefaultVariableOrder


def term_and_set(str_: AnyStr) -> Tuple[AnyStr, PDTSets]:
    split_list = str_.split(IN_SYMBOL)
    term_ = split_list[0].strip()
    pdt_set = resolve_set(split_list[1].strip())
    return term_, pdt_set


def resolve_set(str_: str) -> PDTSets:
    if str_.__contains__(COMPLEMENT_OF):
        return PDTComplementSet(ast.literal_eval(str_.removeprefix(COMPLEMENT_OF).strip()))
    else:
        return PDTSet(ast.literal_eval(str_.strip()))


COMPLEMENT_OF = "Complement of "
OPEN_BRACKET = "❮"
CLOSED_BRACKET = "❯"
EXPLANATION_PREFIX = "Explanation:"
IN_SYMBOL = "∈"


def parse_tree(raw_string: str):
    def _inner_parse_tree(raw_level: str):
        raw_level_string = raw_level.strip()
        string = raw_level_string.replace(EXPLANATION_PREFIX, "").strip()
        level = string.strip().removeprefix(OPEN_BRACKET).removesuffix(CLOSED_BRACKET).strip()
        level = level.strip()
        if level == 'true' or level.startswith("S"):
            return PDTLeaf(value=True)
        elif level.startswith("V"):
            return PDTLeaf(value=False)

        level_term = level.split(IN_SYMBOL)[0].strip()
        all_sub_trees_raw = level.split(f"{level_term} {IN_SYMBOL}")
        all_sub_trees = list(filter(None, map(lambda s: s.strip(), all_sub_trees_raw)))
        values = []
        for tree in all_sub_trees:
            raw_split = tree.split("\n", 1)
            raw_set = raw_split[0].strip()
            guard_set = resolve_set(raw_set)
            raw_sub_tree = _inner_parse_tree(raw_split[1].strip())
            values.append((guard_set, raw_sub_tree))
        return PDTNode(term=level_term, values=values)
    return _inner_parse_tree(raw_string)


def unify_term(terms: List[AnyStr]) -> AnyStr:
    if all(s == terms[0] for s in terms):
        return terms[0]
    else:
        raise Exception(f"Parser error terms are not on the same level {terms}")


def time_extract(str_: AnyStr) -> Tuple[int, int]:
    tmp = str_.split(":")
    return int(tmp[0]), int(tmp[1])


def variable_ordering_tree(pt: PropositionTree) -> VariableOrdering:
    if not pt.forest:
        return DefaultVariableOrder()

    for tree in pt.forest.values():
        return VariableOrder(tree._collect_terms_list())
    return DefaultVariableOrder()


def file_to_proposition_tree(file: AnyStr) -> PropositionTree:
    with open(file, "r") as raw:
        clean = "\n".join(line for line in raw.read().splitlines() if line.strip())
        diff_explanations = list(filter(None, re.split(r"(\d+:\d+)", clean)))
        tree = PropositionTree()
        for pair in [(diff_explanations[i], diff_explanations[i + 1]) for i in range(0, len(diff_explanations), 2)]:
            (tp, ts) = time_extract(pair[0])
            tree.insert(PDTTree(parse_tree(pair[1])), tp, ts)
        tree.variable_order = variable_ordering_tree(tree)
        return tree


def str_to_proposition_tree(raw_string: AnyStr) -> PropositionTree:
    clean = "\n".join(line for line in raw_string.splitlines() if line.strip())
    diff_explanations = list(filter(None, re.split(r"(\d+:\d+)", clean)))
    tree = PropositionTree()
    for pair in [(diff_explanations[i], diff_explanations[i + 1]) for i in range(0, len(diff_explanations), 2)]:
        (tp, ts) = time_extract(pair[0])
        tree.insert(PDTTree(parse_tree(pair[1])), tp, ts)
    tree.variable_order = variable_ordering_tree(tree)
    return tree


if __name__ == "__main__":
    with open("/Users/krq770/Desktop/PastedText1.txt", "r") as f:
        print(str_to_proposition_tree(f.read()))

    with open("/Users/krq770/Desktop/PastedText.txt", "r") as f:
        print(str_to_proposition_tree(f.read()))
