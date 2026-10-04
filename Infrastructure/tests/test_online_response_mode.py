"""Tests for the online response modes. Plain asserts, no pytest
dependency: run with

    Infrastructure/environment/venv/bin/python -m Infrastructure.tests.test_online_response_mode

Covers the tool contract's response_mode parsing (explicit values, the
event-count default, loud rejection of unknown values), the arguments handed
to the driver, and the stream-contract rule that buffering dynamic stages
need one tool response per delivered line.
"""

import sys

from Infrastructure.DataTypes.Types.custome_type import ResponseMode
from Infrastructure.Frontend.Parser.YamlParser import (
    YamlParser, YamlParserException, validate_stream_contract,
)
from Infrastructure.constants import STREAM_STAGE_DYNAMIC


def contract(**tool):
    raw = {"format": "log", "output_collection_mode": "after-delimiter", **tool}
    params = YamlParser.parse_tool_params(None, {"params": {"OnlineExperimentContractTool": raw}})
    return params["OnlineExperimentContractTool"]


def test_process_step_reaches_the_driver():
    c = contract(response_mode="process-step")
    assert c.response_mode == ResponseMode.PROCESS_STEP
    args = c.get_tool_arguments()
    i = args.index("--response-mode")
    assert args[i + 1] == "process-step", args
    print("ok test_process_step_reaches_the_driver")


def test_known_modes_and_default():
    assert contract(response_mode="current-timepoint").response_mode == ResponseMode.CURRENT_TIMEPOINT
    assert contract(response_mode="Event-Count").response_mode == ResponseMode.EVENT_COUNT
    assert contract().response_mode == ResponseMode.EVENT_COUNT
    print("ok test_known_modes_and_default")


def test_unknown_mode_is_rejected():
    try:
        contract(response_mode="proces-step")
    except YamlParserException as e:
        assert "proces-step" in str(e)
    else:
        raise AssertionError("a misspelled response_mode silently became a known mode")
    print("ok test_unknown_mode_is_rejected")


def test_buffering_stage_needs_one_response_per_line():
    spec = [{"identifier": "Sorter", "stage": STREAM_STAGE_DYNAMIC}]
    validate_stream_contract(spec, contract(response_mode="process-step"))
    validate_stream_contract(spec, contract(response_mode="event-count"))
    validate_stream_contract(spec, contract(response_mode="current-timepoint", response_accounting="chain"))
    try:
        validate_stream_contract(spec, contract(response_mode="current-timepoint"))
    except YamlParserException:
        pass
    else:
        raise AssertionError("current-timepoint lockstep behind a buffering stage was accepted")
    print("ok test_buffering_stage_needs_one_response_per_line")


def main():
    test_process_step_reaches_the_driver()
    test_known_modes_and_default()
    test_unknown_mode_is_rejected()
    test_buffering_stage_needs_one_response_per_line()
    print("\nALL RESPONSE MODE TESTS PASSED")


if __name__ == "__main__":
    sys.exit(main())
