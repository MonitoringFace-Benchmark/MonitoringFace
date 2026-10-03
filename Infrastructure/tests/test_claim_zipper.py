"""Tests for the ClaimZipper stream processor: claim_gen's positional claims
are zipped into the trace (a claim at position n goes after the first n trace
lines), and with pacing every line carries its due time for the driver's
`--format prefixed`. Stage params name the claims through `{trace}`, which
resolves to each setting's own trace.

Plain asserts, no pytest dependency: run with

    python -m Infrastructure.tests.test_claim_zipper
"""

import os
import sys
import tempfile

from Archive.Implementations.Builders.ProcessorBuilder.StreamProcessors.ClaimZipper.ClaimZipper import ClaimZipper
from Infrastructure.Builders.ProcessorBuilder.StreamProcessors.StreamProcessorTemplate import (
    StreamProcessorException)
from Infrastructure.Builders.ProcessorBuilder.StreamProcessors.StreamRunner import (
    apply_stream_pipeline, resolve_stage_params, run_stage)

TRACE = ["A, tp=1, ts=11, x=1", "A, tp=0, ts=10, x=2", "B, tp=2, ts=12, x=3"]
RX = ["1000", "1200", "2500"]
CLAIMS = ("# claim_gen claims v1\n"
          "# pos\tutter_ms\tclaim\n"
          "0\t900\t>WATERMARK 0<\n"
          "2\t2100\t>ELAPSED 1 @ 11<\n"
          "2\t2200\t>ELAPSED 0 @ 10<\n"
          "3\t2500\t>ELAPSED 2 @ 12<\n")


def _files(claims=CLAIMS, rx=RX):
    folder = tempfile.mkdtemp()
    with open(os.path.join(folder, "c.claims"), "w") as f:
        f.write(claims)
    with open(os.path.join(folder, "t.rx"), "w") as f:
        f.write("".join(r + "\n" for r in rx))
    return os.path.join(folder, "c.claims"), os.path.join(folder, "t.rx")


def _zip(pacing, claims=CLAIMS, rx=RX, trace=TRACE):
    claims_path, rx_path = _files(claims, rx)
    stage = ClaimZipper("ClaimZipper")
    stage.setup({"claims": claims_path, "rx": rx_path, "pacing": pacing})
    out, counters = run_stage(stage, trace)
    return out, counters, stage.stats()


def test_claims_go_after_their_position():
    out, counters, stats = _zip(pacing=False)
    assert out == [">WATERMARK 0<", TRACE[0], TRACE[1], ">ELAPSED 1 @ 11<",
                   ">ELAPSED 0 @ 10<", TRACE[2], ">ELAPSED 2 @ 12<"]
    assert counters == {"consumed": 3, "released": 7, "dropped": 0}
    assert stats == {"lines": 3, "claims": 4, "pacing": False}


def test_pacing_prefixes_every_line_with_its_due_time():
    out, _, _ = _zip(pacing=True)
    # a claim is never due before the line it follows: the watermark uttered
    # at 900 ms waits for nothing, the first fact is due at 1000 ms
    assert out == ["900\t>WATERMARK 0<", "1000\t" + TRACE[0], "1200\t" + TRACE[1],
                   "2100\t>ELAPSED 1 @ 11<", "2200\t>ELAPSED 0 @ 10<", "2500\t" + TRACE[2],
                   "2500\t>ELAPSED 2 @ 12<"]


def _raises(fragment, **kwargs):
    try:
        _zip(**kwargs)
    except StreamProcessorException as e:
        assert fragment in str(e), str(e)
        return
    raise AssertionError(f"expected a StreamProcessorException mentioning {fragment!r}")


def test_mismatched_inputs_are_rejected():
    _raises("beyond the trace", pacing=False, claims=CLAIMS + "9\t3000\t>ELAPSED 3 @ 13<\n")
    _raises("ends before trace line 3", pacing=True, rx=RX[:2])
    _raises("more lines than the trace", pacing=True, rx=RX + ["2600"])
    _raises("ingestion order", pacing=True, rx=["1000", "900", "2500"])
    _raises("neither", pacing=False, claims="0\t900\twatermark-ish\n")
    _raises("positions decrease", pacing=False, claims="2\t900\t>WATERMARK 0<\n1\t900\t>WATERMARK 1<\n")


def test_setup_requires_its_inputs():
    for params, fragment in (({}, "'claims'"), ({"claims": "x"}, "'rx'")):
        try:
            ClaimZipper("ClaimZipper").setup(params)
        except StreamProcessorException as e:
            assert fragment in str(e), str(e)
        else:
            raise AssertionError(f"setup({params}) should fail")


def test_trace_placeholder_resolves_to_the_setting_trace():
    params = {"claims": "{trace}.a10.elapsed.claims", "rx": "{trace}.rx", "pacing": True}
    assert resolve_stage_params(params, "/exp/data/Trace/rc_live.csv") == {
        "claims": "/exp/data/Trace/rc_live.a10.elapsed.claims",
        "rx": "/exp/data/Trace/rc_live.rx", "pacing": True}
    assert params["claims"] == "{trace}.a10.elapsed.claims"


def test_pipeline_zips_the_claims_that_belong_to_its_trace():
    folder = tempfile.mkdtemp()
    trace = os.path.join(folder, "t.csv")
    with open(trace, "w") as f:
        f.write("".join(line + "\n" for line in TRACE))
    with open(os.path.join(folder, "t.rx"), "w") as f:
        f.write("".join(r + "\n" for r in RX))
    with open(os.path.join(folder, "t.a1.elapsed.claims"), "w") as f:
        f.write(CLAIMS)
    params = {"claims": "{trace}.a1.elapsed.claims", "rx": "{trace}.rx", "pacing": False}
    output = os.path.join(folder, "scratch", "streamed_t.csv")
    steps = apply_stream_pipeline([{"identifier": "ClaimZipper", "params": params}],
                                  trace, output, "csv")
    with open(output) as f:
        assert f.read().splitlines() == [">WATERMARK 0<", TRACE[0], TRACE[1], ">ELAPSED 1 @ 11<",
                                         ">ELAPSED 0 @ 10<", TRACE[2], ">ELAPSED 2 @ 12<"]
    # provenance keeps the configured, setting-independent params
    assert steps[0].params == params


TESTS = [value for name, value in sorted(globals().items()) if name.startswith("test_")]

if __name__ == "__main__":
    for test in TESTS:
        test()
    print(f"{len(TESTS)} test functions passed")
    sys.exit(0)
