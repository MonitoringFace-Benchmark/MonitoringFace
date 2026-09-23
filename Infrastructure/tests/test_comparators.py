"""Tests for the oracle/tool comparison matrix. Plain asserts, no pytest
dependency: run with

    Infrastructure/environment/venv/bin/python -m Infrastructure.tests.test_comparators

Covers every implemented (oracle, tool) cell: that none raises, that each
declares the strength it is actually capable of, that none reports success
without having inspected a value, that each rejects a mutated tool output
wherever its strength permits it to notice, and that Comparison still unpacks
as the legacy (ok, message) tuple.
"""

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractComparator import (
    time_point_pdt_check, verdicts_to_proposition_tree)
from Infrastructure.DataTypes.Verification.OutputStructures.PDTHelper import equality_between_pdts
from Infrastructure.DataTypes.Verification.PDTParser import literal_set, resolve_set, str_to_proposition_tree
from Infrastructure.DataTypes.Verification.OutputStructures.Strength import Comparison, Strength
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.DatagolfVerdicts import DatagolfVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.OooVerdicts import OooVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import (
    PropositionTree, PDTComplementSet, PDTLeaf, PDTNode, PDTSet, PDTTree)
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.Proposition import Proposition
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrder

ORDER = VariableOrder(["x"])
TIME_POINTS = (0, 1)
GOOD = "7"
BAD = "8"


def verdicts(cls, value=GOOD):
    structure = cls(ORDER)
    for tp in TIME_POINTS:
        structure.insert([[value]], tp, tp)
    return structure


def proposition_list(value=True):
    structure = PropositionList(ORDER)
    for tp in TIME_POINTS:
        structure.insert(Proposition(value), tp, tp)
    return structure


def proposition_list_elsewhere():
    """The only meaningful mutation of a PropositionList: report at a different
    time-point. The stored Boolean is a producer-specific constant (DejaVu
    writes False at every violation, TeSSLa True at every reported point) and
    no relation compares it, so flipping it mutates nothing observable."""
    structure = PropositionList(ORDER)
    for tp in (TIME_POINTS[0], max(TIME_POINTS) + 1):
        structure.insert(Proposition(True), tp, tp)
    return structure


def proposition_tree(value=GOOD):
    # lowered from the matching Verdicts, so "equivalent" fixtures really are
    return verdicts_to_proposition_tree(verdicts(Verdicts, value), ORDER)


def datagolf():
    structure = DatagolfVerdicts(ORDER)
    for tp in TIME_POINTS:
        structure.insert_positive_verdict([[GOOD]], tp, tp)
        structure.insert_negative_verdict([[BAD]], tp, tp)
    return structure


ORACLES = {
    "Verdicts": lambda: verdicts(Verdicts),
    "OooVerdicts": lambda: verdicts(OooVerdicts),
    "PropositionList": proposition_list,
    "PropositionTree": proposition_tree,
    "Datagolf": datagolf,
}

TOOLS = {
    "Verdicts": lambda: verdicts(Verdicts),
    "OooVerdicts": lambda: verdicts(OooVerdicts),
    "PropositionList": proposition_list,
    "PropositionTree": proposition_tree,
}

# A tool output that disagrees with the oracle. Assignment-bearing structures
# carry a different value; a PropositionList reports at a different time-point,
# which is the only part of it that carries information.
MUTANTS = {
    "Verdicts": lambda: verdicts(Verdicts, BAD),
    "OooVerdicts": lambda: verdicts(OooVerdicts, BAD),
    "PropositionList": proposition_list_elsewhere,
    "PropositionTree": lambda: proposition_tree(BAD),
}

