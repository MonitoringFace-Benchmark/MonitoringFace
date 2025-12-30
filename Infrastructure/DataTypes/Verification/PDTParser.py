import re
import ast

from typing import AnyStr, List, Tuple

from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PDTSets, PDTComplementSet, PDTSet, PDTNode, PDTLeave, PropositionTree
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrdering, VariableOrder, DefaultVariableOrder


def term_and_set(str_: AnyStr) -> Tuple[AnyStr, PDTSets]:
    split_list = str_.strip().split(IN_SYMBOL)
    term_ = split_list[0].strip()
    pdt_set = resolve_set(split_list[1].strip())
    return term_, pdt_set


def resolve_set(str_: AnyStr) -> PDTSets:
    if str_.__contains__(COMPLEMENT_OF):
        return PDTComplementSet(ast.literal_eval(str_.strip().removeprefix(COMPLEMENT_OF)))
    else:
        return PDTSet(ast.literal_eval(str_.strip()))


COMPLEMENT_OF = "Complement of "
OPEN_BRACKET = "❮"
CLOSED_BRACKET = "❯"
EXPLANATION_PREFIX = "Explanation:"
IN_SYMBOL = "∈"


def parse_tree(raw_string: AnyStr):
    raw_string = raw_string.strip()
    string = raw_string.replace(EXPLANATION_PREFIX, "")

    def _inner_parse_tree(raw_str):
        if raw_str == 'true' or raw_str.startswith("S"):
            return PDTLeave(value=True)
        elif raw_str.startswith("V"):
            return PDTLeave(value=False)
        raw_str = raw_str.strip().removeprefix(OPEN_BRACKET).removesuffix(CLOSED_BRACKET).strip()

        tmp = raw_str.split(IN_SYMBOL, 1)
        pattern = f"{tmp[0].strip()} {IN_SYMBOL}"

        top_level_choices = re.split(rf'(?={pattern})', raw_str)
        terms, values = [], []

        for sub_tree_str in [part.strip() for part in top_level_choices if part.startswith(pattern)]:
            tmp = sub_tree_str.split("\n", 1)
            term_, set_ = term_and_set(tmp[0].strip())
            sub_tree_ = _inner_parse_tree(tmp[1].strip())

            terms.append(term_)
            values.append((set_, sub_tree_))
        return PDTNode(term=unify_term(terms), values=values)
    return _inner_parse_tree(string)


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
        return VariableOrder(tree.collect_terms_list())

    return DefaultVariableOrder()


def file_to_proposition_tree(file: AnyStr) -> PropositionTree:
    with open(file, "r") as raw:
        clean = "\n".join(line for line in raw.read().splitlines() if line.strip())
        diff_explanations = list(filter(None, re.split(r"(\d+:\d+)", clean)))
        tree = PropositionTree()
        for pair in [(diff_explanations[i], diff_explanations[i + 1]) for i in range(0, len(diff_explanations), 2)]:
            (tp, ts) = time_extract(pair[0])
            tree.insert(parse_tree(pair[1]), tp, ts)
        tree.variable_order = variable_ordering_tree(tree)
        return tree


def str_to_proposition_tree(raw_string: AnyStr) -> PropositionTree:
    clean = "\n".join(line for line in raw_string.splitlines() if line.strip())
    diff_explanations = list(filter(None, re.split(r"(\d+:\d+)", clean)))
    tree = PropositionTree()
    for pair in [(diff_explanations[i], diff_explanations[i + 1]) for i in range(0, len(diff_explanations), 2)]:
        (tp, ts) = time_extract(pair[0])
        tree.insert(parse_tree(pair[1]), tp, ts)
    tree.variable_order = variable_ordering_tree(tree)
    return tree
