"""Tests for the watermarks the trace generators add (`watermarks: true`).

The Signature and Pattern generators used to drop the first event of every
watermarked trace: their loop recorded the first line's time point but never
kept the line. Both now share `infuse_watermarks`, which follows TimelyMon's
own trace tool: `>WATERMARK tp<` after the last event of time point tp, no
watermark after the last time point.

Plain asserts, no pytest dependency: run with

    python -m Infrastructure.tests.test_watermark_infusion
"""

import sys

from Archive.Implementations.Builders.ProcessorBuilder.DataGenerators.PatternDataGenerator.PatternDataGenerator import \
    PatternDataGenerator
from Archive.Implementations.Builders.ProcessorBuilder.DataGenerators.SignatureGenerator.SignatureGenerator import \
    SignatureGenerator
from Infrastructure.Builders.ProcessorBuilder.DataGenerators.WatermarkInfusion import infuse_watermarks

TRACE = ("A, tp=0, ts=0, x0=1, x1=1\n"
         "B, tp=0, ts=0, x0=2, x1=2\n"
         "A, tp=1, ts=1, x0=3, x1=3\n"
         "B, tp=2, ts=2, x0=4, x1=4\n")

WATERMARKED = ("A, tp=0, ts=0, x0=1, x1=1\n"
               "B, tp=0, ts=0, x0=2, x1=2\n"
               ">WATERMARK 0<\n"
               "A, tp=1, ts=1, x0=3, x1=3\n"
               ">WATERMARK 1<\n"
               "B, tp=2, ts=2, x0=4, x1=4")


def test_every_event_is_kept():
    assert infuse_watermarks(TRACE) == WATERMARKED


def test_a_first_time_point_with_one_event_keeps_it():
    # The old loop turned such a time point into one without events: the
    # trace opened with ">WATERMARK 0<".
    out = infuse_watermarks("A, tp=0, ts=0, x0=1, x1=1\nA, tp=1, ts=1, x0=3, x1=3\n")
    assert out == "A, tp=0, ts=0, x0=1, x1=1\n>WATERMARK 0<\nA, tp=1, ts=1, x0=3, x1=3"


def test_an_empty_trace_stays_empty():
    assert infuse_watermarks("") == ""
    assert infuse_watermarks("\n") == ""


class _StubImage:
    def __init__(self, out):
        self.out = out

    def run(self, contract, time_on=None, time_out=None):
        return self.out, 0


def _generated(cls, contract):
    generator = cls.__new__(cls)
    generator.image = _StubImage(TRACE)
    _, out = generator.run_generator(contract)
    return out


def test_both_generators_infuse_on_request_only():
    for cls in (SignatureGenerator, PatternDataGenerator):
        assert _generated(cls, {"trace_length": 3, "watermarks": True}) == WATERMARKED, cls.__name__
        assert _generated(cls, {"trace_length": 3}) == TRACE, cls.__name__


TESTS = [value for name, value in sorted(globals().items()) if name.startswith("test_")]

if __name__ == "__main__":
    for test in TESTS:
        test()
    print(f"{len(TESTS)} test functions passed")
    sys.exit(0)