EXPECTED_STRENGTH = {
    ("Verdicts", "Verdicts"): Strength.EQUIVALENT,
    ("Verdicts", "OooVerdicts"): Strength.EQUIVALENT,
    ("Verdicts", "PropositionList"): Strength.CONSISTENT,
    ("Verdicts", "PropositionTree"): Strength.EQUIVALENT,
    ("OooVerdicts", "Verdicts"): Strength.EQUIVALENT,
    ("OooVerdicts", "OooVerdicts"): Strength.EQUIVALENT,
    ("OooVerdicts", "PropositionList"): Strength.CONSISTENT,
    ("OooVerdicts", "PropositionTree"): Strength.EQUIVALENT,
    ("PropositionList", "Verdicts"): Strength.CONSISTENT,
    ("PropositionList", "OooVerdicts"): Strength.CONSISTENT,
    ("PropositionList", "PropositionList"): Strength.EQUIVALENT,
    ("PropositionList", "PropositionTree"): Strength.CONSISTENT,
    ("PropositionTree", "Verdicts"): Strength.SUBSET,
    ("PropositionTree", "OooVerdicts"): Strength.SUBSET,
    ("PropositionTree", "PropositionList"): Strength.CONSISTENT,
    ("PropositionTree", "PropositionTree"): Strength.EQUIVALENT,
    ("Datagolf", "Verdicts"): Strength.CONSISTENT,
    ("Datagolf", "OooVerdicts"): Strength.CONSISTENT,
    ("Datagolf", "PropositionList"): Strength.UNSUPPORTED,
    ("Datagolf", "PropositionTree"): Strength.CONSISTENT,
}

# Cells that cannot see their mutant, and why. Each is a consequence of the
# declared strength, not a defect: a structure that carries no assignments
# cannot notice one changing, and a relation that only checks non-vacuity
# cannot notice a Boolean flipping to false.
MUTANT_INVISIBLE = {
    ("PropositionList", "Verdicts"): "oracle carries no assignments",
    ("PropositionList", "OooVerdicts"): "oracle carries no assignments",
    ("PropositionList", "PropositionTree"): "oracle carries no assignments",
    ("Datagolf", "PropositionList"): "relation is unsupported",
}


def cells():
    for oracle_name, oracle in ORACLES.items():
        for tool_name, tool in TOOLS.items():
            yield oracle_name, tool_name, oracle, tool


def test_no_cell_raises():
    for oracle_name, tool_name, oracle, tool in cells():
        result = oracle().as_oracle(tool())
        assert isinstance(result, Comparison), \
            f"{oracle_name} -> {tool_name} returned {type(result).__name__}, not Comparison"
    print("ok test_no_cell_raises")


def test_declared_strengths():
    for oracle_name, tool_name, oracle, tool in cells():
        result = oracle().as_oracle(tool())
        expected = EXPECTED_STRENGTH[(oracle_name, tool_name)]
        assert result.strength is expected, \
            f"{oracle_name} -> {tool_name}: strength {result.strength} != {expected}"
    print("ok test_declared_strengths")


def test_agreeing_outputs_verify():
    for oracle_name, tool_name, oracle, tool in cells():
        if EXPECTED_STRENGTH[(oracle_name, tool_name)] is Strength.UNSUPPORTED:
            continue
        result = oracle().as_oracle(tool())
        assert result.ok, f"{oracle_name} -> {tool_name} rejected agreeing outputs: {result.message}"
    print("ok test_agreeing_outputs_verify")


def test_reflexive():
    for name, build in ORACLES.items():
        if name == "Datagolf":
            continue  # Datagolf is oracle-only; it is never a tool output
        result = build().as_oracle(build())
        assert result.ok, f"{name} does not verify against a copy of itself: {result.message}"
        assert result.strength is Strength.EQUIVALENT, \
            f"{name} against itself is only {result.strength.value}"
    print("ok test_reflexive")


def test_no_vacuous_success():
    for oracle_name, tool_name, oracle, tool in cells():
        result = oracle().as_oracle(tool())
        if not result.ok:
            continue
        assert result.values_checked > 0, \
            f"{oracle_name} -> {tool_name} reported success having inspected no values"
        assert result.time_points_checked > 0, \
            f"{oracle_name} -> {tool_name} reported success having inspected no time points"
    print("ok test_no_vacuous_success")


