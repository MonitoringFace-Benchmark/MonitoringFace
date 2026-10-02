"""Cumulative verdicts against lines fed, one panel per setting.

Every lane of a claim-family run reads the same disordered stream one line per
round, events and claims alike, so the round index is a coordinate common to
all lanes: the lines fed when a verdict was emitted. A lane's curve counts its
verdicts at the line whose round first emitted them; verdicts of the
end-of-input tail sit at the end of the input. The reference lane is drawn
dashed on top, so lanes that reach it coincide with it. Run from the project
root:

    python -m Infrastructure.Analysis.EmissionTiming.lines_fed <run_dir> [--recorded] [--out FILE]
"""
import argparse
import os
import sys
import textwrap
from typing import Dict, List, Optional, Tuple

import numpy as np
import matplotlib
matplotlib.use("Agg", force=False)
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter

from Infrastructure.Analysis.EmissionTiming.extract import extract, load_frames
from Infrastructure.Analysis.EmissionTiming.sorted_lane import _lane_inputs

# drawn in this order: the reference last, dashed, on top of the lanes that reach it
LANES: List[Tuple[str, str, dict]] = [
    ("TimelyMon common", "TimelyMon common, watermarks", dict(color="#f6c08a", lw=6.0, ls="-")),
    ("TimelyMon tp-interval", "TimelyMon tp-interval, point claims", dict(color="tab:orange", lw=2.2, ls="-")),
    ("MonPoly", "MonPoly, as recorded", dict(color="#9fd49f", lw=1.4, ls=":")),
    ("MonPoly exact", "MonPoly, sorted input", dict(color="tab:green", lw=2.2, ls="-")),
    ("OOOMon", "OOOMon, the limit", dict(color="0.1", lw=1.3, ls=(0, (4, 3)))),
]
REFERENCE = "OOOMon"
BASELINE = "MonPoly exact"


TAIL = float("inf")


def first_lines(frame: dict) -> Tuple[Dict[tuple, float], int]:
    """Per verdict the number of lines fed when it was first emitted (TAIL for
    the end-of-input tail), and the number of lines of the whole input."""
    blocks = frame["blocks"]
    fed_rounds = [i for i, b in enumerate(blocks) if b.get("input_points") is not None]
    if fed_rounds != list(range(len(fed_rounds))):
        raise ValueError(f"{frame['source']}: input rounds are not the leading rounds")
    total = len(fed_rounds)
    first: Dict[tuple, float] = {}
    for e in extract(frame).emissions:
        lines = e.round + 1 if e.round < total else TAIL
        key = (e.point, e.valuation)
        first[key] = min(first.get(key, lines), lines)
    return first, total


def _formula(run_dir: str, setting: str, experiments: str) -> Optional[str]:
    try:
        _, files, _ = _lane_inputs(run_dir, setting.rsplit("_", 1)[0], "MonPoly", experiments)
    except (SystemExit, OSError, KeyError):
        return None
    with open(files["policy"]) as f:
        return " ".join(f.read().split())


