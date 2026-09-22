from typing import Tuple, List, Union

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Strength import Comparison, Strength
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.OooVerdicts import OooVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PDTLeaf, PDTComplementSet, PDTSet, PDTNode, PropositionTree, PDTTree
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.Assignment import Assignment
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.Proposition import Proposition
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrdering, \
    VariableOrder


def pdt_to_verdicts_inner(oracle: PropositionTree, other: Union[Verdicts, OooVerdicts]) -> Comparison:
    strength = Strength.SUBSET
    ok, txt = time_point_pdt_check(oracle, other)
    if not ok:
        return Comparison(False, txt, strength)

    intersection_set = set(oracle.time_points().keys()) & set(other.time_points().keys())
    time_points = 0
    values = 0
    for tp in sorted(intersection_set):
        oracle_pdt = oracle.retrieve(tp)
        other_verdict = other.retrieve(tp)
        if other_verdict is None:
            if oracle_pdt is None:
                continue
            return Comparison(False, f"Tool is missing verdict at time point {tp}",
                              strength, time_points, values)

        verdicts = other_verdict[2]
        if oracle_pdt is None:
            if not verdicts:
                continue
            return Comparison(False, f"Oracle has no tree at time point {tp}",
                              strength, time_points, values)

        time_points += 1
        for v in verdicts:
            values += 1
            if not oracle_pdt.check_assignment(v):
                return Comparison(False, f"Tool has different verdict for {v} at time point {tp}",
                                  strength, time_points, values)

    return Comparison(True, "Tool output is a subset", strength, time_points, values)


def verdicts_to_verdicts_inner(oracle: Union[Verdicts, OooVerdicts], other: Union[OooVerdicts, Verdicts]) -> Comparison:
    strength = Strength.EQUIVALENT
    ok, txt = time_point_check(oracle, other)
    if not ok:
        return Comparison(False, txt, strength)

    time_points = 0
    values = 0
    for time_point in sorted(oracle.time_points().keys()):
        oracle_val = oracle.retrieve(time_point)
        tuple_val = other.retrieve(time_point)

        if oracle_val is None and tuple_val is None:
            continue
        elif oracle_val is None and tuple_val is not None:
            return Comparison(False, f"Tool has additional verdicts at time point {time_point}",
                              strength, time_points, values)
        elif oracle_val is not None and tuple_val is None:
            return Comparison(False, f"Tool is missing verdicts at time point {time_point}",
                              strength, time_points, values)

        s_o_v = sorted(oracle_val[2])
        o_o_v = sorted(tuple_val[2])
        time_points += 1
        values += len(o_o_v)

        if s_o_v != o_o_v:
            return Comparison(
                False,
                f"Verdict values differ at time point {oracle_val[1]} =>\nOracle {oracle_val[2]}\nTool {tuple_val[2]}",
                strength, time_points, values)
    return Comparison(True, "Verified", strength, time_points, values)


def verdicts_to_prop_list_inner(oracle: Union[Verdicts, OooVerdicts], other: PropositionList) -> Comparison:
    """A PropositionList records one Boolean per time-point where the monitor
    reported something. It agrees with a verdict-bearing oracle when that
    Boolean holds exactly where the oracle's verdict set at the time-point is
    non-empty. `prop_list` is read directly because PropositionList.retrieve
    returns (tp, ts, prop) while Verdicts.retrieve returns (ts, tp, values).

    CONSISTENT, not EQUIVALENT: a PropositionList carries no assignments, so
    the strongest available statement is that its Booleans agree with where
    the oracle has verdicts, never that the two outputs agree.
    """
    strength = Strength.CONSISTENT
    ok, txt = time_point_check(oracle, other)
    if not ok:
        return Comparison(False, txt, strength)

    time_points = 0
    values = 0
    for time_point in sorted(oracle.time_points().keys()):
        oracle_val = oracle.retrieve(time_point)
        other_val = other.prop_list.get(time_point)

        if oracle_val is None and other_val is None:
            continue
        elif oracle_val is None and other_val is not None:
            return Comparison(False, f"Tool has additional verdicts at time point {time_point}",
                              strength, time_points, values)
        elif oracle_val is not None and other_val is None:
            return Comparison(False, f"Tool is missing verdicts at time point {time_point}",
                              strength, time_points, values)

        time_points += 1
        values += 1
        expected = len(oracle_val[2]) > 0
        if bool(other_val.value) != expected:
            return Comparison(
                False,
                f"Tool proposition {other_val.value} at time point {time_point} contradicts "
                f"the oracle's {len(oracle_val[2])} verdicts",
                strength, time_points, values)
    return Comparison(True, "Verified", strength, time_points, values)