def test_mutants_rejected():
    for oracle_name, tool_name, oracle, _ in cells():
        result = oracle().as_oracle(MUTANTS[tool_name]())
        invisible = MUTANT_INVISIBLE.get((oracle_name, tool_name))
        if invisible is not None:
            assert not result.ok or result.strength in (Strength.CONSISTENT, Strength.UNSUPPORTED), \
                (f"{oracle_name} -> {tool_name} claims {result.strength.value} but cannot "
                 f"see its mutant ({invisible})")
            continue
        assert not result.ok, \
            (f"{oracle_name} -> {tool_name} accepted a mutated tool output at strength "
             f"{result.strength.value}")
    print("ok test_mutants_rejected")


def test_extra_tool_time_point_is_rejected():
    # the direction that used to raise AttributeError: a PDT oracle against a
    # flat tool that reports a time point the oracle never mentions
    oracle = proposition_tree()
    tool = verdicts(Verdicts)
    tool.insert([[GOOD]], 9, 9)
    result = oracle.as_oracle(tool)
    assert not result.ok, "a tool time point absent from the oracle was accepted"

    # and the mirror: a PDT tool may carry extra time points when vacuous
    ok, _ = time_point_pdt_check(verdicts(Verdicts), proposition_tree())
    assert ok, "a vacuous extra PDT time point was rejected"
    print("ok test_extra_tool_time_point_is_rejected")


def test_tuple_shim():
    result = verdicts(Verdicts).as_oracle(verdicts(Verdicts))
    ok, message = result
    assert ok is True and isinstance(message, str), "Comparison no longer unpacks as (ok, message)"
    print("ok test_tuple_shim")


# --- PDT algebra -----------------------------------------------------------
# equality_between_pdts takes two routes: single_level_tree for one variable,
# apply2_reduce_inner for the rest. Both had branches that could not fail (or
# could not pass), and both are invisible to the matrix tests above because the
# lowered fixtures are symmetric. The oracle is always the LEFT tree.

PDT_VARS = ["x", "y"]


def _uniform(value):
    return PDTNode("y", [(PDTSet({"1"}), PDTLeaf(value)),
                         (PDTComplementSet({"1"}), PDTLeaf(value))])


def _leaf(value):
    return PDTTree(PDTLeaf(value))


def _split(for_seven, for_rest):
    return PDTTree(PDTNode("x", [(PDTSet({"7"}), _uniform(for_seven)),
                                 (PDTComplementSet({"7"}), _uniform(for_rest))]))


def _everywhere(value):
    return PDTTree(PDTNode("x", [(PDTComplementSet(set()), _uniform(value))]))


PDT_CASES = [
    # a node that is uniform agrees with the leaf of the same value, in either
    # orientation; the node/leaf direction is the one a Verdicts oracle takes
    # against a tool whose tree is a bare leaf
    ("node(all false) vs leaf false", _everywhere(False), _leaf(False), True),
    ("leaf false vs node(all false)", _leaf(False), _everywhere(False), True),
    ("node(all true) vs leaf true", _everywhere(True), _leaf(True), True),
    ("leaf true vs node(all true)", _leaf(True), _everywhere(True), True),
    # a node that is not uniform never agrees with a leaf
    ("node(7 true) vs leaf false", _split(True, False), _leaf(False), False),
    ("leaf false vs node(7 true)", _leaf(False), _split(True, False), False),
    # node/node, where the merged partition collapses to a single block
    ("node/node all false", _everywhere(False), _everywhere(False), True),
    ("node/node all true", _everywhere(True), _everywhere(True), True),
    ("node/node true vs false", _everywhere(True), _everywhere(False), False),
    # and a block that does not cover the domain must keep its node
    ("node/node 7 true vs 7 false", _split(True, False), _split(False, False), False),
]


def test_pdt_equality_asymmetric():
    for name, left, right, expected in PDT_CASES:
        got = equality_between_pdts(PDT_VARS, left, right)
        assert got == expected, f"equality_between_pdts: {name} gave {got}, expected {expected}"
    print("ok test_pdt_equality_asymmetric")


