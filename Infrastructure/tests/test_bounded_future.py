"""Tests for bounding unbounded future operators for VeriMon (BoundedFuture).

VeriMon rejects EVENTUALLY/SOMETIMES, ALWAYS, UNTIL and RELEASE with an
unbounded interval. On a finite trace, `[a,*)` and `[a,C]` agree when C is at
least the trace's timestamp span, and VeriMon closes the trace at the end of
the log, so the bounded formula gives the unbounded formula's verdicts.

Plain asserts, no pytest dependency: run with

    python -m Infrastructure.tests.test_bounded_future

The end-to-end test runs VeriMon in Docker; it is skipped unless the image is
present (override with VERIMON_IMAGE). Its work directory lies under the
project root, which Docker Desktop shares.
"""

import os
import shutil
import subprocess
import sys
import tempfile

from Archive.Implementations.Monitors.BoundedFuture import (
    bound_policy_to_trace, bound_unbounded_future, timestamp_span)
from Archive.Implementations.Monitors.VeriMon.VeriMon import VeriMon
from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.Monitors.BaseMonitorTemplate import BaseMonitorTemplate
from Infrastructure.Provenance.Provenance import ConversionRecord, PreprocessingResult
from Infrastructure.constants import POLICY_KEY, TRACE_KEY, TRACE_TARGET_FORMAT

VERIMON_IMAGE = os.environ.get("VERIMON_IMAGE", "monpoly_bc752d37f1d4560b5667eddac9dd1670451b758e_offline_mf_image")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LOG = "@0 A(1);\n@1 A(2);\n@2 B(1);\n@5 A(3);\n@7 A(1);\n@8 B(2);\n"


def test_explicit_unbounded_intervals_end_at_the_horizon():
    assert bound_unbounded_future("A(x0,x1) UNTIL [0,*) B(x0,x1)", 999) == ("A(x0,x1) UNTIL [0,999] B(x0,x1)", 1)
    assert bound_unbounded_future("EVENTUALLY [2,*) A(x)", 999) == ("EVENTUALLY [2,999] A(x)", 1)
    assert bound_unbounded_future("(NOT A(x)) UNTIL(1,*) B(x)", 9) == ("(NOT A(x)) UNTIL(1,9] B(x)", 1)
    assert bound_unbounded_future("SOMETIMES[1,*) A(x)", 9) == ("SOMETIMES[1,9] A(x)", 1)
    assert bound_unbounded_future("A(x) RELEASE[0,*) B(x)", 9) == ("A(x) RELEASE[0,9] B(x)", 1)
    assert bound_unbounded_future("ALWAYS[0,*) A(x)", 9) == ("ALWAYS[0,9] A(x)", 1)


def test_omitted_intervals_are_unbounded():
    assert bound_unbounded_future("EVENTUALLY A(x)", 7) == ("EVENTUALLY[0,7] A(x)", 1)
    assert bound_unbounded_future("A(x) UNTIL B(x)", 7) == ("A(x) UNTIL[0,7] B(x)", 1)
    # a parenthesised operand is not an interval
    assert bound_unbounded_future("A(x) UNTIL (B(x) AND C(x))", 7) == ("A(x) UNTIL[0,7] (B(x) AND C(x))", 1)


def test_bounded_next_and_past_operators_stay():
    for formula in ("EVENTUALLY[0,5s] A(x)", "A(x) UNTIL (0,5] B(x)", "NEXT[0,*) A(x)", "NEXT A(x)",
                    "ONCE[2,*) A(x)", "A(x) SINCE [0,*) B(x)", "PAST_ALWAYS[0,3] A(x)", "HISTORICALLY A(x)",
                    "UNTILX(x) AND EVENTUALLYY(x)"):
        assert bound_unbounded_future(formula, 7) == (formula, 0), formula


def test_aggregations_units_and_short_traces():
    agg = "c <- CNT x0; x1 (A(x0,x1) UNTIL [0,*) B(x0,x1))"
    assert bound_unbounded_future(agg, 50) == ("c <- CNT x0; x1 (A(x0,x1) UNTIL [0,50] B(x0,x1))", 1)
    # the upper bound never falls below the lower one
    assert bound_unbounded_future("EVENTUALLY[5,*) A(x)", 3) == ("EVENTUALLY[5,5] A(x)", 1)
    assert bound_unbounded_future("EVENTUALLY[1m,*) A(x)", 30) == ("EVENTUALLY[1m,60] A(x)", 1)
    nested = "EVENTUALLY (A(x) UNTIL[2,*) EVENTUALLY[0,3] B(x))"
    assert bound_unbounded_future(nested, 10) == ("EVENTUALLY[0,10] (A(x) UNTIL[2,10] EVENTUALLY[0,3] B(x))", 2)


def _folder(files):
    folder = tempfile.mkdtemp()
    for name, content in files.items():
        os.makedirs(os.path.dirname(os.path.join(folder, name)) or folder, exist_ok=True)
        with open(os.path.join(folder, name), "w") as f:
            f.write(content)
    return folder


def test_timestamp_span():
    folder = _folder({"t.log": LOG, "two.log": "@0 A(1);@5 B(1);\n", "empty.log": ""})
    try:
        assert timestamp_span(os.path.join(folder, "t.log")) == 8
        assert timestamp_span(os.path.join(folder, "two.log")) == 5
        assert timestamp_span(os.path.join(folder, "empty.log")) is None
    finally:
        shutil.rmtree(folder)


