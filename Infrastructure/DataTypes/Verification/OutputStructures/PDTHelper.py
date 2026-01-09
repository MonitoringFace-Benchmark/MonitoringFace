from Infrastructure.DataTypes.Verification.OutputStructures.Structures.DatagolfVerdicts import DatagolfVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PDTLeave, \
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
        if isinstance(pdt_, PDTLeave):
            return pdt_.value
        elif isinstance(pdt_, PDTNode):
            return all([_inner(y) for (_, y) in pdt_.values])
        else:
            raise ValueError("Malformed Tree")
    return _inner(pdt)


def equality_between_pdts(vars, left_tree: PDTTree, right_tree: PDTTree) -> bool:
    return collapse_pdt(apply2_reduce_inner(vars, (lambda x, y: x == y), left_tree.tree, right_tree.tree))


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


def _merge2_dedup(f, part1: list, part2: list) -> list:
    def merge2(f, part1, part2):
        if not part1:
            return []

        sub1, v1 = part1[0]
        rest_part1 = part1[1:]

        part12 = []
        part2not1 = []

        for sub2, v2 in part2:
            inter = setc_inter(sub1, sub2)
            if not setc_is_empty(inter):
                part12.append((inter, f(v1, v2)))

            diff = setc_diff(sub2, sub1)
            if not setc_is_empty(diff):
                part2not1.append((diff, v2))

        return part12 + merge2(f, rest_part1, part2not1)

    merged = merge2(f, part1, part2)
    return _dedup_part(merged)


def _dedup_part(part: list) -> list:
    def aux(acc, sv):
        s, v = sv
        if not acc:
            return [(s, v)]
        t, u = acc[0]
        rest_acc = acc[1:]
        if u == v:
            return [(setc_union(s, t), u)] + rest_acc
        else:
            return [(t, u)] + aux(rest_acc, (s, v))

    def dedup_rec(part, acc):
        if not part:
            return acc
        s, v = part[0]
        return dedup_rec(part[1:], aux(acc, (s, v)))

    return dedup_rec(part, [])


def apply1_reduce(vars: list, f, node: PDTComponents) -> PDTComponents:
    if isinstance(node, PDTLeave):
        return PDTLeave(f(node.value))

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
            return apply1_reduce(vars, f, node)
    raise PDTCompareError("Unknown PDTComponents type during apply1_reduce")


def apply2_reduce_inner(vars: list, f, left_node: PDTComponents, right_node: PDTComponents) -> PDTComponents:
    if isinstance(left_node, PDTLeave) and isinstance(right_node, PDTLeave):
        return PDTLeave(f(left_node.value, right_node.value))

    if isinstance(left_node, PDTLeave) and isinstance(right_node, PDTNode):
        return PDTNode(
            right_node.term,
            _map_dedup(right_node.values, lambda l2: apply1_reduce(vars, lambda l1: f(left_node.value, l1), l2))
        )

    if isinstance(left_node, PDTNode) and isinstance(right_node, PDTLeave):
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
            sub_list = _merge2_dedup(
                lambda l1, l2: apply2_reduce_inner(rest_vars, f, l1, l2),
                left_node.values,
                right_node.values
            )

            if len(sub_list) == 1:
                return PDTLeave(isinstance(sub_list[0], PDTComplementSet))
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
        return apply2_reduce_inner(vars, f, left_node, right_node)

    raise PDTCompareError("Unknown PDTComponents type during apply2_reduce_inner")


def _extract_finite_and_complement(node_values: PDTNode) -> tuple[list[tuple[PDTSet, PDTComponents]], PDTComplementSet]:
    finite_pairs = []
    complement_pair = None

    for guard, subtree in node_values.values:
        if isinstance(guard, PDTSet):
            finite_pairs.append((guard, subtree))
        elif isinstance(guard, PDTComplementSet):
            complement_pair = guard

    return finite_pairs, complement_pair


def _find_leaf_for_value(node, value) -> bool:
    if value is None and not isinstance(node, PDTLeave):
        raise PDTCompareError(f"Value is None but node at term {node.term} is not a leaf")

    if isinstance(node, PDTLeave):
        return node.value

    for guard, subtree in node.values:
        if guard.is_member(value):
            return _find_leaf_for_value(subtree, value)

    raise PDTCompareError(f"No guard matched value {value} at term {node.term}")


def _are_finite_sets_equivalent(left_finite, right_finite):
    left_sets = [guard.set for guard, _ in left_finite]
    matched_left = set()

    for right_set in [guard.set for guard, _ in right_finite]:
        found_match = False
        for i, left_set in enumerate(left_sets):
            if right_set & left_set:  # intersection
                if right_set <= left_set:  # subset check
                    matched_left.add(i)
                    found_match = True
                    break
        if not found_match:
            return False

    if len(matched_left) != len(left_sets):
        return False

    return True
