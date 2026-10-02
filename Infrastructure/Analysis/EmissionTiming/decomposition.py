"""Per-setting table of a claim-family run: the correctness gate, each lane's
lead over the sorted lane, its share of verdicts at the reference, and the
lead decomposition, all in lines fed.

Every lane feeds the same disordered stream one line per round, so a verdict's
position is the number of lines fed when a lane first emitted it (frames from
EmissionTiming.sorted_lane for the sorted lane). Per verdict the lead of the
watermark lane over the sorted lane splits into three parts:

    price of in-orderness    = sorted - watermark          (MonPoly - common)
    price of prefix closure  = watermark - point claims    (common - tp-interval)
    distance to the limit    = point claims - reference    (tp-interval - OOOMon)

Verdicts the sorted lane emits only at the end of the input have no position
there; they are counted, and left out of the lead and of the first part.

The gate compares verdict multisets (pairs of time-point and valuation,
counted, so duplicate emissions show) of all lanes, after each lane's value
columns are put in the reference's order (tools order free variables
differently; the reordering applied is reported). Run from the project root:

    python -m Infrastructure.Analysis.EmissionTiming.decomposition <run_dir> [--out FILE]
"""
import argparse
import csv
import os
import statistics
import sys
from collections import Counter
from typing import Dict, List, Optional, Tuple

from Infrastructure.Analysis.EmissionTiming.extract import column_order, extract, load_frames, reorder

SORTED, RECORDED, WATERMARK, POINTS, REFERENCE = (
    "MonPoly exact", "MonPoly", "TimelyMon common", "TimelyMon tp-interval", "OOOMon")
LANES = [RECORDED, SORTED, WATERMARK, POINTS, REFERENCE]
TAIL = float("inf")


def positions(frame: dict) -> Tuple[Dict[tuple, float], Counter, int]:
    """First emission per verdict in lines fed (TAIL after the last line),
    the verdict multiset, and the number of unmapped verdicts."""
    blocks = frame["blocks"]
    total = sum(1 for b in blocks if b.get("input_points") is not None)
    run = extract(frame)
    first: Dict[tuple, float] = {}
    counts: Counter = Counter()
    for e in run.emissions:
        key = (e.point, e.valuation)
        counts[key] += 1
        lines = e.round + 1 if e.round < total else TAIL
        first[key] = min(first.get(key, lines), lines)
    return first, counts, run.unmapped


def _summary(values: List[float]) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    if not values:
        return None, None, None
    return statistics.median(values), round(statistics.mean(values), 2), max(values)


def aligned(pos: Dict[str, Dict[tuple, float]], sets: Dict[str, Counter]) -> Dict[str, Tuple[int, ...]]:
    """Reorder every lane's value columns to the reference's (in place); the
    orders that are not the identity, per lane."""
    moved = {}
    for lane in list(sets):
        if lane == REFERENCE or REFERENCE not in sets:
            continue
        order = column_order(sets[REFERENCE], sets[lane])
        if order != tuple(range(len(order))):
            pos[lane] = {(p, reorder(v, order)): x for (p, v), x in pos[lane].items()}
            sets[lane] = Counter({(p, reorder(v, order)): n for (p, v), n in sets[lane].items()})
            moved[lane] = order
    return moved


