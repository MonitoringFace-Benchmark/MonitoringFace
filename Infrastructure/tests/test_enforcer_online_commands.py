"""Tests for the online commands of the enforcers measured on the EnfGuard
benchmark suite (Archive/Experiments/enforcement_suite). Plain asserts, no
pytest dependency: run with

    Infrastructure/environment/venv/bin/python -m Infrastructure.tests.test_enforcer_online_commands

Covers MonPoly's command with and without a latency marker (the marker's
echo replaces -verbose's step lines), the Enfpoly, EnfGuard and Dogwood
commands, and the files that come with a policy (its functions and their
Python requirements): read from instructions.txt, recorded in provenance,
copied next to the policy into the online image, and passed to EnfGuard; also
the instructions-file format of Dogwood policies.
"""

import sys

from Archive.Implementations.Monitors.Dogwood.Dogwood import Dogwood
from Archive.Implementations.Monitors.EnfGuard.EnfGuard import EnfGuard
from Archive.Implementations.Monitors.Enfpoly.Enfpoly import Enfpoly
from Archive.Implementations.Monitors.MonPoly.MonPoly import MonPoly
from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats, \
    str_to_policy_inout_format, policy_inout_format_to_str
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.Frontend.Parser.YamlParser import YamlParser
from Infrastructure.constants import POLICY_COMPANIONS_KEY, POLICY_KEY, SIGNATURE_KEY, TRACE_KEY

MARKER = '> LATENCY "at time point" <'


def params(extra=None, **tool):
    raw = {"format": "log", "response_mode": "process-step", "output_collection_mode": "after-delimiter", **tool}
    return YamlParser.parse_tool_params(None, {"params": {**(extra or {}), "OnlineExperimentContractTool": raw}})


def command(cls, p):
    cmd, name = cls(None, cls.__name__, p).construct_online_command()
    assert name is None
    return cmd


def test_monpoly_without_marker_keeps_verbose_steps():
    cmd = command(MonPoly, params())
    assert cmd[-3:] == ["-verbose", "-nofilteremptytp", "-nofilterrel"], cmd
    print("ok test_monpoly_without_marker_keeps_verbose_steps")


def test_monpoly_with_marker_drops_verbose_steps():
    cmd = command(MonPoly, params({"ignore_parse_errors": True}, latency_marker=MARKER))
    assert cmd == ["-sig", "additional/signature.sig", "-formula", "additional/policy.policy",
                   "-ignore_parse_errors"], cmd
    print("ok test_monpoly_with_marker_drops_verbose_steps")


def test_enfpoly_enforces():
    assert command(Enfpoly, params({"ignore_parse_errors": True}, latency_marker=MARKER)) == [
        "-enforce", "-sig", "additional/signature.sig", "-formula", "additional/policy.policy",
        "-ignore_parse_errors"]
    print("ok test_enfpoly_enforces")


def test_enfguard_online():
    assert command(EnfGuard, params(latency_marker=MARKER)) == [
        "-sig", "additional/signature.sig", "-formula", "additional/policy.policy"]
    print("ok test_enfguard_online")


def with_companions(p, **companions):
    p[POLICY_COMPANIONS_KEY] = companions
    return p


def test_enfguard_reads_the_policys_functions():
    p = with_companions(params(latency_marker=MARKER), functions="Functions/functions.py")
    mon = EnfGuard(None, "EnfGuard", p)
    assert mon.construct_online_command()[0][-2:] == ["-func", "additional/functions.py"]
    p[SIGNATURE_KEY], p[POLICY_KEY], p[TRACE_KEY] = "Signature/s.sig", "Formula/p.mfotl", "Trace/t.log"
    assert mon.construct_offline_command()[0][-2:] == ["-func", "Functions/functions.py"]
    print("ok test_enfguard_reads_the_policys_functions")


def test_instructions_carry_policy_companions():
    import os
    import tempfile
    from Infrastructure.BenchmarkBuilder.Coordinator.CaseStudyCoordinator import CaseStudyCoordinator
    from Infrastructure.constants import PATH_TO_INSTRUCTIONS, PATH_TO_NAMED_DATA
    with tempfile.TemporaryDirectory() as root:
        path = os.path.join(root, "instructions.txt")
        with open(path, "w") as f:
            f.write("Trace, Policy, Signature, Functions, Requirements\n"
                    "Trace/t.log: monpoly, Formula/a.mfotl: mfotl, Signature/s.sig, Functions/f.py, Functions/requirements.txt\n"
                    "Trace/t.log: monpoly, Formula/b.mfotl: mfotl, Signature/s.sig, , \n")
        coordinator = CaseStudyCoordinator.__new__(CaseStudyCoordinator)
        coordinator.oracle, coordinator.results = None, {}
        coordinator.path_manager = PathManager()
        coordinator.path_manager.add_path(PATH_TO_INSTRUCTIONS, path)
        coordinator.path_manager.add_path(PATH_TO_NAMED_DATA, os.path.join(root, "data"))
        coordinator.header, coordinator.instructions = coordinator._init_instr()
        assert coordinator.policy_companions(0) == {
            "functions": "Functions/f.py", "requirements": "Functions/requirements.txt"}
        assert coordinator.policy_companions(1) == {}
    print("ok test_instructions_carry_policy_companions")


