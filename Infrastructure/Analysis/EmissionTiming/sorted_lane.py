"""Exact emission positions for an in-order monitor behind the Sorter.

Under chain accounting a round closes on the stage counters alone, so output
the monitor prints after its round closed lands in a later round: a recorded
position of a sorted-lane verdict can only be late. The Sorter is
deterministic, so the exact position follows offline. The lane's fed stream
is replayed through the Sorter, recording the fed line whose arrival releases
each block; the pinned monitor runs once over the released blocks with
-verbose, where everything after the marker of step k and before the next
marker is step k's output; every verdict of step k is credited to the fed line
that released block k. The end-of-input flush and the monitor's final step
belong to a tail round after the last fed line.

MonPoly ends a time-point only at the next `@` or at a `;`. The Sorter's
blocks carry no `;`, so on the lane MonPoly prints step k once block k+1 has
arrived. Crediting step k to the release of block k is the position MonPoly
reaches with `;`-terminated blocks (checked on the pinned binary), the earliest
it can report.

The result is written as a frame in the platform's format (one block per fed
line, carrying the time-points of the fed line as the driver records them,
then the tail), so it differs from the lane's own frame only in where the
output sits, and extract and compare read it like any other lane.
Run from the project root:

    python -m Infrastructure.Analysis.EmissionTiming.sorted_lane <run_dir> \\
        [--tool MonPoly] [--image online_experiment_monpoly_mf_image]
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Dict, List, Optional, Tuple

from Infrastructure.Builders.BuilderUtilities import input_points
from Infrastructure.Builders.ProcessorBuilder.StreamProcessors.StreamProcessorTemplate import (
    load_stream_processor)

MARKER = re.compile(r"^At time point (\d+):")
BLOCK_TS = re.compile(r"^@(\d+)")
RUN_STAMP = re.compile(r"_\d{8}_\d{6}$")


def sorter_releases(fed_lines: List[str], params: Optional[Dict] = None) -> Tuple[List[str], List[int]]:
    """The released blocks in order and, per block, the 1-based fed position
    whose arrival released it; len(fed_lines) + 1 for the end-of-input flush."""
    sorter = load_stream_processor("Sorter")("Sorter")
    sorter.setup(dict(params or {}))
    blocks: List[str] = []
    released_at: List[int] = []
    for position, line in enumerate(fed_lines, start=1):
        for block in sorter.feed(line):
            blocks.append(block)
            released_at.append(position)
    for block in sorter.flush():
        blocks.append(block)
        released_at.append(len(fed_lines) + 1)
    return blocks, released_at


def step_outputs(stdout_lines: List[str]) -> Dict[int, List[str]]:
    """Monitor -verbose output per step: the verdict lines (`@ts (time point
    j): ...`) after the marker of step k and before the next marker. The
    formula header is printed unflushed and surfaces wherever stdout is next
    flushed (after the last marker in a batch run), so only verdict lines
    count."""
    steps: Dict[int, List[str]] = {}
    current = None
    for line in stdout_lines:
        line = line.strip()
        match = MARKER.match(line)
        if match:
            current = int(match.group(1))
            steps.setdefault(current, [])
        elif current is not None and line.startswith("@"):
            steps[current].append(line)
    return steps


def check_numbering(fed_points: List[List[List[int]]], blocks: List[str]) -> None:
    """The monitor numbers time-points by block, the fed stream by its tp
    field; both name the same time-point only if block k carries the
    timestamp of tp k."""
    ts_of: Dict[int, int] = {}
    for points in fed_points:
        for tp, ts in points:
            if tp is not None:
                ts_of.setdefault(tp, ts)
    for k, block in enumerate(blocks):
        ts = int(BLOCK_TS.match(block).group(1))
        if ts_of.get(k) != ts:
            raise SystemExit(f"block {k} carries @{ts}, but tp {k} of the fed stream has ts {ts_of.get(k)}")


def exact_frame(fed_points: List[List[List[int]]], blocks: List[str], released_at: List[int],
                steps: Dict[int, List[str]], tool: str, setting: str) -> dict:
    """One frame block per fed line plus the tail. A fed line's block carries
    the time-points of the line itself and the output of the steps whose
    blocks the line released."""
    fed_count = len(fed_points)
    rounds = [{"output": [], "input_points": points, "processed": position}
              for position, points in enumerate(fed_points, start=1)]
    tail = {"output": [], "input_points": None, "processed": fed_count}
    for k, position in enumerate(released_at):
        target = tail if position > fed_count else rounds[position - 1]
        target["output"].extend(steps.get(k, []))
    for k, lines in steps.items():
        if k >= len(blocks):                  # the monitor's own end-of-input step
            tail["output"].extend(lines)
    out_blocks = rounds + ([tail] if tail["output"] else [])
    for block in out_blocks:
        block["output"] = block["output"] or None
    return {"tool": tool, "setting": setting, "exit_code": 0, "blocks": out_blocks,
            "source": "sorted_lane replay"}


def _sha256(path: str) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def _lane_inputs(run_dir: str, block: str, tool: str, experiments_dir: str) -> Tuple[str, Dict[str, str], List[str]]:
    """The fed stream (the stored copy of the trace the static stages
    produced), the policy and signature (checked against their recorded
    sha256) and the tool's invocation, from the lane's provenance."""
    prov_path = os.path.join(run_dir, "provenance", block, tool, "provenance.json")
    with open(prov_path) as f:
        prov = json.load(f)
    entries = {e["kind"]: e for e in prov["entries"]}
    trace = entries["trace"]
    if not trace.get("stored"):
        raise SystemExit(f"{prov_path}: the trace has no stored copy; the lane has no static stage")
    fed = os.path.join(os.path.dirname(prov_path), trace["stored"]["file"])
    files = {}
    # a single-experiment run folder is <experiment>_<date>_<time>; an
    # experiment folder inside a suite run carries the bare name
    name = os.path.basename(run_dir.rstrip("/"))
    experiment = RUN_STAMP.sub("", name)
    for kind in ("policy", "signature"):
        source = entries[kind]["source"]
        path = os.path.join(experiments_dir, experiment, source["file"])
        if not os.path.exists(path) or _sha256(path) != source["sha256"]:
            raise SystemExit(f"{path}: missing or changed since the run (sha256 differs)")
        files[kind] = path
    return fed, files, prov["tool_invocation"]


def run_monitor(image: str, blocks: List[str], files: Dict[str, str], invocation: List[str]) -> List[str]:
    """Run the pinned binary (/usr/local/bin/tool in the online image) once
    over the released blocks, with the lane's own invocation."""
    work = tempfile.mkdtemp(prefix="sorted_lane_")
    try:
        os.makedirs(os.path.join(work, "additional"))
        shutil.copy(files["policy"], os.path.join(work, "additional", "policy.policy"))
        shutil.copy(files["signature"], os.path.join(work, "additional", "signature.sig"))
        proc = subprocess.run(
            ["docker", "run", "--rm", "-i", "-v", f"{work}:/work", "-w", "/work",
             "--entrypoint", "/usr/local/bin/tool", image] + invocation,
            input="\n".join(blocks) + "\n", capture_output=True, text=True, timeout=3600)
        if proc.returncode != 0:
            raise SystemExit(f"{image} exited {proc.returncode}: {proc.stderr[-500:]}")
        return proc.stdout.splitlines()
    finally:
        shutil.rmtree(work, ignore_errors=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m Infrastructure.Analysis.EmissionTiming.sorted_lane",
        description="Exact emission positions of a sorted lane, written as frames/<setting>__<tool>_exact.json.")
    parser.add_argument("run_dir", help="result folder of an online run with frames/ and provenance/")
    parser.add_argument("--tool", default="MonPoly", help="the sorted lane's tool name (default: MonPoly)")
    parser.add_argument("--image", default="online_experiment_monpoly_mf_image",
                        help="image holding the pinned binary at /usr/local/bin/tool")
    parser.add_argument("--experiments", default="Infrastructure/experiments",
                        help="folder holding the experiments' generated inputs")
    args = parser.parse_args(argv)

    frames = sorted(glob.glob(os.path.join(args.run_dir, "frames", f"*__{args.tool}.json")))
    if not frames:
        print(f"no frames for {args.tool} in {args.run_dir}", file=sys.stderr)
        return 1
    for frame_path in frames:
        setting = os.path.basename(frame_path).split("__")[0]
        block = setting.rsplit("_", 1)[0]
        fed_path, files, invocation = _lane_inputs(args.run_dir, block, args.tool, args.experiments)
        with open(fed_path) as f:
            fed = [line.rstrip("\n") for line in f if line.strip()]
        fed_points = [input_points(line) for line in fed]
        with open(frame_path) as f:
            recorded = [b["input_points"] for b in json.load(f)["blocks"] if b.get("input_points") is not None]
        if recorded != fed_points:
            raise SystemExit(f"{frame_path}: the lane's recorded input differs from the stored fed stream")
        blocks, released_at = sorter_releases(fed)
        check_numbering(fed_points, blocks)
        steps = step_outputs(run_monitor(args.image, blocks, files, invocation))
        frame = exact_frame(fed_points, blocks, released_at, steps, f"{args.tool} exact", setting)
        out = os.path.join(args.run_dir, "frames", f"{setting}__{args.tool}_exact.json")
        with open(out, "w") as f:
            json.dump(frame, f)
        verdict_lines = sum(len(v) for v in steps.values())
        print(f"{setting}: {len(fed)} fed lines, {len(blocks)} blocks released, "
              f"{verdict_lines} output lines -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