def plot(run_dir: str, out: str, recorded: bool, experiments: str) -> None:
    settings: Dict[str, Dict[str, dict]] = {}
    for frame in load_frames(run_dir):
        settings.setdefault(frame["setting"], {})[frame["tool"]] = frame
    lanes = [lane for lane in LANES if recorded or lane[0] != "MonPoly"]
    names = sorted(settings)
    cols = 2 if len(names) > 1 else 1
    rows = (len(names) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(6.4 * cols, 4.9 * rows), squeeze=False)

    for n, (ax, setting) in enumerate(zip(axes.flat, names)):
        frames = settings[setting]
        firsts, total = {}, None
        for tool, _, _ in lanes:
            if tool in frames:
                firsts[tool], lines = first_lines(frames[tool])
                if total not in (None, lines):
                    raise ValueError(f"{setting}: lanes fed different numbers of lines")
                total = lines
        for tool, _, style in lanes:
            if tool not in firsts:
                continue
            xs = np.sort(np.fromiter((min(x, total) for x in firsts[tool].values()), dtype=np.float64))
            ax.step(np.concatenate([[0], xs, [total]]), np.concatenate([[0], np.arange(1, xs.size + 1), [xs.size]]),
                    where="post", solid_capstyle="butt", zorder=3, **style)
        verdicts = max(len(f) for f in firsts.values())
        ax.axvline(total, color="0.45", lw=0.9, ls=":", zorder=1)

        if BASELINE in firsts and REFERENCE in firsts:
            base, ref = firsts[BASELINE], firsts[REFERENCE]
            shared = [k for k in ref if k in base]
            behind = sum(base[k] > ref[k] for k in shared)
            leads = sorted(base[k] - ref[k] for k in shared if base[k] != TAIL and ref[k] != TAIL)
            at_end = sum(base[k] == TAIL and ref[k] != TAIL for k in shared)
            where = "every verdict" if behind == len(ref) else f"{behind:,} of {len(ref):,} verdicts"
            if leads:
                ax.text(0.98, 0.04,
                        f"MonPoly behind the limit on {where}:\n"
                        f"{np.median(leads):,.0f} lines (median), {leads[-1]:,.0f} (max),\n"
                        f"and {at_end:,} verdicts only at end of input",
                        transform=ax.transAxes, ha="right", va="bottom", fontsize=9, color="0.2",
                        bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="0.8", lw=0.8))

        label = setting.rsplit("_", 1)[0].split("_")[2] if setting.count("_") >= 4 else setting
        formula = textwrap.wrap(_formula(run_dir, setting, experiments) or "", 78)
        if formula:
            ax.text(0, 1.015, "\n".join(formula), transform=ax.transAxes,
                    ha="left", va="bottom", fontsize=7.2, family="monospace", color="0.3")
        ax.set_title(f"({'abcdefghij'[n]}) formula {label}: {verdicts:,} verdicts", fontsize=12, loc="left",
                     pad=6 + 9.5 * len(formula))
        ax.set_xlim(0, total * 1.02)
        ax.set_ylim(0, verdicts * 1.04 + 1)
        ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
        ax.grid(True, alpha=0.25)
        ax.set_xlabel("lines fed (events and claims)", fontsize=10.5)
        if n % cols == 0:
            ax.set_ylabel("verdicts emitted", fontsize=10.5)
    for ax in list(axes.flat)[len(names):]:
        ax.axis("off")

    handles = [Line2D([], [], label=label, **style) for tool, label, style in lanes
               if any(tool in settings[s] for s in names)]
    handles.append(Line2D([], [], color="0.45", lw=0.9, ls=":", label="end of input"))
    fig.legend(handles=handles, loc="lower center", ncol=min(len(handles), 3), fontsize=10, frameon=False)
    fig.tight_layout(rect=(0, 0.07 if len(handles) > 3 else 0.05, 1, 1), h_pad=2.5)
    os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m Infrastructure.Analysis.EmissionTiming.lines_fed",
        description="Cumulative verdicts against lines fed, one panel per setting.")
    parser.add_argument("run_dir", help="result folder of an online claim-family run (frames/, provenance/)")
    parser.add_argument("--recorded", action="store_true",
                        help="also draw the sorted lane as the driver recorded it (chain accounting)")
    parser.add_argument("--experiments", default="Infrastructure/experiments",
                        help="folder holding the experiments' generated inputs (for the formula text)")
    parser.add_argument("--out", help="output file (default: <run_dir>/emission_timing/cumulative_lines_fed.png)")
    args = parser.parse_args(argv)
    out = args.out or os.path.join(args.run_dir, "emission_timing", "cumulative_lines_fed.png")
    plot(args.run_dir, out, args.recorded, args.experiments)
    print(f"written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
