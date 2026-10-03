"""Tests for the MFOTL -> ooo-fragment policy converter: TimelyMon's syntax
and precedence (operands need no parentheses, multi-variable EXISTS, open
interval ends), the de Bruijn layout, and the rejection of everything outside
the fragment. Plain asserts, no pytest dependency: run with

    python -m Infrastructure.tests.test_ooo_fragment_converter
"""

import sys

from Archive.Implementations.Builders.ProcessorBuilder.PolicyConverters.OOOFragmentConverter.OOOFragmentConverter import (
    convert_mfotl_to_fragment, free_variable_columns)
from Infrastructure.Builders.ProcessorBuilder.PolicyConverters.PolicyConverterTemplate import (
    PolicyTransformationException)


def converts(policy, fragment):
    got = convert_mfotl_to_fragment(policy)
    assert got == fragment, f"{policy!r}\n  got      {got}\n  expected {fragment}"


def same_as(policy, parenthesized):
    assert convert_mfotl_to_fragment(policy) == convert_mfotl_to_fragment(parenthesized), policy


def rejects(policy, fragment):
    try:
        convert_mfotl_to_fragment(policy)
    except PolicyTransformationException as e:
        assert fragment in str(e), str(e)
        return
    raise AssertionError(f"{policy!r} should be rejected ({fragment})")


def test_fully_parenthesized_policies():
    converts("((PREVIOUS[0,*) ((EXISTS y1. (P0(y1))))) AND ((NOT ((P2() AND (P2()))))))",
             "(ANTIJOIN (PREV [0,*] (EXISTS (PRED P0 x0))) (JOIN (PRED P2) (PRED P2)))")


def test_operands_need_no_parentheses():
    # the TimelyMon halves of formalized_streaming_monitor's paired campaigns
    converts("q(u) SINCE[0,5] p(u)", "(SINCE (PRED q x0) [0,5] (PRED p x0))")
    converts("p(u) AND NOT q(u)", "(ANTIJOIN (PRED p x0) (PRED q x0))")
    converts("p(u) UNTIL[0,*) q(u)", "(UNTIL (PRED p x0) [0,*] (PRED q x0))")
    converts("P(x) AND ONCE [1,5] Q(x)", "(JOIN (PRED P x0) (SINCE (EQ 0 0) [1,5] (PRED Q x0)))")
    converts("P(x) AND NOT x = 3", "(FILTEREQ (PRED P x0) true x0 3)")


def test_exists_binds_several_variables():
    converts("EXISTS a, b . R(a, b, x)", "(EXISTS (EXISTS (PRED R x1 x0 x2)))")
    same_as("EXISTS a, b . R(a, b, x)", "EXISTS a . (EXISTS b . (R(a, b, x)))")


def test_precedence_follows_timelymon():
    same_as("P(x) OR Q(x) AND R(x)", "P(x) OR (Q(x) AND R(x))")
    same_as("P(x) SINCE[0,1] Q(x) SINCE[0,2] R(x)", "P(x) SINCE[0,1] (Q(x) SINCE[0,2] R(x))")
    same_as("P(x) AND Q(x) SINCE[0,1] R(x)", "(P(x) AND Q(x)) SINCE[0,1] R(x)")
    # NOT, EXISTS and the unary temporal operators take one operand
    same_as("EXISTS y . P(x, y) AND Q(x)", "(EXISTS y . P(x, y)) AND Q(x)")
    same_as("ONCE [0,1] P(x) AND Q(x)", "(ONCE [0,1] P(x)) AND Q(x)")
    converts("NOT P(x) SINCE[0,3] Q(x)", "(NEGSINCE (PRED P x0) [0,3] (PRED Q x0))")


def test_open_interval_ends_move_inwards():
    converts("ONCE (2,5] P(x)", "(SINCE (EQ 0 0) [3,5] (PRED P x0))")
    converts("ONCE (0,*) P(x)", "(SINCE (EQ 0 0) [1,*] (PRED P x0))")
    converts("ONCE [0,5) P(x)", "(SINCE (EQ 0 0) [0,4] (PRED P x0))")
    rejects("ONCE (2,3) P(x)", "empty interval (2,3)")


def test_single_quoted_strings_are_constants():
    converts("P(x, 'a b')", '(PRED P x0 "a b")')


def test_constructs_outside_the_fragment_are_rejected():
    rejects("P(x, y) AND x < y", "comparison x <")
    rejects("P(x) AND 5 > x", "comparison 5 >")
    # `<` used to be skipped by the tokenizer, turning this into x = 5
    rejects("P(x) AND x <= 5", "comparison x <")
    rejects("c <- CNT t; w (ONCE [0,9] (EXISTS b . log(w, b, t)))", "aggregation")
    rejects("P(x) IMPLIES Q(x)", "unknown connective 'IMPLIES'")
    rejects("P(x) & Q(x)", "unknown connective '&'")


def test_free_variables_in_natural_name_order():
    assert free_variable_columns("P(x10, x2, b) AND (EXISTS y . Q(y, b))") == ["b", "x2", "x10"]


TESTS = [value for name, value in sorted(globals().items()) if name.startswith("test_")]

if __name__ == "__main__":
    for test in TESTS:
        test()
    print(f"{len(TESTS)} test functions passed")
    sys.exit(0)