def test_bound_policy_to_trace_writes_the_bounded_policy():
    folder = _folder({"p.mfotl": "EVENTUALLY[2,*) A(x)\n", "scratch/t.log": LOG})
    try:
        params = {POLICY_KEY: "p.mfotl", TRACE_KEY: "scratch/t.log",
                  TRACE_TARGET_FORMAT: InputOutputTraceFormats.MONPOLY}
        step = bound_policy_to_trace(params, folder)
        assert step.params == {"horizon": 8, "bounded_operators": 1}
        assert params[POLICY_KEY] == "scratch/bounded_p.mfotl"
        with open(os.path.join(folder, params[POLICY_KEY])) as f:
            assert f.read() == "EVENTUALLY[2,8] A(x)\n"
        # nothing to bound, or not a MonPoly log: the policy stays
        params = {POLICY_KEY: "p.mfotl", TRACE_KEY: "scratch/t.log", TRACE_TARGET_FORMAT: InputOutputTraceFormats.CSV}
        assert bound_policy_to_trace(params, folder) is None and params[POLICY_KEY] == "p.mfotl"
    finally:
        shutil.rmtree(folder)


def test_verimon_preprocessing_records_the_step():
    folder = _folder({"p.mfotl": "A(x) UNTIL B(x)\n", "scratch/t.log": LOG})

    def converted(self, path_to_folder, *args, **kwargs):
        self.params.update({POLICY_KEY: "p.mfotl", TRACE_KEY: "scratch/t.log",
                            TRACE_TARGET_FORMAT: InputOutputTraceFormats.MONPOLY})
        return PreprocessingResult(elapsed_s=0.0, records=[
            ConversionRecord(kind="trace", source_file="t.csv", source_format="csv", steps=[],
                             as_seen_by_tool="scratch/t.log"),
            ConversionRecord(kind="policy", source_file="p.mfotl", source_format="mfotl", steps=[],
                             as_seen_by_tool="p.mfotl")])

    original = BaseMonitorTemplate.preprocessing
    BaseMonitorTemplate.preprocessing = converted
    try:
        verimon = VeriMon.__new__(VeriMon)
        verimon.name, verimon.params = "VeriMon", {}
        result = verimon.preprocessing(folder, InputOutputTraceFormats.CSV, InputOutputPolicyFormats.MFOTL,
                                       "t.csv", "s.sig", "p.mfotl", None)
        policy = [r for r in result.records if r.kind == "policy"][0]
        assert policy.as_seen_by_tool == "scratch/bounded_p.mfotl"
        assert [s.converter for s in policy.steps] == ["BoundUnboundedFuture"]
        verimon.params = {"bound_unbounded_future": False}
        result = verimon.preprocessing(folder, InputOutputTraceFormats.CSV, InputOutputPolicyFormats.MFOTL,
                                       "t.csv", "s.sig", "p.mfotl", None)
        assert verimon.params[POLICY_KEY] == "p.mfotl"
    finally:
        BaseMonitorTemplate.preprocessing = original
        shutil.rmtree(folder)


def _verimon(folder, formula):
    with open(os.path.join(folder, "f.mfotl"), "w") as f:
        f.write(formula)
    run = subprocess.run(["docker", "run", "--rm", "-v", f"{folder}:/work", "-w", "/work", VERIMON_IMAGE,
                          "monpoly", "-sig", "s.sig", "-formula", "f.mfotl", "-log", "t.log", "-verified"],
                         capture_output=True, text=True)
    return run.stdout + run.stderr


def test_verimon_end_to_end():
    if subprocess.run(["docker", "image", "inspect", VERIMON_IMAGE], capture_output=True).returncode != 0:
        print("skip: no VeriMon image")
        return
    folder = tempfile.mkdtemp(dir=PROJECT_ROOT, prefix=".test_bounded_future_")
    try:
        with open(os.path.join(folder, "s.sig"), "w") as f:
            f.write("A(x:int)\nB(x:int)\n")
        with open(os.path.join(folder, "t.log"), "w") as f:
            f.write(LOG)
        horizon = timestamp_span(os.path.join(folder, "t.log"))
        assert "unbounded future" in _verimon(folder, "EVENTUALLY[2,*) A(x)")
        # A later A at least 2 time units ahead; the last two time points have none.
        assert _verimon(folder, bound_unbounded_future("EVENTUALLY[2,*) A(x)", horizon)[0]).split("\n")[:4] == [
            "@0 (time point 0): (1) (3)", "@1 (time point 1): (1) (3)", "@2 (time point 2): (1) (3)",
            "@5 (time point 3): (1)"]
        assert _verimon(folder, bound_unbounded_future("A(x) UNTIL B(x)", horizon)[0]).split("\n")[:2] == [
            "@2 (time point 2): (1)", "@8 (time point 5): (2)"]
    finally:
        shutil.rmtree(folder)
    print("ok: VeriMon gives the unbounded verdicts on the bounded formula")


TESTS = [value for name, value in sorted(globals().items()) if name.startswith("test_")]

if __name__ == "__main__":
    for test in TESTS:
        test()
    print(f"{len(TESTS)} test functions passed")
    sys.exit(0)
