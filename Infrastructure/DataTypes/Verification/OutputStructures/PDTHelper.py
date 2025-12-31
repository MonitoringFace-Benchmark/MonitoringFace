from Infrastructure.DataTypes.Verification.OutputStructures.Structures.DatagolfVerdicts import DatagolfVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PDTLeave, \
    PDTComplementSet, PDTSet, PDTNode, PDTComponents, PropositionTree


class PDTCompareError(Exception):
    pass


def data_golf_pdt_equality(data_golf: DatagolfVerdicts, right_tree: PropositionTree) -> bool:
    for (tp, vals) in data_golf.pos_verdicts.items():
        tree = right_tree.forest[tp]
        if tree:
            for val in vals:
                if not _find_leaf_for_value(tree.root, val):
                    raise PDTCompareError(f"Right tree has different verdict for {val}")
        else:
            raise PDTCompareError(f"Right tree missing positive verdict for type {tp}")

    for (tp, vals) in data_golf.neg_verdicts.items():
        tree = right_tree.forest[tp]
        if not tree:
            continue
        else:
            for val in vals:
                if _find_leaf_for_value(tree.root, val):
                    raise PDTCompareError(f"Right tree has different verdict for {val}")
    return True



def equality_between_pdts(left_tree, right_tree) -> bool:
    def _inner(left_node, right_node) -> bool:
        if isinstance(left_node, PDTLeave) and isinstance(right_node, PDTLeave):
            return left_node.value == right_node.value

        if isinstance(left_node, PDTLeave) or isinstance(right_node, PDTLeave):
            raise PDTCompareError(
                f"Structure mismatch at term {getattr(left_node, 'term', 'leaf')}: "
                f"ground truth is {'leaf' if isinstance(left_node, PDTLeave) else 'node'}, "
                f"but right tree is {'leaf' if isinstance(right_node, PDTLeave) else 'node'}"
            )

        if left_node.term != right_node.term:
            raise PDTCompareError(
                f"Right tree tests wrong variable at this node: "
                f"tests '{right_node.term}', but ground truth tests '{left_node.term}'"
            )

        left_finite, left_complement = _extract_finite_and_complement(left_node.values)
        right_finite, right_complement = _extract_finite_and_complement(right_node.values)

        if left_complement.complement_set != right_complement.complement_set:
            raise PDTCompareError(
                f"Right tree's ComplementSet at term '{left_node.term}' is incorrect: "
                f"excludes {right_complement.complement_set}, but ground truth excludes {left_complement.complement_set}"
            )

        if not _are_finite_sets_equivalent(left_finite, right_finite):
            raise PDTCompareError(f"Right tree's finite sets at term '{left_node.term}' are not subset-equivalent")

        # todo how to recurse properly here, given that we need to also
        # recurse the right tree that might not be the same structure?
        for _, left_subtree in left_finite:
            pass

        return True

    return _inner(left_tree, right_tree)


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
