"""Per-step monitor latency vs. real-time replay position.

Two complementary input sources are supported:

Driver log path
    Reads an ``OnlineExperimentDriver`` stdout log directly.  Both x-axis
    variants are available:

    * ``ts``   – scheduled position ``(ts - ts0)`` from event timestamps.
    * ``wall`` – measured per-step ``[Wall Offset]`` (send instant after the
      pacing sleep).  Exposes lag/drift when the monitor cannot keep up.
      Falls back to ``ts`` when the log predates that field.

Result CSV path
    Reads the per-step ``output_pairs`` column written by ``AnalysisOnline``
    / ``BenchmarkBuilder`` (format: ``[[processed_count, elapsed_ns], ...]``).
    Valid runs, accumulative-timeout runs, and maximum-timeout runs are all
    merged onto one figure and colour-coded by status.  Accepts a single CSV,
    a folder that contains any of the three report files, or a DataFrame.
    x-axis: step index (0-based); real-time position is unavailable from the
    CSV alone.

API
---
    from Infrastructure.Analysis.AutomatedAnalysis.OnlineLatencyPlotter import (
        plot_latency_over_replay,   # driver-log path
        plot_latency_from_csv,      # result-CSV path
        parse_driver_log,
        parse_result_csv,
        LatencyReplaySummary,
    )

    # driver log — measured wall-clock x-axis
    s = plot_latency_over_replay("run.log", out="lat.png", x_source="wall")

    # iterable of lines (e.g. docker container.logs())
    s = plot_latency_over_replay(lines, out="lat.png", label="TimelyMon")

    # stats only, no figure
    s = plot_latency_over_replay("run.log", render=False)

    # result CSV folder (merges all three status groups)
    s = plot_latency_from_csv("/path/to/report/", out="lat_csv.png")

    # single CSV
    s = plot_latency_from_csv("successful_runs.csv", out="lat_ok.png")

    # DataFrame produced by AnalysisOnline.run()
    results = AnalysisOnline().run(aggregator)
    s = plot_latency_from_csv(results["successful_runs"], out="lat.png")

CLI
---
    python -m Infrastructure.Analysis.AutomatedAnalysis.OnlineLatencyPlotter \\
        run.log [--x-source wall] [--y-log] [--out lat.png]

    python -m Infrastructure.Analysis.AutomatedAnalysis.OnlineLatencyPlotter \\
        --csv /path/to/report/ [--y-log] [--out lat_csv.png]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import warnings
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg", force=False)   # headless-safe; never overrides a live backend
import matplotlib.pyplot as plt

__all__ = [
    # data types
    "ParsedReplay",
    "RunSeries",
    "LatencyReplaySummary",
    # parsing
    "parse_driver_log",
    "parse_result_csv",
    # plotting
    "plot_latency_over_replay",
    "plot_latency_from_csv",
    # constants
    "TS_UNIT_SECONDS",
    "Y_UNIT_FROM_NS",
    # CLI
    "main",
]

# --------------------------------------------------------------------------- #
# Constants / type aliases
# --------------------------------------------------------------------------- #

#: A log source: file path, raw log text, or iterable of str/bytes lines.
LogSource = Union[str, "os.PathLike[str]", Iterable[Union[str, bytes]]]

#: A CSV source: file path, folder path, or DataFrame.
CsvSource = Union[str, "os.PathLike[str]", pd.DataFrame]

#: seconds represented by one timestamp unit
TS_UNIT_SECONDS: Dict[str, float] = {
    "seconds": 1.0, "milliseconds": 1e-3, "microseconds": 1e-6,
}
#: factor to convert a nanosecond value into the chosen y unit
Y_UNIT_FROM_NS: Dict[str, float] = {
    "s": 1e-9, "ms": 1e-6, "us": 1e-3, "ns": 1.0,
}

# Status labels as written by BenchmarkBuilder / ResultAggregatorOnline
_STATUS_OK  = "OK"
_STATUS_ATO = "ATO"   # accumulative-latency timeout
_STATUS_MTO = "MTO"   # maximum-latency timeout

# Colours per status
_STATUS_COLOR: Dict[str, str] = {
    _STATUS_OK:  "tab:blue",
    _STATUS_ATO: "tab:orange",
    _STATUS_MTO: "tab:red",
}
_STATUS_LABEL: Dict[str, str] = {
    _STATUS_OK:  "OK",
    _STATUS_ATO: "Timeout (accumulative)",
    _STATUS_MTO: "Timeout (max latency)",
}

# Report file names produced by AnalysisOnline.save_report
_CSV_FILES: List[Tuple[str, str]] = [
    ("successful_runs.csv",                     _STATUS_OK),
    ("timeout_accumulative_latency_details.csv", _STATUS_ATO),
    ("timeout_maximum_latency_details.csv",      _STATUS_MTO),
]

_TS_RE      = re.compile(r"ts\s*=\s*(\d+)")
_ELAPSED_RE = re.compile(r"^\[Elapsed\]\s+(\d+)")
_WALLOFF_RE = re.compile(r"^\[Wall Offset\]\s+(\d+)")


# =========================================================================== #
# Data classes
# =========================================================================== #

@dataclass
class ParsedReplay:
    """Per-step series extracted from a driver log (parallel arrays)."""
    ts_offset:        np.ndarray   # (ts – ts0) in raw timestamp units
    wall_ns:          np.ndarray   # measured wall offset (ns); NaN where absent
    latency_ns:       np.ndarray   # per-step [Elapsed] latency (ns)
    ts0:              Optional[int]   = None
    timeout_ts_offset: Optional[float] = None
    timeout_wall_ns:   Optional[float] = None
    timeout_message:   Optional[str]   = None
    footers: Dict[str, str] = field(default_factory=dict)

    @property
    def steps(self) -> int:
        return int(self.latency_ns.size)

    @property
    def has_wall(self) -> bool:
        return self.wall_ns.size > 0 and not bool(np.all(np.isnan(self.wall_ns)))

    @property
    def timed_out(self) -> bool:
        return self.timeout_message is not None


@dataclass
class RunSeries:
    """Per-step series for one run row extracted from a result CSV."""
    name:       str
    setting:    str
    status:     str              # OK / ATO / MTO
    steps:      int
    processed:  np.ndarray      # cumulative processed-event counts per step
    latency_ns: np.ndarray      # per-step elapsed latency (ns)


@dataclass
class LatencyReplaySummary:
    """Return value of both plot functions."""
    out_path:        Optional[str]
    steps:           int
    span_s:          float          # x-axis range in seconds (or steps for CSV)
    p50_ms:          float
    p99_ms:          float
    max_ms:          float
    x_source:        str            # "ts" | "wall" | "step"
    timed_out:       bool
    timeout_message: Optional[str]
    footers:         Dict[str, str]

    def as_dict(self) -> Dict[str, object]:
        return {k: v for k, v in self.__dict__.items()}


# =========================================================================== #
# Parsing — driver log
# =========================================================================== #

def _iter_lines(source: LogSource) -> Iterable[str]:
    """Yield text lines from a path, raw log text, or an iterable of lines."""
    if isinstance(source, (str, os.PathLike)) and os.path.exists(source):
        with open(source, "r", errors="ignore") as fh:
            yield from fh
        return
    if isinstance(source, str):
        yield from source.splitlines()
        return
    for line in source:          # iterable of str/bytes (e.g. container.logs())
        yield (line.decode("utf-8", errors="ignore")
               if isinstance(line, (bytes, bytearray)) else line)


def parse_driver_log(source: LogSource) -> ParsedReplay:
    """Parse an OnlineExperimentDriver log into a :class:`ParsedReplay`.

    Accepts a file path, raw log text, or any iterable of lines.
    Raises :class:`ValueError` when no ``[Elapsed]`` steps are found.
    """
    ts0:          Optional[int] = None
    pending_ts:   Optional[int] = None
    pending_wall: Optional[int] = None
    rel_ts:  List[float] = []
    wall_ns: List[float] = []
    lat_ns:  List[int]   = []
    timeout = None        # (ts_or_None, wall_or_None, message)
    footers: Dict[str, str] = {}

    for line in _iter_lines(source):
        if line.startswith("[Input"):
            m = _TS_RE.search(line)
            if m:
                t = int(m.group(1))
                if ts0 is None:
                    ts0 = t
                pending_ts = t
        elif line.startswith("[Wall Offset]"):
            m = _WALLOFF_RE.match(line)
            if m:
                pending_wall = int(m.group(1))
        elif line.startswith("[Elapsed]"):
            m = _ELAPSED_RE.match(line)
            if m:
                rel_ts.append(float(pending_ts if pending_ts is not None else (ts0 or 0)))
                wall_ns.append(float(pending_wall) if pending_wall is not None else np.nan)
                lat_ns.append(int(m.group(1)))
                pending_wall = None
        elif line.startswith("[Error"):
            timeout = (pending_ts, pending_wall, line.strip())
        elif line.startswith("[Wall Clock]"):
            footers["wall_clock"] = line.split("]", 1)[1].strip()
        elif line.startswith("[Accumulative Elapsed]"):
            footers["accumulative"] = line.split("]", 1)[1].strip()
        elif line.startswith("[Total Count]"):
            footers["total_count"] = line.split("]", 1)[1].strip()

    if not lat_ns:
        raise ValueError("no [Elapsed] steps found — is this an OnlineExperimentDriver log?")

    ts0 = ts0 if ts0 is not None else int(rel_ts[0])
    t_ts   = None if (timeout is None or timeout[0] is None) else float(timeout[0] - ts0)
    t_wall = None if (timeout is None or timeout[1] is None) else float(timeout[1])
    return ParsedReplay(
        ts_offset        = np.asarray(rel_ts,  dtype=np.float64) - ts0,
        wall_ns          = np.asarray(wall_ns, dtype=np.float64),
        latency_ns       = np.asarray(lat_ns,  dtype=np.float64),
        ts0              = ts0,
        timeout_ts_offset = t_ts,
        timeout_wall_ns   = t_wall,
        timeout_message   = timeout[2] if timeout else None,
        footers           = footers,
    )


# =========================================================================== #
# Parsing — result CSV
# =========================================================================== #

def _parse_output_pairs(raw) -> Tuple[np.ndarray, np.ndarray]:
    """Parse one ``output_pairs`` cell → (processed_counts, latency_ns)."""
    if pd.isna(raw) or raw == "":
        return np.array([], dtype=np.float64), np.array([], dtype=np.float64)
    try:
        pairs = json.loads(raw) if isinstance(raw, str) else raw
    except (ValueError, TypeError):
        return np.array([], dtype=np.float64), np.array([], dtype=np.float64)
    if not isinstance(pairs, list) or len(pairs) == 0:
        return np.array([], dtype=np.float64), np.array([], dtype=np.float64)
    processed = np.asarray([p[0] for p in pairs if len(p) >= 2], dtype=np.float64)
    latency   = np.asarray([p[1] for p in pairs if len(p) >= 2], dtype=np.float64)
    return processed, latency


def _df_to_series(df: pd.DataFrame, status: str) -> List[RunSeries]:
    """Convert one result DataFrame (one status group) into RunSeries list."""
    out = []
    if df.empty or "output_pairs" not in df.columns:
        return out
    for _, row in df.iterrows():
        processed, lat_ns = _parse_output_pairs(row.get("output_pairs"))
        if lat_ns.size == 0:
            continue
        out.append(RunSeries(
            name       = str(row.get("Name",    "")),
            setting    = str(row.get("Setting", "")),
            status     = status,
            steps      = int(lat_ns.size),
            processed  = processed,
            latency_ns = lat_ns,
        ))
    return out


def parse_result_csv(source: CsvSource) -> List[RunSeries]:
    """Parse result CSVs into a list of :class:`RunSeries`.

    Parameters
    ----------
    source:
        * A **folder** – auto-discovers ``successful_runs.csv``,
          ``timeout_accumulative_latency_details.csv``,
          ``timeout_maximum_latency_details.csv``.
        * A **single CSV path** – status inferred from the filename, defaulting
          to ``OK`` when unrecognised.
        * A **DataFrame** – treated as a single status group; a ``Status``
          column is used if present, otherwise assumed ``OK``.

    Returns
    -------
    List[RunSeries]
        One entry per parseable run row (rows with empty ``output_pairs``
        are skipped).
    """
    if isinstance(source, pd.DataFrame):
        # Infer status from a Status column when present.
        status_col = source.get("Status") if "Status" in source.columns else None
        if status_col is not None:
            series: List[RunSeries] = []
            for st, grp in source.groupby("Status"):
                series.extend(_df_to_series(grp, str(st)))
            return series
        return _df_to_series(source, _STATUS_OK)

    path = os.fspath(source)
    if os.path.isdir(path):
        series = []
        for fname, status in _CSV_FILES:
            full = os.path.join(path, fname)
            if os.path.exists(full):
                df = pd.read_csv(full)
                series.extend(_df_to_series(df, status))
        return series

    # Single CSV — infer status from filename.
    basename = os.path.basename(path).lower()
    status = _STATUS_OK
    for fname, st in _CSV_FILES:
        if fname.lower() in basename or basename in fname.lower():
            status = st
            break
    df = pd.read_csv(path)
    return _df_to_series(df, status)


# =========================================================================== #
# Shared helpers
# =========================================================================== #

def _downsample(x: np.ndarray, y: np.ndarray, max_points: int):
    """Cap point count, always preserving the top-1% latency spikes."""
    if not max_points or x.size <= max_points:
        return x, y
    k = max(1, x.size // 100)
    keep = np.zeros(x.size, dtype=bool)
    keep[np.argpartition(y, -k)[-k:]] = True
    rest   = np.where(~keep)[0]
    budget = max_points - int(keep.sum())
    if budget > 0 and rest.size > budget:
        keep[rest[np.linspace(0, rest.size - 1, budget).astype(int)]] = True
    elif budget > 0:
        keep[rest] = True
    return x[keep], y[keep]


def _save_fig(fig, out: Optional[Union[str, "os.PathLike[str]"]]):
    parent = os.path.dirname(os.fspath(out)) if out else ""
    if parent:
        os.makedirs(parent, exist_ok=True)
    fig.savefig(os.fspath(out), dpi=150)
    plt.close(fig)


# =========================================================================== #
# Plot — driver log
# =========================================================================== #

def plot_latency_over_replay(
    log: Union[LogSource, ParsedReplay],
    out: Optional[Union[str, "os.PathLike[str]"]] = "latency_over_replay.png",
    *,
    x_source:        str            = "ts",
    timestamp_units: str            = "milliseconds",
    y_unit:          str            = "ms",
    y_log:           bool           = False,
    threshold_ms:    Optional[float] = None,
    drop_warmup:     int            = 0,
    max_points:      int            = 400_000,
    render:          bool           = True,
    title:           Optional[str]  = None,
    label:           Optional[str]  = None,
) -> LatencyReplaySummary:
    """Plot per-step latency from a driver log against real-time replay position.

    Parameters
    ----------
    log:
        File path, raw log text, iterable of lines, or a pre-parsed
        :class:`ParsedReplay`.
    out:
        Output image path (PNG/PDF/SVG).  Ignored when *render* is ``False``.
    x_source:
        ``"ts"`` (scheduled, from event timestamps) or ``"wall"`` (measured
        per-step wall offset).  ``"wall"`` falls back to ``"ts"`` with a
        warning if the log has no ``[Wall Offset]`` lines.
    timestamp_units:
        How to scale trace timestamps to seconds for the ``ts`` x-axis.
    y_unit:
        Latency unit shown on the y-axis (``s`` / ``ms`` / ``us`` / ``ns``).
    y_log:
        Log-scale the latency axis.
    threshold_ms:
        Draw a horizontal threshold line (e.g. the maximum-latency budget).
    drop_warmup:
        Drop the first *N* steps (e.g. a JIT cold-start spike).
    max_points:
        Downsample cap; top-1% latency spikes are always preserved.
    render:
        When ``False``, return stats only without drawing (``out_path=None``).
    title, label:
        Custom plot title / display name used in the default title.
    """
    if x_source not in ("ts", "wall"):
        raise ValueError(f"x_source must be 'ts' or 'wall', got {x_source!r}")
    if timestamp_units not in TS_UNIT_SECONDS:
        raise ValueError(f"timestamp_units must be one of {sorted(TS_UNIT_SECONDS)}")
    if y_unit not in Y_UNIT_FROM_NS:
        raise ValueError(f"y_unit must be one of {sorted(Y_UNIT_FROM_NS)}")

    parsed = log if isinstance(log, ParsedReplay) else parse_driver_log(log)

    rel_ts, wall_ns, lat_ns = parsed.ts_offset, parsed.wall_ns, parsed.latency_ns
    if drop_warmup:
        n = drop_warmup
        rel_ts, wall_ns, lat_ns = rel_ts[n:], wall_ns[n:], lat_ns[n:]
        if lat_ns.size == 0:
            raise ValueError("drop_warmup removed all steps")

    xfac = TS_UNIT_SECONDS[timestamp_units]
    yfac = Y_UNIT_FROM_NS[y_unit]

    use_wall = x_source == "wall" and not bool(np.all(np.isnan(wall_ns)))
    if x_source == "wall" and not use_wall:
        warnings.warn("no [Wall Offset] in log; falling back to x_source='ts'", stacklevel=2)

    if use_wall:
        x         = wall_ns * 1e-9
        x_label   = "Real-time replay position (s) — measured wall-clock"
        timeout_x = None if parsed.timeout_wall_ns is None else parsed.timeout_wall_ns * 1e-9
        eff_src   = "wall"
    else:
        x         = rel_ts * xfac
        x_label   = "Real-time replay position (s) — event timestamps"
        timeout_x = None if parsed.timeout_ts_offset is None else parsed.timeout_ts_offset * xfac
        eff_src   = "ts"

    lat_ms = lat_ns / 1e6
    p50, p99, ymax = (float(np.percentile(lat_ms, q))
                      for q in (50, 99, 100))

    mask = ~np.isnan(x)
    x, y = x[mask], (lat_ns * yfac)[mask]
    span_s = float(x.max()) if x.size else 0.0

    out_path: Optional[str] = None
    if render:
        if out is None:
            raise ValueError("out must be set when render=True")
        src_name = label or (
            os.fspath(log) if isinstance(log, (str, os.PathLike)) and os.path.exists(log)
            else "driver log"
        )
        xs, ys = _downsample(x, y, max_points)
        fig, ax = plt.subplots(figsize=(12, 5))
        ax.scatter(xs, ys, s=3, alpha=0.5, edgecolors="none", rasterized=True,
                   label="per-step latency")
        if y_log:
            ax.set_yscale("log")
        if threshold_ms is not None:
            ax.axhline(threshold_ms * 1e6 * yfac, color="tab:red", ls="--", lw=1,
                       label=f"threshold {threshold_ms:g} ms")
        if timeout_x is not None:
            ax.axvline(timeout_x, color="black", ls=":", lw=1.5, label="timeout")
        ax.set_xlim(left=0)
        ax.set_xlabel(x_label)
        ax.set_ylabel(f"Per-step latency ({y_unit})")
        ax.set_title(title or (
            f"Per-step latency over replay — {src_name}\n"
            f"{lat_ns.size} steps, span {span_s:.1f}s, "
            f"p50 {p50:.3f}ms / p99 {p99:.3f}ms / max {ymax:.3f}ms"
        ))
        ax.grid(True, which="both", alpha=0.3)
        ax.legend(loc="upper right", fontsize=8)
        fig.tight_layout()
        out_path = os.fspath(out)
        _save_fig(fig, out_path)

    return LatencyReplaySummary(
        out_path        = out_path,
        steps           = int(lat_ns.size),
        span_s          = span_s,
        p50_ms          = p50,
        p99_ms          = p99,
        max_ms          = ymax,
        x_source        = eff_src,
        timed_out       = parsed.timed_out,
        timeout_message = parsed.timeout_message,
        footers         = dict(parsed.footers),
    )


# =========================================================================== #
# Plot — result CSVs (merged valid + timeout)
# =========================================================================== #

def plot_latency_from_csv(
    source: CsvSource,
    out: Optional[Union[str, "os.PathLike[str]"]] = "latency_from_csv.png",
    *,
    y_unit:       str            = "ms",
    y_log:        bool           = False,
    threshold_ms: Optional[float] = None,
    drop_warmup:  int            = 0,
    max_points:   int            = 400_000,
    render:       bool           = True,
    title:        Optional[str]  = None,
) -> LatencyReplaySummary:
    """Plot per-step latency from result CSVs, merging all status groups.

    Valid (OK), accumulative-timeout (ATO) and maximum-timeout (MTO) runs are
    overlaid on the same figure with distinct colours.  The x-axis is step
    index (0-based); real-time position is not available from the CSV alone.

    Parameters
    ----------
    source:
        A folder (auto-discovers the three report files), a single CSV path,
        or a DataFrame already loaded by ``AnalysisOnline``.
    out:
        Output image path.  Ignored when *render* is ``False``.
    y_unit:
        Latency unit (``s`` / ``ms`` / ``us`` / ``ns``).
    y_log:
        Log-scale the latency axis.
    threshold_ms:
        Draw a horizontal threshold line.
    drop_warmup:
        Drop the first *N* steps from every series.
    max_points:
        Per-series downsample cap.
    render:
        When ``False``, return stats only.
    title:
        Custom plot title.
    """
    if y_unit not in Y_UNIT_FROM_NS:
        raise ValueError(f"y_unit must be one of {sorted(Y_UNIT_FROM_NS)}")

    all_series = parse_result_csv(source)
    if not all_series:
        raise ValueError("no parseable run series found in source")

    yfac = Y_UNIT_FROM_NS[y_unit]

    # Aggregate stats across ALL series for the summary.
    all_lat_ms: List[float] = []
    for s in all_series:
        lat = s.latency_ns[drop_warmup:] if drop_warmup else s.latency_ns
        all_lat_ms.extend((lat / 1e6).tolist())

    lat_ms_arr = np.asarray(all_lat_ms, dtype=np.float64)
    p50  = float(np.percentile(lat_ms_arr, 50))
    p99  = float(np.percentile(lat_ms_arr, 99))
    ymax = float(lat_ms_arr.max())
    total_steps = sum(s.steps for s in all_series)
    span_steps  = max(
        (s.latency_ns[drop_warmup:].size if drop_warmup < s.steps else 0)
        for s in all_series
    )

    timed_out = any(s.status in (_STATUS_ATO, _STATUS_MTO) for s in all_series)

    out_path: Optional[str] = None
    if render:
        if out is None:
            raise ValueError("out must be set when render=True")

        # Build one scatter series per (status, name) combination so the legend
        # is readable even with many runs.  Colour by status, alpha by run count.
        fig, ax = plt.subplots(figsize=(12, 5))

        # Track which status labels have already been added to the legend.
        _legend_seen: set = set()

        for run in all_series:
            lat = run.latency_ns[drop_warmup:] if drop_warmup < run.steps else run.latency_ns
            if lat.size == 0:
                continue
            x = np.arange(lat.size, dtype=np.float64)
            y = lat * yfac
            xs, ys = _downsample(x, y, max_points)
            color = _STATUS_COLOR.get(run.status, "tab:gray")
            legend_key = run.status
            label_str = (
                f"{_STATUS_LABEL.get(run.status, run.status)} — {run.name} / {run.setting}"
                if legend_key not in _legend_seen
                else None
            )
            _legend_seen.add(legend_key)
            ax.scatter(xs, ys, s=3, alpha=0.45, edgecolors="none",
                       rasterized=True, color=color, label=label_str)

        if y_log:
            ax.set_yscale("log")
        if threshold_ms is not None:
            ax.axhline(threshold_ms * 1e6 * yfac, color="black", ls="--", lw=1,
                       label=f"threshold {threshold_ms:g} ms")

        ax.set_xlim(left=0)
        ax.set_xlabel("Step index")
        ax.set_ylabel(f"Per-step latency ({y_unit})")

        status_counts = {st: sum(1 for s in all_series if s.status == st)
                         for st in (_STATUS_OK, _STATUS_ATO, _STATUS_MTO)}
        status_summary = ", ".join(
            f"{_STATUS_LABEL[st]}={n}" for st, n in status_counts.items() if n > 0
        )
        ax.set_title(title or (
            f"Per-step latency — merged results ({status_summary})\n"
            f"{total_steps} total steps, "
            f"p50 {p50:.3f}ms / p99 {p99:.3f}ms / max {ymax:.3f}ms"
        ))
        ax.grid(True, which="both", alpha=0.3)
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(handles, labels, loc="upper right", fontsize=8,
                      markerscale=3)
        fig.tight_layout()
        out_path = os.fspath(out)
        _save_fig(fig, out_path)

    return LatencyReplaySummary(
        out_path        = out_path,
        steps           = total_steps,
        span_s          = float(span_steps),    # steps, not seconds
        p50_ms          = p50,
        p99_ms          = p99,
        max_ms          = ymax,
        x_source        = "step",
        timed_out       = timed_out,
        timeout_message = None,
        footers         = {},
    )


# =========================================================================== #
# CLI
# =========================================================================== #

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        prog="OnlineLatencyPlotter",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("log", nargs="?",
                     help="OnlineExperimentDriver stdout log (driver-log mode)")
    src.add_argument("--csv", metavar="PATH",
                     help="result CSV file or folder produced by AnalysisOnline "
                          "(CSV mode — merges all status groups)")

    ap.add_argument("--x-source", choices=["ts", "wall"], default="ts",
                    help="(driver-log only) x-axis: timestamps or wall-clock offset")
    ap.add_argument("--timestamp-units", choices=list(TS_UNIT_SECONDS),
                    default="milliseconds")
    ap.add_argument("--y-unit", choices=list(Y_UNIT_FROM_NS), default="ms")
    ap.add_argument("--y-log", action="store_true")
    ap.add_argument("--threshold-ms", type=float, default=None)
    ap.add_argument("--drop-warmup", type=int, default=0)
    ap.add_argument("--max-points", type=int, default=400_000)
    ap.add_argument("--out", default=None,
                    help="output image path (default: latency_over_replay.png "
                         "or latency_from_csv.png)")
    args = ap.parse_args(argv)

    try:
        if args.csv:
            out = args.out or "latency_from_csv.png"
            summary = plot_latency_from_csv(
                args.csv, out=out, y_unit=args.y_unit, y_log=args.y_log,
                threshold_ms=args.threshold_ms, drop_warmup=args.drop_warmup,
                max_points=args.max_points,
            )
        else:
            out = args.out or "latency_over_replay.png"
            summary = plot_latency_over_replay(
                args.log, out=out, x_source=args.x_source,
                timestamp_units=args.timestamp_units, y_unit=args.y_unit,
                y_log=args.y_log, threshold_ms=args.threshold_ms,
                drop_warmup=args.drop_warmup, max_points=args.max_points,
            )
    except (ValueError, OSError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    print(f"steps          : {summary.steps}")
    print(f"span           : {summary.span_s:.1f} ({'s' if summary.x_source != 'step' else 'steps'})")
    print(f"latency p50    : {summary.p50_ms:.3f} ms")
    print(f"latency p99    : {summary.p99_ms:.3f} ms")
    print(f"latency max    : {summary.max_ms:.3f} ms")
    if summary.footers:
        print(f"driver footers : {summary.footers}")
    if summary.timed_out:
        print(f"TIMEOUT        : {summary.timeout_message or 'yes'}")
    print(f"wrote          : {summary.out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
