import re
import ast


from typing import AnyStr, List

from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PDTSets, PDTComplementSet, \
    PDTSet, PDTNode, PDTLeave


def parse_brackets_stack(s):
    stack = [[]]
    token = ""
    for char in s:
        if char == '❮':
            if token.strip():
                stack[-1].append(token.strip())
                token = ""
            stack.append([])
        elif char == '❯':
            if token.strip():
                stack[-1].append(token.strip())
                token = ""
            finished = stack.pop()
            stack[-1].append(finished)
        else:
            token += char
    return stack[0]


def term_and_set(str_: AnyStr) -> (AnyStr, PDTSets):
    str_ = str_.strip()
    split_list = str_.split("∈")
    term_ = split_list[0].strip()
    pdt_set = resolve_set(split_list[1].strip())
    return term_, pdt_set


def resolve_set(str_: AnyStr) -> PDTSets:
    if str_.__contains__("Complement of"):
        return complement_set(str_)
    else:
        return normal_set(str_)


def complement_set(str_: AnyStr) -> PDTSets:
    set_str = str_.strip()
    set_str = set_str.removeprefix("Complement of ")
    return PDTComplementSet(ast.literal_eval(set_str))


def normal_set(str_: AnyStr) -> PDTSets:
    set_str = str_.strip()
    return PDTSet(ast.literal_eval(set_str))


def parse_tree(raw_string: AnyStr):
    raw_string = raw_string.strip()
    string = raw_string.replace("Explanation:", "")
    # recursive step
    top_level_vals = parse_brackets_stack(string)[0]
    terms = []
    vals = []
    inner_pairs = [(top_level_vals[i], top_level_vals[i + 1]) for i in range(0, len(top_level_vals), 2)]
    for (term_set, sub_tree) in inner_pairs:
        term_, set_ = term_and_set(term_set)
        terms.append(term_)
        vals.append((set_, parse_tree_inner(sub_tree)))
    print(vals)
    return PDTTree(root=PDTNode(term=unify_term(terms), values=vals))


def unify_term(terms: List[AnyStr]) -> AnyStr:
    if all(s == terms[0] for s in terms):
        return terms[0]
    else:
        raise Exception(f"Parser error terms are not on the same level {terms}")


def parse_tree_inner(sub_tree):
    print("====" * 20)
    print(sub_tree)
    if well_formed(sub_tree):
        terms, vals = [], []
        inner_pairs = [(sub_tree[i], sub_tree[i + 1]) for i in range(0, len(sub_tree), 2)]
        for (term_set, sub_tree) in inner_pairs:
            term_, set_ = term_and_set(term_set)
            terms.append(term_)
            vals.append((set_, parse_tree_inner(sub_tree)))
        return PDTNode(term=unify_term(terms), values=vals)
    else:
        # leave
        print("leave")
        if len(sub_tree) == 1:
            sub_tree_ = sub_tree[0].split("\n")
            if len(sub_tree_) == 2:
                bool_val = True if sub_tree_[1] == "true" else False
                return PDTLeave(bool_val)
            elif len(sub_tree_) % 2 == 0:
                print(sub_tree_)
                print("well formed")
            else:
                print("inner leave")
        else:
            print("*" * 50)
        print(sub_tree)

    return []


def well_formed(xs):
    if len(xs) % 2 != 0:
        return False
    for i, item in enumerate(xs):
        if i % 2 == 0:
            if not isinstance(item, str):
                return False
        else:
            if not isinstance(item, list):
                return False
    return True


class PDTTree:
    def __init__(self, root):
        self.tree = root


if __name__ == "__main__":
    with open("/Users/krq770/Desktop/tmp/t.txt", "r") as f:
        your_string = f.read()
        cleaned = "\n".join(
            line for line in your_string.splitlines() if line.strip()
        )
        parts = list(filter(None, re.split(r"(\d+:\d+)", cleaned)))
        pairs = [(parts[i], parts[i + 1]) for i in range(0, len(parts), 2)]
        print(len(pairs))
        for pair in pairs:
            parse_tree(pair[1])
            """
            x = pair[1]
            x = x.strip()
            x = x.replace("Explanation:", "")

            for xxx in parse_brackets_stack(x):
                #print(xxx)
                _inner_pairs = [(xxx[i], xxx[i + 1]) for i in range(0, len(xxx), 2)]
                for (str_part, list_part) in _inner_pairs:

                    print(str_part)
                    term, sets = term_and_set(str_part)
                    print(list_part)
                    #print(type(xx))
                break
            break
            """
