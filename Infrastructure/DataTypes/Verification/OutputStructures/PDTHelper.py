from Infrastructure.DataTypes.Verification.OutputStructures.Structures.DatagolfVerdicts import DatagolfVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PDTLeaf, \
    PDTComplementSet, PDTSet, PDTNode, PDTComponents, PropositionTree, PDTTree, PDTSets


class PDTCompareError(Exception):
    pass


def data_golf_pdt_equality(data_golf: DatagolfVerdicts, right_tree: PropositionTree) -> bool:
    for (tp, vals) in data_golf.pos_verdicts.items():
        tree = right_tree.forest[tp]
        if tree:
            for val in vals:
                if not tree.check_assignment(val):
                    raise PDTCompareError(f"Right tree has different verdict for {val}")
        else:
            raise PDTCompareError(f"Right tree missing positive verdict for type {tp}")

    for (tp, vals) in data_golf.neg_verdicts.items():
        tree = right_tree.forest[tp]
        if not tree:
            continue
        else:
            for val in vals:
                if tree.check_assignment(val):
                    raise PDTCompareError(f"Right tree has different verdict for {val}")
    return True


def collapse_pdt(pdt: PDTComponents) -> bool:
    def _inner(pdt_):
        if isinstance(pdt_, PDTLeaf):
            return pdt_.value
        elif isinstance(pdt_, PDTNode):
            return all([_inner(y) for (_, y) in pdt_.values])
        else:
            raise ValueError("Malformed Tree")
    return _inner(pdt)


def negate_pdt(pdt: PDTComponents) -> PDTComponents:
    if isinstance(pdt, PDTLeaf):
        return PDTLeaf(not pdt.value)
    elif isinstance(pdt, PDTNode):
        new_values = []
        for guard, subtree in pdt.values:
            negated_subtree = negate_pdt(subtree)
            new_values.append((guard, negated_subtree))
        return PDTNode(pdt.term, new_values)
    else:
        raise PDTCompareError("Unknown PDTComponents type during negate_pdt")


def equality_between_pdts(vars, left_tree: PDTTree, right_tree: PDTTree) -> bool:
    if len(vars) == 1:
        print("Single level tree comparison")
        return single_level_tree(left_tree.tree, right_tree.tree)
    else:
        print("Multi-level tree comparison")
        return collapse_pdt(apply2_reduce_inner(vars, (lambda x, y: x == y), left_tree.tree, right_tree.tree))


def single_level_tree(left_tree: PDTComponents, right_tree: PDTComponents) -> bool:
    if isinstance(left_tree, PDTLeaf) and isinstance(right_tree, PDTLeaf):
        return left_tree.value and right_tree.value
    elif isinstance(left_tree, PDTNode) and isinstance(right_tree, PDTNode):
        l_comp = None
        for x in left_tree.values:
            if isinstance(x[1], PDTComplementSet):
                l_comp = x[1]
        r_comp = None
        for x in right_tree.values:
            if isinstance(x[1], PDTComplementSet):
                r_comp = x[1]
        return l_comp == r_comp
    else:
         return False


def setc_union(set1: PDTSets, set2: PDTSets) -> PDTSets:
    if isinstance(set1, PDTSet) and isinstance(set2, PDTSet):
        return PDTSet(set1.set | set2.set)
    elif isinstance(set1, PDTSet) and isinstance(set2, PDTComplementSet):
        return PDTComplementSet(set1.set - set2.complement_set)
    elif isinstance(set1, PDTComplementSet) and isinstance(set2, PDTSet):
        return PDTComplementSet(set2.set - set1.complement_set)
    elif isinstance(set1, PDTComplementSet) and isinstance(set2, PDTComplementSet):
        return PDTComplementSet(set1.complement_set & set2.complement_set)
    else:
        raise PDTCompareError("Unknown PDTSets types in setc_union")


def setc_inter(set1: PDTSets, set2: PDTSets) -> PDTSets:
    if isinstance(set1, PDTSet) and isinstance(set2, PDTSet):
        return PDTSet(set1.set & set2.set)
    elif isinstance(set1, PDTSet) and isinstance(set2, PDTComplementSet):
        return PDTSet(set1.set - set2.complement_set)
    elif isinstance(set1, PDTComplementSet) and isinstance(set2, PDTSet):
        return PDTSet(set2.set - set1.complement_set)
    elif isinstance(set1, PDTComplementSet) and isinstance(set2, PDTComplementSet):
        return PDTComplementSet(set1.complement_set | set2.complement_set)
    else:
        raise PDTCompareError("Unknown PDTSets types in setc_inter")


