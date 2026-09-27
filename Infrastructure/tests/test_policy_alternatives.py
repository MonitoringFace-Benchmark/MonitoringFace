"""Tests for policy alternatives in case-study instructions. Plain asserts, no
pytest dependency: run with
    Infrastructure/environment/venv/bin/python -m Infrastructure.tests.test_policy_alternatives
Covers parsing of `file: fmt | file: fmt` cells, per-consumer selection over
the real policy-converter graph (native beats converted, fewer steps win, the
earlier alternative wins ties, unreachable falls back to the first option),
the coordinator's instruction parsing and settings iteration, and the oracle
format delegation.
"""
import os
import shutil
import sys
import tempfile
from types import SimpleNamespace

from Archive.Implementations.Oracles.VeriMonOracle.VeriMonOracle import VeriMonOracle
from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats as P
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.AutoConversion.PolicyAlternatives import PolicyAlternatives, parse_policy_alternatives
from Infrastructure.BenchmarkBuilder.Coordinator.CaseStudyCoordinator import CaseStudyCoordinator
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.Monitors.BaseMonitorTemplate import select_policy
from Infrastructure.AutoConversion.AutoPolicyConverter import AutoPolicyConverter
from Infrastructure.constants import PATH_TO_PROJECT, PATH_TO_ARCHIVE, PATH_TO_INSTRUCTIONS, PATH_TO_NAMED_DATA, POLICY_KEY, TRACE_KEY

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

CELL = "Formula/consent.mfotl: mfotl | Formula/consent.tessla: srv-policy"


def project_paths():
    pm = PathManager()
    pm.add_path(PATH_TO_PROJECT, REPO)
    pm.add_path(PATH_TO_ARCHIVE, os.path.join(REPO, "Archive"))
    return pm


def distance(pm, source, target):
    res = AutoPolicyConverter.reachable(pm, source, target)
    return None if res is None else res[2]


def test_converter_graph_premises():
    pm = project_paths()
    assert distance(pm, P.MFOTL, P.OOO_FRAGMENT) == 1
    assert distance(pm, P.SRV_POLICY, P.OOO_FRAGMENT) is None
    assert distance(pm, P.QTL, P.OOO_FRAGMENT) is None
    assert distance(pm, P.UNICODE_MFOTL, P.OOO_FRAGMENT) == 2
    print("ok test_converter_graph_premises")


def raises(fn, fragment):
    try:
        fn()
    except ValueError as e:
        assert fragment in str(e), str(e)
        return
    raise AssertionError(f"expected ValueError containing '{fragment}'")


def test_parse():
    alt = parse_policy_alternatives(CELL)
    assert alt.options == (("Formula/consent.mfotl", P.MFOTL), ("Formula/consent.tessla", P.SRV_POLICY))
    assert parse_policy_alternatives(str(alt)) == alt
    raises(lambda: parse_policy_alternatives("a.mfotl: mfotl | b.mfotl: mfotl"), "distinct formats")
    raises(lambda: parse_policy_alternatives("a.mfotl: mfotl | b.tessla"), "has no format")
    raises(lambda: PolicyAlternatives((("a.mfotl", P.MFOTL),)), "at least two")
    raises(lambda: parse_policy_alternatives("a.mfotl: mfotl | b.x: no-such-format"), "Unknown")
    print("ok test_parse")


def test_plain_settings_pass_through():
    pm = project_paths()
    assert select_policy([P.SRV_POLICY], pm, "f.mfotl", P.MFOTL) == ("f.mfotl", P.MFOTL)
    assert select_policy(None, pm, "f.mfotl", P.MFOTL) == ("f.mfotl", P.MFOTL)
    print("ok test_plain_settings_pass_through")


def test_native_beats_converted():
    pm = project_paths()
    alt = parse_policy_alternatives(CELL)
    assert select_policy([P.SRV_POLICY], pm, alt, None) == ("Formula/consent.tessla", P.SRV_POLICY)
    assert select_policy([P.MFOTL], pm, alt, None) == ("Formula/consent.mfotl", P.MFOTL)
    print("ok test_native_beats_converted")


def test_converted_route_when_no_native():
    pm = project_paths()
    alt = parse_policy_alternatives("Formula/consent.tessla: srv-policy | Formula/consent.mfotl: mfotl")
    assert select_policy([P.OOO_FRAGMENT], pm, alt, None) == ("Formula/consent.mfotl", P.MFOTL)
    print("ok test_converted_route_when_no_native")


def test_fewer_steps_beat_listing_order():
    pm = project_paths()
    alt = parse_policy_alternatives("Formula/c.umfotl: unicode-mfotl | Formula/c.mfotl: mfotl")
    assert select_policy([P.OOO_FRAGMENT], pm, alt, None) == ("Formula/c.mfotl", P.MFOTL)
    print("ok test_fewer_steps_beat_listing_order")


