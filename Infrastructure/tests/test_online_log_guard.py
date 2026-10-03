"""Tests for the tool's stderr inside the driver log stream: the container
log merges both, so a monitor's source-guard summary must become a count
(facts dropped because they reached an already completed time-point) and its
warnings must stay out of the rounds' verdict output.

Plain asserts, no pytest dependency: run with

    python -m Infrastructure.tests.test_online_log_guard
"""

import sys

from Infrastructure.Builders.BuilderUtilities import parse_online_logs

ROUND = [
    "[Driver Protocol] 2\n",
    "[Input  ] A, tp=0, ts=0, x=1\n",
    "[Output ]\n",
    "(1): Time point(s) 0\n",
    "warning: fact at tp 0 arrived below watermark 1 — dropped\n",
    "Event count 1\n",
    "[Processed] 1\n",
    "[Wall Offset] 10 ns\n",
    "[Elapsed] 100 ns\n",
    "\n",
]
FOOTER = ["[Accumulative Elapsed] 0.5 s\n", "[Total Count] 1\n"]


def test_timelymon_guard_summary_and_warnings():
    summary = ("source guard: 0 regressing watermark(s) ignored, 13 late fact(s) dropped, "
               "0 signature-incompatible record(s) dropped, 0 non-monotone timestamp(s)\n")
    parsed = parse_online_logs([line.encode() for line in ROUND + [summary] + FOOTER])
    assert parsed["blocks"][0]["output"] == ["(1): Time point(s) 0", "Event count 1"]
    assert parsed["late_dropped"] == 13
    assert parsed["tool_warnings"] == 1
    assert parsed["total_count"] == 1


def test_ooomon_guard_summary():
    parsed = parse_online_logs(ROUND + ["source guard: 4 late fact(s) dropped\n"] + FOOTER)
    assert parsed["late_dropped"] == 4


def test_no_guard_report_means_none():
    parsed = parse_online_logs(ROUND + FOOTER)
    assert parsed["late_dropped"] is None
    assert parsed["blocks"][0]["processed"] == 1


TESTS = [value for name, value in sorted(globals().items()) if name.startswith("test_")]

if __name__ == "__main__":
    for test in TESTS:
        test()
    print(f"{len(TESTS)} test functions passed")
    sys.exit(0)
