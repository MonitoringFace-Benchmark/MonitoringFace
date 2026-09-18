"""Implicit syntax agreement of the OOO claim family (Disorderer, Sorter,
PrefixRebuilder): canonical events carry `tp=<int>`, the bridge format for
in-order tools is `@tp @ts atom(args)` (per-line rendering of the same
event, so it commutes with any permutation), a point-completeness claim is
`>ELAPSED <tp> @ <ts><` (TimelyMon tp-interval-timestamp's native token:
time-point tp with timestamp ts is complete, independent of any prefix; the
claim carries the timestamp, so even an empty tp's ts travels in the
stream), a downward-closed claim is the established `>WATERMARK <tp><`.
Claims and watermarks are synthesized lines and carry origin index 0 in
released_origins reports."""

import re

from Infrastructure.Builders.ProcessorBuilder.StreamProcessors.StreamProcessorTemplate import (
    StreamProcessorException)

TP_RE = re.compile(r"tp=(\d+)")
TS_RE = re.compile(r"ts=(\d+)")
CLAIM_RE = re.compile(r">ELAPSED\s+(\d+)\s*@\s*(\d+)<")
WATERMARK_RE = re.compile(r">WATERMARK\s+(\d+)<")
BRIDGE_RE = re.compile(r"^@(\d+)\s+@(\d+)\s*(.*)$")

SYNTHESIZED_ORIGIN = 0


def bridge_parts(line: str):
    match = BRIDGE_RE.match(line)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2)), match.group(3).strip()


def extract_ts(line: str) -> int:
    match = TS_RE.search(line)
    if match is not None:
        return int(match.group(1))
    bridge = bridge_parts(line)
    if bridge is not None:
        return bridge[1]
    raise StreamProcessorException(f"no ts in event line {line!r}")


def extract_tp(line: str) -> int:
    match = TP_RE.search(line)
    if match is not None:
        return int(match.group(1))
    bridge = bridge_parts(line)
    if bridge is not None:
        return bridge[0]
    raise StreamProcessorException(f"no tp in event line {line!r}")


def csv_to_bridge(line: str) -> str:
    fields = [field.strip() for field in line.split(",")]
    name = fields[0]
    tp = None
    ts = None
    args = []
    for field in fields[1:]:
        if "=" not in field:
            raise StreamProcessorException(f"malformed canonical event line {line!r}")
        key, value = field.split("=", 1)
        key = key.strip()
        if key == "tp":
            tp = int(value)
        elif key == "ts":
            ts = int(value)
        else:
            args.append(value.strip())
    if tp is None or ts is None:
        raise StreamProcessorException(f"canonical event line without tp/ts: {line!r}")
    return f"@{tp} @{ts} {name}({','.join(args)})"


def claim_parts(line: str):
    match = CLAIM_RE.search(line)
    return (int(match.group(1)), int(match.group(2))) if match else None


def claim_tp(line: str):
    parts = claim_parts(line)
    return parts[0] if parts else None


def watermark_tp(line: str):
    match = WATERMARK_RE.search(line)
    return int(match.group(1)) if match else None


def render_claim(tp: int, ts: int) -> str:
    return f">ELAPSED {tp} @ {ts}<"


def render_watermark(tp: int) -> str:
    return f">WATERMARK {tp}<"