def test_tie_prefers_earlier_alternative():
    pm = project_paths()
    forward = parse_policy_alternatives(CELL)
    backward = parse_policy_alternatives("Formula/consent.tessla: srv-policy | Formula/consent.mfotl: mfotl")
    both = [P.MFOTL, P.SRV_POLICY]
    assert select_policy(both, pm, forward, None)[1] == P.MFOTL
    assert select_policy(both, pm, backward, None)[1] == P.SRV_POLICY
    print("ok test_tie_prefers_earlier_alternative")


def test_unreachable_falls_back_to_first():
    pm = project_paths()
    alt = parse_policy_alternatives("Formula/q.qtl: qtl | Formula/q.tessla: srv-policy")
    assert select_policy([P.OOO_FRAGMENT], pm, alt, None) == ("Formula/q.qtl", P.QTL)
    assert select_policy(None, pm, alt, None) == ("Formula/q.qtl", P.QTL)
    print("ok test_unreachable_falls_back_to_first")


def coordinator_stub(tmp, lines):
    with open(os.path.join(tmp, "instructions.txt"), "w") as f:
        f.write("\n".join(lines) + "\n")
    pm = PathManager()
    pm.add_path(PATH_TO_INSTRUCTIONS, os.path.join(tmp, "instructions.txt"))
    pm.add_path(PATH_TO_NAMED_DATA, os.path.join(tmp, "data"))
    return SimpleNamespace(path_manager=pm, oracle=None, results={})


def test_instruction_parsing_and_iteration(tmp):
    stub = coordinator_stub(tmp, [
        "Trace, Policy, Signature",
        f"Trace/log.log: monpoly, {CELL}, Signature/sig.sig",
        "Trace/log.log: monpoly, Formula/deletion.mfotl: mfotl, Signature/sig.sig",
    ])
    header, instructions = CaseStudyCoordinator._init_instr(stub)
    assert header == [TRACE_KEY, POLICY_KEY, "signature"]
    policy, policy_type = instructions[0][POLICY_KEY]
    assert isinstance(policy, PolicyAlternatives) and policy_type is None
    assert instructions[0][TRACE_KEY] == ("Trace/log.log", InputOutputTraceFormats.MONPOLY)
    assert instructions[1][POLICY_KEY] == ("Formula/deletion.mfotl", P.MFOTL)

    stub.instructions = instructions
    settings = CaseStudyCoordinator.iterate_settings(stub)
    assert settings[0][4] == policy and settings[0][5] is None
    assert settings[1][4:6] == ("Formula/deletion.mfotl", P.MFOTL)
    assert settings[0][6] == "Signature/sig.sig"
    print("ok test_instruction_parsing_and_iteration")


def test_alternatives_only_in_policy_column(tmp):
    stub = coordinator_stub(tmp, [
        "Trace, Policy",
        "Trace/a.log: monpoly | Trace/a.csv: csv, Formula/p.mfotl: mfotl",
    ])
    try:
        CaseStudyCoordinator._init_instr(stub)
    except Exception as e:
        assert "Only the policy column" in str(e), str(e)
    else:
        raise AssertionError("trace alternatives must be rejected")
    print("ok test_alternatives_only_in_policy_column")


def test_oracle_delegates_formats():
    monitor = SimpleNamespace(name="VeriMon", params={},
                              supported_policy_formats=lambda: [P.MFOTL, P.NEGATED_MFOTL])
    oracle = VeriMonOracle(monitor, {})
    pm = project_paths()
    alt = parse_policy_alternatives("Formula/c.tessla: srv-policy | Formula/c.mfotl: mfotl")
    assert oracle.supported_policy_formats() == [P.MFOTL, P.NEGATED_MFOTL]
    assert select_policy(oracle.supported_policy_formats(), pm, alt, None) == ("Formula/c.mfotl", P.MFOTL)
    print("ok test_oracle_delegates_formats")


def main():
    plain = [
        test_converter_graph_premises,
        test_parse,
        test_plain_settings_pass_through,
        test_native_beats_converted,
        test_converted_route_when_no_native,
        test_fewer_steps_beat_listing_order,
        test_tie_prefers_earlier_alternative,
        test_unreachable_falls_back_to_first,
        test_oracle_delegates_formats,
    ]
    with_tmp = [
        test_instruction_parsing_and_iteration,
        test_alternatives_only_in_policy_column,
    ]
    for t in plain:
        t()
    for t in with_tmp:
        tmp = tempfile.mkdtemp(prefix="policy-alt-test-")
        try:
            t(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("\nALL POLICY ALTERNATIVE TESTS PASSED")


if __name__ == "__main__":
    sys.exit(main())