def prop_list_to_verdicts_inner(oracle: PropositionList, other: Union[Verdicts, OooVerdicts]) -> Comparison:
    """Mirror of verdicts_to_prop_list_inner with the PropositionList as the
    oracle: its Boolean must hold exactly where the tool reports verdicts.
    CONSISTENT for the same reason: the oracle cannot see assignments."""
    strength = Strength.CONSISTENT
    ok, txt = time_point_check(oracle, other)
    if not ok:
        return Comparison(False, txt, strength)

    time_points = 0
    values = 0
    for time_point in sorted(oracle.time_points().keys()):
        oracle_val = oracle.prop_list.get(time_point)
        other_val = other.retrieve(time_point)

        if oracle_val is None and other_val is None:
            continue
        elif oracle_val is None and other_val is not None:
            return Comparison(False, f"Tool has additional verdicts at time point {time_point}",
                              strength, time_points, values)
        elif oracle_val is not None and other_val is None:
            return Comparison(False, f"Tool is missing verdicts at time point {time_point}",
                              strength, time_points, values)

        time_points += 1
        values += 1
        if bool(oracle_val.value) != (len(other_val[2]) > 0):
            return Comparison(
                False,
                f"Tool reports {len(other_val[2])} verdicts at time point {time_point} but "
                f"the oracle proposition is {oracle_val.value}",
                strength, time_points, values)
    return Comparison(True, "Verified", strength, time_points, values)


def time_point_check(oracle: AbstractOutputStructure, other: AbstractOutputStructure) -> Tuple[bool, str]:
    oracle_tps = set(oracle.time_points().keys())
    other_tps = set(other.time_points().keys())

    if oracle_tps != other_tps:
        missing_from_tool = oracle_tps - other_tps
        missing_from_oracle = other_tps - oracle_tps
        if missing_from_tool:
            return False, f"Tool is missing time points from oracle: {missing_from_tool}"
        if missing_from_oracle:
            return False, f"Oracle is missing time points from tool: {missing_from_oracle}"
    return True, "Verified"


def time_point_pdt_check(oracle: AbstractOutputStructure, tool: AbstractOutputStructure) -> Tuple[bool, str]:
    complement = set(tool.time_points().keys()) - set(oracle.time_points().keys())
    for tp in sorted(complement):
        if tool.has_verdicts(tp):
            return False, f"Tool has verdicts at time point {tp}, absent from the oracle"
    return True, "Verified"


def time_point_pdt_pdt_check(oracle: AbstractOutputStructure, other: AbstractOutputStructure) -> Tuple[bool, str]:
    oracle_tps = set(oracle.time_points())
    other_tps = set(other.time_points())

    if oracle_tps != other_tps:
        missing_from_tool = set(oracle_tps) - set(other_tps)
        missing_from_oracle = set(other_tps) - set(oracle_tps)
        if missing_from_tool:
            return False, f"Tool is missing time points from oracle: {missing_from_tool}"
        if missing_from_oracle:
            return False, f"Oracle is missing time points from tool: {missing_from_oracle}"
    return True, "Verified"


def verdicts_to_proposition_tree(verdicts: Union[Verdicts, OooVerdicts], new_order: VariableOrdering):
    values = []
    for tp in sorted(verdicts.time_points().keys()):
        ts, _, vals = verdicts.retrieve(tp)
        values.append([ts, tp, vals])

    pdt = PropositionTree(new_order)
    return to_tree_inner(values, pdt)


def to_tree_inner(values, pdt: PropositionTree):
    for (ts, tp, val) in values:
        pdt.tp_to_ts[tp] = ts
        if val and isinstance(val[0], Proposition):
            pdt.forest[tp] = PDTTree(PDTLeaf(value=val[0].value))
        else:
            assignments = list(map(lambda ass: ass.retrieve_order(new_order=pdt.variable_order), val))
            pdt.forest[tp] = PDTTree(_pdt_subtree_recurse(vars_=pdt.retrieve_order(), assignments=assignments))
    return pdt


def _pdt_subtree_recurse(vars_: List[str], assignments: List[Assignment]):
    if not vars_:
        return PDTLeaf(len(assignments) > 0)

    var_ = vars_[0]
    remaining = vars_[1:]

    value_to_assignments = {}
    for assignment in assignments:
        val = assignment.retrieve_value(var_)
        if val not in value_to_assignments:
            value_to_assignments[val] = []
        value_to_assignments[val].append(assignment)

    choices = []
    for elem, matching in value_to_assignments.items():
        subtree = _pdt_subtree_recurse(remaining, matching)
        choices.append((PDTSet({elem}), subtree))

    choices.append((PDTComplementSet(set(value_to_assignments.keys())), PDTLeaf(False)))
    return PDTNode(var_, choices)