def test_policy_companions_reach_the_online_image():
    import os
    import tempfile
    from Infrastructure.Builders import OnlineExperiementPipeline as pipeline
    companions = {"functions": "Functions/functions.py", "requirements": "Functions/requirements.txt"}
    with tempfile.TemporaryDirectory() as setting, tempfile.TemporaryDirectory() as build:
        for rel in ("Formula/p.mfotl", "Signature/s.sig", *companions.values(), "data.log"):
            os.makedirs(os.path.dirname(os.path.join(setting, rel)) or setting, exist_ok=True)
            open(os.path.join(setting, rel), "w").write(rel)
        built = {}
        saved = (pipeline.extract_binary, pipeline.build_image_wrapper, pipeline.image_building)
        pipeline.extract_binary = lambda *a, **k: None
        pipeline.build_image_wrapper = lambda *a, **k: True
        pipeline.image_building = lambda image_name, build_dir, args=None: built.update(args=args)
        try:
            pipeline.build_pipeline(
                tool_image_manager=type("Image", (), {"get_image_name": lambda self: "tool"})(),
                path_to_build=build, path_to_archive=os.path.join(os.getcwd(), "Archive"),
                data_source="data.log", path_to_folder=setting, policy_file="Formula/p.mfotl",
                signature_file="Signature/s.sig", target_image_name="target", policy_companions=companions)
        finally:
            pipeline.extract_binary, pipeline.build_image_wrapper, pipeline.image_building = saved
        additional = os.path.join(build, "OnlineExperimentDriver", "additional")
        assert sorted(os.listdir(additional)) == ["functions.py", "policy.policy", "requirements.txt", "signature.sig"]
        assert open(os.path.join(additional, "functions.py")).read() == "Functions/functions.py"
        assert built["args"] == {"POLICY_REQUIREMENTS": "requirements.txt"}
    print("ok test_policy_companions_reach_the_online_image")


def test_policy_companions_are_recorded():
    import os
    import tempfile
    from Infrastructure.constants import PATH_TO_PROJECT
    with tempfile.TemporaryDirectory() as setting:
        for rel in ("Formula/p.mfotl", "Signature/s.sig", "Functions/functions.py", "Trace/t.log"):
            os.makedirs(os.path.dirname(os.path.join(setting, rel)), exist_ok=True)
            open(os.path.join(setting, rel), "w").write(rel)
        pm = PathManager()
        pm.add_path(PATH_TO_PROJECT, os.getcwd())
        mon = EnfGuard(None, "EnfGuard", with_companions(params(), functions="Functions/functions.py"))
        pre = mon.preprocessing(setting, InputOutputTraceFormats.MONPOLY, InputOutputPolicyFormats.MFOTL,
                                "Trace/t.log", "Signature/s.sig", "Formula/p.mfotl", pm)
        kinds = {r.kind: r.source_file for r in pre.records}
        assert kinds["policy-functions"] == "Functions/functions.py", kinds
    print("ok test_policy_companions_are_recorded")


def test_dogwood_policies():
    assert command(Dogwood, params(latency_marker=MARKER)) == [
        "-sig", "additional/signature.sig", "-formula", "additional/policy.policy"]
    assert str_to_policy_inout_format("dogwood") == InputOutputPolicyFormats.DOGWOOD
    assert policy_inout_format_to_str(InputOutputPolicyFormats.DOGWOOD) == "dogwood"
    assert Dogwood.supported_policy_formats() == [InputOutputPolicyFormats.DOGWOOD]
    print("ok test_dogwood_policies")


TESTS = [
    test_monpoly_without_marker_keeps_verbose_steps,
    test_monpoly_with_marker_drops_verbose_steps,
    test_enfpoly_enforces,
    test_enfguard_online,
    test_enfguard_reads_the_policys_functions,
    test_instructions_carry_policy_companions,
    test_policy_companions_reach_the_online_image,
    test_policy_companions_are_recorded,
    test_dogwood_policies,
]

if __name__ == "__main__":
    for test in TESTS:
        test()
    print(f"\n{len(TESTS)} test functions passed")
    sys.exit(0)
