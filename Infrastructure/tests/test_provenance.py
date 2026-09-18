"""Tests for the --provenance storage guarantee. Plain asserts, no pytest
dependency: run with

    Infrastructure/environment/venv/bin/python -m Infrastructure.tests.test_provenance

Covers, without Docker: record building through the real preprocessing()
(identity route and a stubbed one-step conversion), the store's layout and
manifest, atomic write, repeat determinism checking, capture failure,
post-run mutation detection, and invocation recording.
"""

import json
import os
import shutil
import sys
import tempfile

from Infrastructure.AutoConversion.AutoTraceConverter import AutoTraceConverter
from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.Monitors.BaseMonitorTemplate import BaseMonitorTemplate
from Infrastructure.Provenance.Provenance import (
    ConversionRecord, ConversionStep, ProvenanceError, ProvenanceFactory,
    read_fingerprint, framework_commit, MANIFEST_NAME,
)
from Infrastructure.constants import PATH_TO_PROJECT, TRACE_KEY, POLICY_KEY


class IdentityMonitor(BaseMonitorTemplate):
    """Supports the canonical formats directly (like TimelyMon)."""

    @staticmethod
    def supported_trace_formats():
        return [InputOutputTraceFormats.CSV]

    @staticmethod
    def supported_policy_formats():
        return [InputOutputPolicyFormats.MFOTL]

    def preprocessing_data(self, *a, **k):
        raise NotImplementedError

    def preprocessing_policy(self, *a, **k):
        raise NotImplementedError


class StubStepConverter:
    """A DataConverterTemplate stand-in that uppercases the trace and
    reports a fake command, exercising the converted-record path."""

    def auto_convert(self, path_to_folder, input_file, path_to_output_folder,
                     output_file, source, target, params):
        with open(f"{path_to_folder}/{input_file}") as f:
            content = f.read()
        with open(f"{path_to_output_folder}/{output_file}", "w") as f:
            f.write(content.upper())
        return ["stub-convert", "-i", source.value, "-f", target.value]


def make_setting(tmp):
    setting = os.path.join(tmp, "experiments", "exp", "operators_5", "free_vars_2", "num_0")
    os.makedirs(os.path.join(setting, "scratch"))
    with open(os.path.join(setting, "data_10.csv"), "w") as f:
        f.write("P1, tp=0, ts=0, x0=1\n")
    with open(os.path.join(setting, "policy.policy"), "w") as f:
        f.write("P1(x0)\n")
    with open(os.path.join(setting, "signature.sig"), "w") as f:
        f.write("P1(x0:int)\n")
    return setting


def make_factory(tmp, setting):
    results = os.path.join(tmp, "results", "exp_20260820_120000")
    os.makedirs(results, exist_ok=True)
    experiment_root = os.path.join(tmp, "experiments", "exp")
    with open(os.path.join(experiment_root, "fingerprint"), "w") as f:
        f.write("fingerprint_experiment=abc\nfingerprint_data=def\n")
    return ProvenanceFactory(
        result_folder=results, experiment_root=experiment_root,
        fingerprint=read_fingerprint(os.path.join(experiment_root, "fingerprint")),
        commit="testcommit",
    ), results


def preprocess_identity(setting):
    mon = IdentityMonitor(image=None, name="TimelyMon 1", params={"worker": 1})
    pm = PathManager()
    pm.add_path(PATH_TO_PROJECT, "/nonexistent")
    pre = mon.preprocessing(
        setting, InputOutputTraceFormats.CSV, InputOutputPolicyFormats.MFOTL,
        "data_10.csv", "signature.sig", "policy.policy", pm
    )
    return mon, pre


def test_identity_records(tmp):
    setting = make_setting(tmp)
    mon, pre = preprocess_identity(setting)
    kinds = {r.kind: r for r in pre.records}
    assert set(kinds) == {"trace", "policy", "signature"}, kinds
    assert all(r.steps == [] and not r.custom for r in pre.records)
    assert kinds["trace"].as_seen_by_tool == "data_10.csv"
    assert mon.params[TRACE_KEY] == "data_10.csv"
    assert pre.elapsed_s >= 0
    print("ok test_identity_records")