def test_pdt_equality_multivariable():
    for order, left, right, expected in [
        (["x", "y"], [("7", "1")], [("7", "1")], True),
        (["x", "y"], [("7", "1")], [("8", "1")], False),
        (["x", "y"], [("7", "1")], [("7", "2")], False),
        (["x", "y"], [("7", "1")], [("7", "1"), ("9", "9")], False),
        (["x", "y"], [("7", "1"), ("9", "9")], [("7", "1"), ("9", "9")], True),
        (["x", "y", "z"], [("7", "1", "a")], [("7", "1", "a")], True),
        (["x", "y", "z"], [("7", "1", "a")], [("7", "1", "b")], False),
    ]:
        variable_order = VariableOrder(order)

        def lowered(rows):
            structure = Verdicts(variable_order)
            structure.insert([list(row) for row in rows], 0, 0)
            return verdicts_to_proposition_tree(structure, variable_order).forest[0]

        got = equality_between_pdts(order, lowered(left), lowered(right))
        assert got == expected, \
            f"equality_between_pdts over {order}: {left} vs {right} gave {got}, expected {expected}"
    print("ok test_pdt_equality_multivariable")


def test_pdt_equality_ignores_redundant_blocks():
    """Single variable, so this goes through single_level_tree rather than
    apply2_reduce_inner. A monitor prints one block per value it observed,
    including violating ones; the platform lowers Verdicts into satisfying
    blocks plus a single complement. Real WhyMon output carries dozens of
    violating blocks per time point, so a structural comparison would reject
    every one of them.
    """
    single = ["x"]
    lowered = PDTTree(PDTNode("x", [(PDTSet({"7"}), PDTLeaf(True)),
                                    (PDTComplementSet({"7"}), PDTLeaf(False))]))
    printed = PDTTree(PDTNode("x", [(PDTSet({"7"}), PDTLeaf(True)),
                                    (PDTSet({"9"}), PDTLeaf(False)),
                                    (PDTSet({"5"}), PDTLeaf(False)),
                                    (PDTComplementSet({"7", "9", "5"}), PDTLeaf(False))]))
    assert equality_between_pdts(single, lowered, printed), \
        "blocks that agree with the default must not make the comparison fail"
    assert equality_between_pdts(single, printed, lowered), "and it must be symmetric"

    # the mirror, where the default is true and the exceptions are the false ones
    default_true = PDTTree(PDTNode("x", [(PDTSet({"7"}), PDTLeaf(False)),
                                         (PDTComplementSet({"7"}), PDTLeaf(True))]))
    default_true_padded = PDTTree(PDTNode("x", [(PDTSet({"7"}), PDTLeaf(False)),
                                                (PDTSet({"9"}), PDTLeaf(True)),
                                                (PDTComplementSet({"7", "9"}), PDTLeaf(True))]))
    assert equality_between_pdts(single, default_true, default_true_padded), \
        "redundant true blocks under a true default must not fail either"

    # a block that does NOT agree with the default is a real difference
    disagrees = PDTTree(PDTNode("x", [(PDTSet({"7"}), PDTLeaf(True)),
                                      (PDTSet({"9"}), PDTLeaf(True)),
                                      (PDTComplementSet({"7", "9"}), PDTLeaf(False))]))
    assert not equality_between_pdts(single, lowered, disagrees), \
        "an extra satisfying value must be noticed"

    # a uniform node and the leaf of the same value denote the same function
    assert equality_between_pdts(
        single, PDTTree(PDTNode("x", [(PDTComplementSet(set()), PDTLeaf(False))])), _leaf(False)), \
        "a node that is false everywhere equals the false leaf"
    assert not equality_between_pdts(single, lowered, _leaf(False)), \
        "a node with a satisfying value does not equal the false leaf"
    print("ok test_pdt_equality_ignores_redundant_blocks")