def setc_diff(set1: PDTSets, set2: PDTSets) -> PDTSets:
    if isinstance(set1, PDTSet) and isinstance(set2, PDTSet):
        return PDTSet(set1.set - set2.set)
    elif isinstance(set1, PDTSet) and isinstance(set2, PDTComplementSet):
        return PDTSet(set1.set & set2.complement_set)
    elif isinstance(set1, PDTComplementSet) and isinstance(set2, PDTSet):
        return PDTComplementSet(set1.complement_set | set2.set)
    elif isinstance(set1, PDTComplementSet) and isinstance(set2, PDTComplementSet):
        return setc_inter(set1, PDTSet(set2.complement_set))
    else:
        raise PDTCompareError("Unknown PDTSets types in setc_diff")


def setc_is_empty(s: PDTSets) -> bool:
    if isinstance(s, PDTSet):
        return len(s.set) == 0
    elif isinstance(s, PDTComplementSet):
        return False
    else:
        raise PDTCompareError("Unknown PDTSets type in setc_is_empty")


def _map_dedup(part: list, f) -> list:
    return _dedup_part([(guard, f(value)) for guard, value in part])


def _merge2_dedup_iter(f, part1: list, part2: list) -> list:
    merged = []
    remaining_part2 = list(part2)
    for sub1, v1 in part1:
        new_remaining = []
        for sub2, v2 in remaining_part2:
            inter = setc_inter(sub1, sub2)
            if not setc_is_empty(inter):
                merged.append((inter, f(v1, v2)))
            diff = setc_diff(sub2, sub1)
            if not setc_is_empty(diff):
                new_remaining.append((diff, v2))
        remaining_part2 = new_remaining
    return _dedup_part(merged)


def _dedup_part(part: list) -> list:
    if not part:
        return []

    result = []
    for s, v in part:

        if result:
            # Check if we can merge with any existing entry
            merged = False
            for i in range(len(result)):
                t, u = result[i]
                if u == v:
                    result[i] = (setc_union(s, t), u)
                    merged = True
                    break
            if not merged:
                result.append((s, v))
        else:
            result.append((s, v))

    return result


def apply1_reduce(vars: list, f, node: PDTComponents) -> PDTComponents:
    if isinstance(node, PDTLeaf):
        return PDTLeaf(f(node.value))

    if isinstance(node, PDTNode):
        if not vars:
            raise PDTCompareError("Variable list is empty during apply1_reduce")

        current_var = vars[0]
        if node.term == current_var:
            new_values = []
            for guard, subtree in node.values:
                reduced_subtree = apply1_reduce(vars[1:], f, subtree)
                new_values.append((guard, reduced_subtree))
            deduped = _dedup_part(new_values)
            return PDTNode(node.term, deduped)
        else:
            return apply1_reduce(vars[1:], f, node)
    raise PDTCompareError("Unknown PDTComponents type during apply1_reduce")


def apply2_reduce_inner(vars: list, f, left_node: PDTComponents, right_node: PDTComponents) -> PDTComponents:
    if isinstance(left_node, PDTLeaf) and isinstance(right_node, PDTLeaf):
        return PDTLeaf(f(left_node.value, right_node.value))

    if isinstance(left_node, PDTLeaf) and isinstance(right_node, PDTNode):
        return PDTNode(
            right_node.term,
            _map_dedup(right_node.values, lambda l2: apply1_reduce(vars, lambda l1: f(left_node.value, l1), l2))
        )

    if isinstance(left_node, PDTNode) and isinstance(right_node, PDTLeaf):
        return PDTNode(
            left_node.term,
            _map_dedup(left_node.values, lambda l1: apply1_reduce(vars, lambda l2: f(l1, right_node.value), l1))
        )

    if isinstance(left_node, PDTNode) and isinstance(right_node, PDTNode):
        if not vars:
            raise PDTCompareError("Variable list is empty during apply2_reduce_inner")

        current_var = vars[0]
        rest_vars = vars[1:]

        if left_node.term == current_var and right_node.term == current_var:
            sub_list = _merge2_dedup_iter(
                lambda l1, l2: apply2_reduce_inner(rest_vars, f, l1, l2),
                left_node.values,
                right_node.values
            )

            if len(sub_list) == 1:
                return PDTLeaf(isinstance(sub_list[0], PDTComplementSet))
            return PDTNode(current_var, sub_list)

        if left_node.term == current_var:
            return PDTNode(
                left_node.term,
                _map_dedup(
                    left_node.values,
                    lambda l1: apply2_reduce_inner(rest_vars, f, l1, PDTNode(right_node.term, right_node.values))
                )
            )

        if right_node.term == current_var:
            return PDTNode(right_node.term,
                _map_dedup(right_node.values, lambda l2: apply2_reduce_inner(rest_vars, f, PDTNode(left_node.term, left_node.values), l2))
            )
        return apply2_reduce_inner(rest_vars, f, left_node, right_node)

    raise PDTCompareError("Unknown PDTComponents type during apply2_reduce_inner")