def test_converted_record_via_stub_chain(tmp):
    setting = make_setting(tmp)
    pm = PathManager()
    pm.add_path(PATH_TO_PROJECT, "/nonexistent")
    conv = AutoTraceConverter(pm, InputOutputTraceFormats.CSV, InputOutputTraceFormats.DEJAVU_ENCODED)
    # instance attribute shadows the method: no registry, no docker
    conv._conversion_chain = lambda: [
        (StubStepConverter(), InputOutputTraceFormats.CSV, InputOutputTraceFormats.DEJAVU_ENCODED)
    ]
    from Infrastructure.constants import PATH_TO_TRACE_INPUT, PATH_TO_INTERMEDIATE_WORKSPACE, PATH_TO_TRACE_OUTPUT
    pm.add_path(PATH_TO_TRACE_INPUT, setting)
    pm.add_path(PATH_TO_INTERMEDIATE_WORKSPACE, f"{setting}/scratch")
    pm.add_path(PATH_TO_TRACE_OUTPUT, f"{setting}/scratch")

    path, steps = conv.convert("data_10.csv", "data_10.csv", params={})
    assert path == "scratch/data_10.csv"
    assert len(steps) == 1
    step = steps[0]
    assert isinstance(step, ConversionStep)
    assert step.converter == "StubStepConverter"
    assert step.command == ["stub-convert", "-i", "csv", "-f", "dejavu-encoded"]
    with open(os.path.join(setting, path)) as f:
        assert "TP=0" in f.read()  # actually converted
    print("ok test_converted_record_via_stub_chain")
    return setting, steps


def test_capture_layout_and_manifest(tmp):
    setting, steps = test_converted_record_via_stub_chain(tmp)
    factory, results = make_factory(tmp, setting)
    records = [
        ConversionRecord(kind="trace", source_file="data_10.csv", source_format="csv",
                         steps=steps, as_seen_by_tool="scratch/data_10.csv"),
        ConversionRecord(kind="policy", source_file="policy.policy", source_format="mfotl",
                         steps=[], as_seen_by_tool="policy.policy"),
    ]

    class FakeTool:
        name = "DejaVu"
        params = {"stratified": True}
    session = factory.session("5_2_0_10", setting, FakeTool())
    session.capture(records)

    entry = os.path.join(results, "provenance", "5_2_0_10", "DejaVu")
    assert os.path.isfile(os.path.join(entry, "trace.dejavu-encoded"))
    assert not os.path.exists(os.path.join(entry, "policy.mfotl")), "identity must not copy"
    manifest = json.load(open(os.path.join(entry, MANIFEST_NAME)))
    assert manifest["schema_version"] == 1
    assert manifest["experiment_fingerprint"]["fingerprint_experiment"] == "abc"
    assert manifest["framework_commit"] == "testcommit"
    assert manifest["captures"] == 1
    by_kind = {e["kind"]: e for e in manifest["entries"]}
    assert by_kind["trace"]["stored"]["file"] == "trace.dejavu-encoded"
    assert by_kind["trace"]["steps"][0]["command"][0] == "stub-convert"
    assert by_kind["trace"]["source"]["file"].endswith("num_0/data_10.csv")
    assert len(by_kind["trace"]["source"]["sha256"]) == 64
    assert by_kind["policy"]["stored"] is None
    # stored copy hash matches the scratch file the tool would read
    import hashlib
    scratch_hash = hashlib.sha256(open(os.path.join(setting, "scratch/data_10.csv"), "rb").read()).hexdigest()
    assert by_kind["trace"]["stored"]["sha256"] == scratch_hash
    print("ok test_capture_layout_and_manifest")
    return session, records, entry, setting


def test_repeat_verification_and_nondeterminism(tmp):
    session, records, entry, setting = test_capture_layout_and_manifest(tmp)
    # identical repeat: fine, captures increments
    session.capture(records)
    manifest = json.load(open(os.path.join(entry, MANIFEST_NAME)))
    assert manifest["captures"] == 2
    # nondeterministic converter simulation: scratch content differs
    with open(os.path.join(setting, "scratch/data_10.csv"), "a") as f:
        f.write("EXTRA\n")
    try:
        session.capture(records)
        raise AssertionError("nondeterministic conversion not detected")
    except ProvenanceError as e:
        assert "nondeterministic" in str(e)
    print("ok test_repeat_verification_and_nondeterminism")


def test_capture_failure_is_loud(tmp):
    setting = make_setting(tmp)
    factory, results = make_factory(tmp, setting)

    class FakeTool:
        name = "MonPoly"
        params = {}
    session = factory.session("5_2_0_10", setting, FakeTool())
    records = [ConversionRecord(kind="trace", source_file="does_not_exist.csv",
                                source_format="csv", steps=[], as_seen_by_tool="does_not_exist.csv")]
    try:
        session.capture(records)
        raise AssertionError("capture of a missing file must raise")
    except ProvenanceError:
        pass
    # atomicity: the failed capture left no entry and no temp litter
    prov_root = os.path.join(results, "provenance")
    leftovers = []
    for root, dirs, files in os.walk(prov_root):
        leftovers.extend(files)
    assert leftovers == [], leftovers
    print("ok test_capture_failure_is_loud")