def test_closed_formula_lowering():
    """Zero free variables: Verdicts stores propositions and lowers to a bare
    leaf, which is the shape a fully quantified policy produces. Real
    WhyMyMon output on the GDPR case study is exactly this - 713 time points,
    no partition blocks at all - so the path is worth holding down.
    """
    closed = VariableOrder([])
    oracle = Verdicts(closed)
    for tp in TIME_POINTS:
        oracle.insert([], tp, tp)

    tool = PropositionTree(closed)
    for tp in TIME_POINTS:
        tool.insert(PDTTree(PDTLeaf(True)), tp, tp)

    result = oracle.as_oracle(tool)
    assert result.ok, f"closed-formula comparison failed: {result.message}"
    assert result.values_checked > 0, "closed-formula comparison inspected nothing"

    extra = PropositionTree(closed)
    for tp in TIME_POINTS + (9,):
        extra.insert(PDTTree(PDTLeaf(True)), tp, tp)
    assert not oracle.as_oracle(extra).ok, \
        "a tool time point absent from the oracle was accepted"
    print("ok test_closed_formula_lowering")


# a real WhyMon explanation, taken verbatim from an online Nokia run: three
# nested levels, each partitioning on nothing at all
WHYMON_EXPLANATION = (
    "1282813808:0\nExplanation:\n\u276e\n"
    "data \u2208 Complement of {}\n\u276e\n"
    "x \u2208 Complement of {}\n\u276e\n"
    "y \u2208 Complement of {}\n\u276e\n"
    "SNeg{0}\nVAndL{0}\nVAndL{0}\nVPred(0, delete, [x, db3, y, data])\n"
    "\u276f\n\u276f\n\u276f\n\u276f"
)


def test_parser_normalises_empty_set_literal():
    """ast.literal_eval("{}") yields a dict, and "Complement of {}" is what a
    level that partitions on nothing prints. Left as a dict it reaches
    setc_inter/setc_diff and raises there, so multi-variable comparison of
    real monitor output was impossible.
    """
    assert isinstance(literal_set("{}"), set), "empty set literal must parse as a set"
    assert literal_set("{}") == set()
    assert literal_set("{1, 2}") == {1, 2}
    assert isinstance(resolve_set("Complement of {}").complement_set, set)
    print("ok test_parser_normalises_empty_set_literal")


def test_real_whymon_explanation_compares():
    """End to end on real output: parse, then compare through
    apply2_reduce_inner, which is the path every multi-variable policy takes.
    Each level here is a single all-covering complement block, the shape that
    exercises the single-block collapse.
    """
    parsed = str_to_proposition_tree(WHYMON_EXPLANATION)
    order = parsed.retrieve_order()
    assert order == ["data", "x", "y"], f"unexpected variable order {order}"

    tree = next(iter(parsed.forest.values()))
    assert equality_between_pdts(order, tree, tree), \
        "a real WhyMon tree must equal itself"
    assert not equality_between_pdts(order, tree, PDTTree(PDTLeaf(False))), \
        "a satisfying tree must not equal the false leaf"
    print("ok test_real_whymon_explanation_compares")


def test_gate():
    subset = proposition_tree().as_oracle(verdicts(Verdicts))
    assert subset.meets(Strength.CONSISTENT), "subset should satisfy a consistent floor"
    assert subset.meets(None), "no floor should always be satisfied"
    assert not subset.meets(Strength.EQUIVALENT), "subset should not satisfy an equivalent floor"
    print("ok test_gate")


TESTS = [
    test_no_cell_raises,
    test_declared_strengths,
    test_agreeing_outputs_verify,
    test_reflexive,
    test_no_vacuous_success,
    test_mutants_rejected,
    test_extra_tool_time_point_is_rejected,
    test_pdt_equality_asymmetric,
    test_pdt_equality_multivariable,
    test_pdt_equality_ignores_redundant_blocks,
    test_closed_formula_lowering,
    test_parser_normalises_empty_set_literal,
    test_real_whymon_explanation_compares,
    test_tuple_shim,
    test_gate,
]


def main():
    for test in TESTS:
        test()
    print(f"\nALL {len(TESTS)} COMPARATOR TESTS PASSED")


if __name__ == "__main__":
    main()