def setting_row(setting: str, frames: Dict[str, dict]) -> dict:
    pos, sets, unmapped = {}, {}, {}
    for lane in LANES:
        if lane in frames:
            pos[lane], sets[lane], unmapped[lane] = positions(frames[lane])
    columns = aligned(pos, sets)
    missing = [lane for lane in LANES if lane not in frames]
    reference = sets.get(REFERENCE)
    gate = "ok"
    if missing:
        gate = "missing " + ", ".join(missing)
    elif any(s != reference for s in sets.values()) or any(unmapped.values()):
        gate = "FAILED " + "; ".join(
            f"{lane}: extra {sum((s - reference).values())} missing {sum((reference - s).values())}"
            for lane, s in sets.items() if s != reference)
    duplicates = {lane: sum(c - 1 for c in s.values()) for lane, s in sets.items()}
    if any(duplicates.values()):
        gate = "FAILED duplicates " + str({k: v for k, v in duplicates.items() if v})

    row = {"setting": setting, "gate": gate, "verdicts": len(pos.get(REFERENCE, {})),
           "columns": "; ".join(f"{lane} {order}" for lane, order in columns.items())}
    if gate != "ok":
        return row
    keys = list(pos[REFERENCE])
    sorted_pos = pos[SORTED]
    timed = [k for k in keys if sorted_pos[k] != TAIL]
    row["sorted_end_only"] = len(keys) - len(timed)
    row["sorted_exact_later_than_recorded"] = sum(sorted_pos[k] > pos[RECORDED][k] for k in keys)
    for lane, name in ((WATERMARK, "watermark"), (POINTS, "points"), (REFERENCE, "reference")):
        lead = [sorted_pos[k] - pos[lane][k] for k in timed]
        row[f"{name}_lead_median"], row[f"{name}_lead_mean"], row[f"{name}_lead_max"] = _summary(lead)
        row[f"{name}_later_than_sorted"] = sum(pos[lane][k] > sorted_pos[k] for k in keys)
        row[f"{name}_at_reference"] = round(sum(pos[lane][k] == pos[REFERENCE][k] for k in keys) / len(keys), 4)
    parts = {
        "in_orderness": [sorted_pos[k] - pos[WATERMARK][k] for k in timed],
        "prefix_closure": [pos[WATERMARK][k] - pos[POINTS][k] for k in keys],
        "to_limit": [pos[POINTS][k] - pos[REFERENCE][k] for k in keys],
    }
    for name, values in parts.items():
        row[f"{name}_median"], row[f"{name}_mean"], row[f"{name}_max"] = _summary(values)
        row[f"{name}_negative"] = sum(v < 0 for v in values)
    return row


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m Infrastructure.Analysis.EmissionTiming.decomposition",
        description="Correctness gate, leads and lead decomposition per setting, in lines fed.")
    parser.add_argument("run_dir", help="result folder of an online claim-family run (frames/ incl. MonPoly_exact)")
    parser.add_argument("--out", help="CSV (default: <run_dir>/emission_timing/decomposition.csv)")
    args = parser.parse_args(argv)

    settings: Dict[str, Dict[str, dict]] = {}
    for frame in load_frames(args.run_dir):
        settings.setdefault(frame["setting"], {})[frame["tool"]] = frame
    rows = [setting_row(s, f) for s, f in sorted(settings.items())]

    print(f"{'setting':14s} {'gate':6s} {'verdicts':>8s} {'end only':>8s}   lead over MonPoly, median/max lines "
          f"(common | tp-interval | OOOMon)   at OOOMon (common | tp-interval)   "
          f"decomposition median/mean (in-orderness | prefix closure | to limit)")
    for r in rows:
        if r["gate"] != "ok":
            print(f"{r['setting']:14s} {r['gate']}")
            continue
        print(f"{r['setting']:14s} {r['gate']:6s} {r['verdicts']:8d} {r['sorted_end_only']:8d}   "
              f"{r['watermark_lead_median']}/{r['watermark_lead_max']} | {r['points_lead_median']}/"
              f"{r['points_lead_max']} | {r['reference_lead_median']}/{r['reference_lead_max']}   "
              f"{r['watermark_at_reference']:.3f} | {r['points_at_reference']:.3f}   "
              f"{r['in_orderness_median']}/{r['in_orderness_mean']} | {r['prefix_closure_median']}/"
              f"{r['prefix_closure_mean']} | {r['to_limit_median']}/{r['to_limit_mean']}")
        flags = {k: v for k, v in r.items() if (k.endswith("_negative") or k.endswith("_later_than_sorted")
                                                or k in ("sorted_exact_later_than_recorded", "columns")) and v}
        if flags:
            print(f"{'':14s} NOTE {flags}")

    out = args.out or os.path.join(args.run_dir, "emission_timing", "decomposition.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    fields = sorted({k for r in rows for k in r}, key=lambda k: (k not in ("setting", "gate", "verdicts"), k))
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"written to {out}")
    return 1 if any(r["gate"] != "ok" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