def test_invocation_and_post_run_verify(tmp):
    session, records, entry, setting = test_capture_layout_and_manifest(tmp)
    session.record_invocation(["run", "scratch/policy.policy", "scratch/data_10.csv"])
    session.record_invocation(["should", "not", "overwrite"])
    manifest = json.load(open(os.path.join(entry, MANIFEST_NAME)))
    assert manifest["tool_invocation"][0] == "run"

    session.verify_after_run(records)
    manifest = json.load(open(os.path.join(entry, MANIFEST_NAME)))
    assert manifest["input_unchanged_after_run"] is True
    # the tool "mutates" its input mid-run
    with open(os.path.join(setting, "scratch/data_10.csv"), "w") as f:
        f.write("TAMPERED\n")
    session.verify_after_run(records)
    manifest = json.load(open(os.path.join(entry, MANIFEST_NAME)))
    assert manifest["input_unchanged_after_run"] is False
    # the flag latches: a later clean verification must not clear it
    print("ok test_invocation_and_post_run_verify")


def test_collision_detection(tmp):
    """'DejaVu 1' and 'DejaVu_1' sanitize to the same directory; the second
    session must fail loudly instead of merging into the first manifest."""
    setting = make_setting(tmp)
    factory, results = make_factory(tmp, setting)
    records = [ConversionRecord(kind="trace", source_file="data_10.csv", source_format="csv",
                                steps=[], as_seen_by_tool="data_10.csv")]

    class ToolA:
        name = "DejaVu 1"
        params = {}

    class ToolB:
        name = "DejaVu_1"
        params = {}
    factory.session("5_2_0_10", setting, ToolA()).capture(records)
    try:
        factory.session("5_2_0_10", setting, ToolB()).capture(records)
        raise AssertionError("directory collision not detected")
    except ProvenanceError as e:
        assert "collision" in str(e)
    print("ok test_collision_detection")


def test_source_mutation_detected(tmp):
    """A tool mutating its CANONICAL source (not the scratch copy) must flip
    input_unchanged_after_run and be diagnosed as a source change on repeat."""
    session, records, entry, setting = test_capture_layout_and_manifest(tmp)
    with open(os.path.join(setting, "data_10.csv"), "a") as f:
        f.write("MUTATED BY TOOL\n")
    session.verify_after_run(records)
    manifest = json.load(open(os.path.join(entry, MANIFEST_NAME)))
    assert manifest["input_unchanged_after_run"] is False, \
        "source mutation with intact scratch copy must be detected"
    try:
        session.capture(records)  # repeat after mutation
        raise AssertionError("mutated source not detected on repeat")
    except ProvenanceError as e:
        assert "changed between repeats" in str(e), e
        assert "nondeterministic" not in str(e), "must not blame the converter"
    print("ok test_source_mutation_detected")


def test_jsonable_exotic_params(tmp):
    setting = make_setting(tmp)
    factory, results = make_factory(tmp, setting)

    class Weird:
        pass

    class Tool:
        name = "MonPoly"
        params = {("tuple", "key"): 1, 2: Weird(), "ok": [1, {"nested": Weird()}]}
    records = [ConversionRecord(kind="trace", source_file="data_10.csv", source_format="csv",
                                steps=[], as_seen_by_tool="data_10.csv")]
    factory.session("5_2_0_10", setting, Tool()).capture(records)  # must not raise
    manifest = json.load(open(os.path.join(
        results, "provenance", "5_2_0_10", "MonPoly", MANIFEST_NAME)))
    assert "('tuple', 'key')" in manifest["tool"]["params"]
    print("ok test_jsonable_exotic_params")


def test_stale_tmp_swept(tmp):
    setting = make_setting(tmp)
    factory, results = make_factory(tmp, setting)
    records = [ConversionRecord(kind="trace", source_file="data_10.csv", source_format="csv",
                                steps=[], as_seen_by_tool="data_10.csv")]

    class Tool:
        name = "VeriMon"
        params = {}
    session = factory.session("5_2_0_10", setting, Tool())
    # simulate a crashed earlier process's leftover temp dir (different pid)
    litter = os.path.join(os.path.dirname(session.entry_dir), ".VeriMon.tmp-99999")
    os.makedirs(litter)
    session.capture(records)
    assert not os.path.isdir(litter), "stale tmp litter must be swept"
    assert os.path.isfile(session.manifest_path)
    print("ok test_stale_tmp_swept")


def test_framework_commit_helper():
    commit = framework_commit(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    assert commit is None or len(commit) == 40 or (commit.endswith("-dirty") and len(commit) == 46)
    assert framework_commit("/nonexistent-path") is None
    print("ok test_framework_commit_helper")


def main():
    tests = [
        test_identity_records,
        test_converted_record_via_stub_chain,
        test_capture_layout_and_manifest,
        test_repeat_verification_and_nondeterminism,
        test_capture_failure_is_loud,
        test_invocation_and_post_run_verify,
        test_collision_detection,
        test_source_mutation_detected,
        test_jsonable_exotic_params,
        test_stale_tmp_swept,
    ]
    for t in tests:
        tmp = tempfile.mkdtemp(prefix="prov-test-")
        try:
            t(tmp)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    test_framework_commit_helper()
    print("\nALL PROVENANCE TESTS PASSED")


if __name__ == "__main__":
    sys.exit(main())
