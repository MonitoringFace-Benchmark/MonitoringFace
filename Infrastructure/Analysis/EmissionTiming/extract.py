"""Per-verdict emissions from online frames.

A frame is one driver round: the time-points its input carried
(input_points, [tp, ts] pairs; tp is None for MonPoly log lines, which are
time-points of their own) and the tool's output for that round. A verdict's
emission time is the log time the input had reached in the round that
emitted it: the largest timestamp fed so far. Rounds after the last input
are the tool's end-of-input tail and have no emission time of their own.

Tools number time-points differently (MonPoly from 0 in arrival order, the
CSV traces by their tp field), so every time-point is identified by its
timestamp and its position among the time-points sharing that timestamp,
which each run derives from its own recorded input.
"""
import glob
import json
import os
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

MONPOLY_RE = re.compile(r"^@\d+\s*\(time point (\d+)\):\s*(.*)$")
TIMELYMON_RE = re.compile(r"^\((.*)\):\s*Time point\(s\)\s*(\d+)(?:-(\d+))?\s*$")
TUPLE_RE = re.compile(r"\(([^()]*)\)")

PointId = Tuple[int, int]


@dataclass(frozen=True)
class Emission:
    point: PointId
    valuation: Tuple[str, ...]
    round: int
    log_time: Optional[int]


@dataclass
class ToolRun:
    tool: str
    setting: str
    source: str
    emissions: List[Emission]
    point_timestamps: List[int]
    unmapped: int


def load_frames(run_dir: str) -> List[dict]:
    frames = []
    for path in sorted(glob.glob(os.path.join(run_dir, "frames", "*.json"))):
        with open(path) as f:
            frame = json.load(f)
        if "blocks" not in frame:
            continue
        frame["source"] = path
        frames.append(frame)
    return frames


def _values(text: str) -> Tuple[str, ...]:
    return tuple(v.strip().strip("'\"") for v in text.split(",") if v.strip())


def verdicts_of_line(line: str) -> List[Tuple[int, Tuple[str, ...]]]:
    """(tool's own time-point number, valuation) for every verdict on a line."""
    line = line.strip()
    match = TIMELYMON_RE.match(line)
    if match:
        first = int(match[2])
        last = int(match[3]) if match[3] else first
        return [(tp, _values(match[1])) for tp in range(first, last + 1)]
    match = MONPOLY_RE.match(line)
    if match:
        tp, payload = int(match[1]), match[2].strip()
        if payload == "true":
            return [(tp, ())]
        return [(tp, _values(t)) for t in TUPLE_RE.findall(payload) if t.strip()]
    return []


def point_ids(blocks: List[dict]) -> Tuple[Dict[int, PointId], List[int]]:
    """Map the tool's time-point numbers to shared ids, and list the
    timestamps of all time-points in time-point order."""
    numbered: Dict[int, int] = {}
    arrivals: List[int] = []
    for block in blocks:
        for tp, ts in block.get("input_points") or []:
            if tp is None:
                arrivals.append(ts)
            else:
                numbered.setdefault(tp, ts)
    if numbered and arrivals:
        raise ValueError("input mixes numbered and log time-points")
    order = sorted(numbered.items()) if numbered else list(enumerate(arrivals))
    ids: Dict[int, PointId] = {}
    seen: Dict[int, int] = {}
    for number, ts in order:
        ids[number] = (ts, seen.get(ts, 0))
        seen[ts] = seen.get(ts, 0) + 1
    return ids, [ts for _, ts in order]


def log_times(blocks: List[dict]) -> List[Optional[int]]:
    """Per round, the largest timestamp fed so far; None for the rounds of
    the end-of-input tail."""
    last_input = max((i for i, b in enumerate(blocks) if b.get("input_points") is not None), default=-1)
    times, reached = [], None
    for i, block in enumerate(blocks):
        for _, ts in block.get("input_points") or []:
            reached = ts if reached is None else max(reached, ts)
        times.append(None if i > last_input else reached)
    return times


def extract(frame: dict) -> ToolRun:
    blocks = frame["blocks"]
    if not any(b.get("input_points") is not None for b in blocks):
        raise ValueError(f"{frame.get('source')}: frames carry no input_points; "
                         f"recorded before input time-points were kept")
    ids, point_timestamps = point_ids(blocks)
    times = log_times(blocks)
    emissions, unmapped = [], 0
    for i, block in enumerate(blocks):
        for line in block.get("output") or []:
            for tp, valuation in verdicts_of_line(line):
                if tp not in ids:
                    unmapped += 1
                    continue
                emissions.append(Emission(ids[tp], valuation, i, times[i]))
    return ToolRun(frame["tool"], frame["setting"], frame["source"], emissions, point_timestamps, unmapped)


def extract_runs(run_dirs: List[str]) -> List[ToolRun]:
    return [extract(frame) for run_dir in run_dirs for frame in load_frames(run_dir)]
