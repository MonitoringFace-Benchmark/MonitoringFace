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

Suite results folder
    Reads the results folder of a suite run (one subfolder per experiment,
    each with ``<experiment>_valid.csv`` / ``..._timeout_accumulative_latency.csv``
    / ``..._timeout_maximum_latency.csv`` and a ``provenance`` folder).  Runs
    of all experiments are pooled and grouped by the formula they ran, which
    is read from the provenance of their setting.  One figure is written per
    formula with every tool that ran it.  A figure config (dict, JSON string,
    or JSON/YAML file) sets title, axis labels, legend, log scale, and so on
    per figure, keyed by formula name (``"default"`` applies to all figures).

API
---
    from Infrastructure.Analysis.AutomatedAnalysis.OnlineLatencyPlotter import (
        plot_latency_over_replay,   # driver-log path
        plot_latency_from_csv,      # result-CSV path
        plot_suite,                 # suite results folder, one figure per formula
        parse_driver_log,
        parse_result_csv,
        load_suite,
        LatencyReplaySummary,
        FIGURE_DEFAULTS,            # every per-figure option and its default
    )

    # suite folder — one figure per formula, titles per figure
    summaries = plot_suite(
        "Infrastructure/results/<suite>_<timestamp>",
        figure_config={
            "default":        {"y_log": True, "legend_loc": "upper left"},
            "formula_delete": {"title": "DELETE"},
            "formula_select": {"title": "SELECT", "out": "select.svg"},
        },
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

    python -m Infrastructure.Analysis.AutomatedAnalysis.OnlineLatencyPlotter \\
        --suite Infrastructure/results/<suite>_<timestamp> \\
        [--out-dir plots] [--format svg] \\
        [--figure-config '{"default": {"y_log": true}, "formula_delete": {"title": "DELETE"}}']
        [--figure-config figures.yaml]

    --figure-config takes an inline JSON object or the path of a JSON/YAML file.
    Keys are formula names (as the provenance names the policy file, without
    extension), the setting block ("0", "1", ...), or "default". Values are
    dicts of the options listed in FIGURE_DEFAULTS, e.g. title, xlabel,
    ylabel, legend, legend_loc, y_log, y_unit, threshold_ms, window, colors,
    out. Other command-line flags (--y-log, --y-unit, ...) fill "default".
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

import csv
csv.field_size_limit(min(sys.maxsize, 2**31 - 1))   # sys.maxsize overflows a C long on Windows

__all__ = [
    # data types
    "ParsedReplay",
    "RunSeries",
    "LatencyReplaySummary",
    # parsing
    "parse_driver_log",
    "parse_result_csv",
    "load_suite",
    "formula_of_setting",
    "load_figure_config",
    # plotting
    "plot_latency_over_replay",
    "plot_latency_from_csv",
    "plot_suite",
    # constants
    "TS_UNIT_SECONDS",
    "Y_UNIT_FROM_NS",
    "FIGURE_DEFAULTS",
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
# Suffixes of the files ResultAggregatorOnline.save writes into an experiment
# folder: <experiment_name><suffix>
_SUITE_SUFFIXES: List[Tuple[str, str]] = [
    ("_valid.csv",                        _STATUS_OK),
    ("_timeout_accumulative_latency.csv", _STATUS_ATO),
    ("_timeout_maximum_latency.csv",      _STATUS_MTO),
]

# Default colour per tool; a figure config may override or extend it
_SERIES_COLORS: Dict[str, str] = {
    "WhyMon":    "tab:blue",
    "TimelyMon": "tab:orange",
    "MonPoly":   "tab:green",
    "VeriMon":   "tab:red",
    "EnfGuard":  "tab:purple",
}

#: Every option a figure config may set, with its default. "default" in a
#: config applies to all figures; a formula's entry overrides it.
FIGURE_DEFAULTS: Dict[str, object] = {
    "title":           None,           # figure title; None for no title
    "xlabel":          "Step index",
    "ylabel":          None,           # None: "Per-step latency (<y_unit>)"
    "y_unit":          "ms",           # one of Y_UNIT_FROM_NS
    "y_log":           False,
    "y_tick_format":   "auto",         # "auto": matplotlib's (10^k on a log axis); "plain": 0.1, 1, 10, ...
    "ylim":            None,           # [low, high]; None for auto
    "xlim":            None,           # [low, high]; None for [0, auto]
    "threshold_ms":    None,           # horizontal dashed line, in ms
    "drop_warmup":     0,              # steps dropped at the start of every run
    "max_points":      400_000,        # downsampling cap per run
    "window":          100,            # rolling-mean window in steps; 1 for raw
    "linewidth":       1.5,
    "alpha":           0.8,
    "colors":          {},             # tool name -> matplotlib colour, on top of the defaults
    "labels":          {},             # tool name -> legend label
    "legend":          True,
    "legend_loc":      "upper right",
    "legend_fontsize": 16,
    "fontsize":        20,             # axis label size
    "title_fontsize":  20,
    "tick_fontsize":   None,           # None keeps matplotlib's default
    "figsize":         [12, 5],
    "grid":            True,
    "mark_timeouts":   True,           # "x" at the last step of a timed-out run
    "out":             None,           # file name or path; None: <formula>.<format>
}

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

"""def _parse_output_pairs(raw) -> Tuple[np.ndarray, np.ndarray]:
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
    return out"""


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

    proc_list = []
    lat_list = []
    for p in pairs:
        # Only include pairs with 2+ valid elements
        if isinstance(p, (list, tuple)) and len(p) >= 2:
            try:
                proc_list.append(float(p[0]))
                lat_list.append(float(p[1]))
            except (ValueError, TypeError):
                pass  # Skip invalid numeric values

    return np.asarray(proc_list, dtype=np.float64), np.asarray(lat_list, dtype=np.float64)


def _df_to_series(df: pd.DataFrame, status: str) -> List[RunSeries]:
    """Convert one result DataFrame (one status group) into RunSeries list."""
    out = []
    if df.empty or "output_pairs" not in df.columns:
        return out
    for _, row in df.iterrows():
        processed, lat_ns = _parse_output_pairs(row.get("output_pairs"))
        # Only skip if the array is empty or contains strictly NaNs
        if lat_ns.size == 0 or np.all(np.isnan(lat_ns)):
            continue
        out.append(RunSeries(
            name=str(row.get("Name", "")),
            setting=str(row.get("Setting", "")),
            status=status,
            steps=int(lat_ns.size),
            processed=processed,
            latency_ns=lat_ns,
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
        for full, status in _discover_csvs(path):
            series.extend(_df_to_series(pd.read_csv(full), status))
        return series

    df = pd.read_csv(path)
    return _df_to_series(df, _status_of_filename(path))


def _status_of_filename(path: str) -> str:
    """Status group of a result CSV by its name (report names and suite suffixes)."""
    basename = os.path.basename(path).lower()
    for fname, st in _CSV_FILES:
        if fname.lower() in basename or basename in fname.lower():
            return st
    for suffix, st in _SUITE_SUFFIXES:
        if basename.endswith(suffix):
            return st
    return _STATUS_OK


def _discover_csvs(folder: str) -> List[Tuple[str, str]]:
    """(path, status) of the result CSVs directly in ``folder``: the report files
    of AnalysisOnline.save_report and the suffixed files of ResultAggregatorOnline."""
    found: List[Tuple[str, str]] = []
    for fname, status in _CSV_FILES:
        full = os.path.join(folder, fname)
        if os.path.exists(full):
            found.append((full, status))
    for entry in sorted(os.listdir(folder)):
        for suffix, status in _SUITE_SUFFIXES:
            if entry.endswith(suffix):
                found.append((os.path.join(folder, entry), status))
    return found


# =========================================================================== #
# Parsing — suite results folder
# =========================================================================== #

def _setting_block(setting: str) -> str:
    """'1_0' -> '1': the setting without its trailing repeat index."""
    parts = str(setting).split("_")
    return "_".join(parts[:-1]) if len(parts) > 1 else parts[0]


def formula_of_setting(experiment_dir: Union[str, "os.PathLike[str]"], setting: str) -> str:
    """Name of the policy file a setting ran, from ``provenance/<block>/<tool>/provenance.json``.

    Falls back to ``setting <block>`` when the experiment folder has no
    provenance for the setting.
    """
    block = _setting_block(setting)
    prov_dir = os.path.join(os.fspath(experiment_dir), "provenance", block)
    if not os.path.isdir(prov_dir):
        return f"setting {block}"
    for tool in sorted(os.listdir(prov_dir)):
        record = os.path.join(prov_dir, tool, "provenance.json")
        if not os.path.exists(record):
            continue
        with open(record, "r", encoding="utf-8") as fh:
            entries = json.load(fh).get("entries", [])
        for entry in entries:
            if entry.get("kind") != "policy":
                continue
            source = entry.get("source") or {}
            policy = (source.get("file") if isinstance(source, dict) else None) or entry.get("as_seen_by_tool")
            if policy:
                return os.path.splitext(os.path.basename(str(policy)))[0]
    return f"setting {block}"


def load_suite(suite_dir: Union[str, "os.PathLike[str]"]) -> Dict[str, List[RunSeries]]:
    """Runs of every experiment in a suite results folder, grouped by formula.

    ``suite_dir`` is the results folder of a suite run (one subfolder per
    experiment) or a single experiment folder.  Returns an ordered dict
    ``formula name -> runs`` in the order of the settings; the runs of a
    formula are sorted by tool name, then setting.
    """
    root = os.fspath(suite_dir)
    if not os.path.isdir(root):
        raise ValueError(f"{root}: not a folder")
    experiments = [root] if _discover_csvs(root) else sorted(
        os.path.join(root, d) for d in os.listdir(root)
        if os.path.isdir(os.path.join(root, d)) and _discover_csvs(os.path.join(root, d))
    )
    if not experiments:
        raise ValueError(f"{root}: no result CSVs found in the folder or its subfolders")

    keyed: Dict[Tuple[int, str], List[RunSeries]] = {}
    for exp in experiments:
        for run in parse_result_csv(exp):
            block = _setting_block(run.setting)
            order = int(block) if block.isdigit() else sys.maxsize
            key = (order, formula_of_setting(exp, run.setting))
            keyed.setdefault(key, []).append(run)

    grouped: Dict[str, List[RunSeries]] = {}
    for (_, formula), runs in sorted(keyed.items(), key=lambda kv: kv[0]):
        grouped.setdefault(formula, []).extend(sorted(runs, key=lambda r: (r.name, r.setting)))
    return grouped


def load_figure_config(spec) -> Dict[str, Dict[str, object]]:
    """Figure config from a dict, an inline JSON string, or a JSON/YAML file path."""
    if spec is None:
        return {}
    if isinstance(spec, dict):
        config = spec
    else:
        text = str(spec).strip()
        if os.path.exists(text):
            with open(text, "r", encoding="utf-8") as fh:
                if text.lower().endswith((".yaml", ".yml")):
                    import yaml
                    config = yaml.safe_load(fh)
                else:
                    config = json.load(fh)
        else:
            try:
                config = json.loads(text)
            except ValueError as exc:
                raise ValueError(f"figure config is neither a file nor valid JSON: {exc}") from exc
    if not isinstance(config, dict):
        raise ValueError("figure config must be a mapping of figure name -> options")
    unknown = {k for opts in config.values() if isinstance(opts, dict) for k in opts} - set(FIGURE_DEFAULTS)
    if unknown:
        raise ValueError(f"unknown figure option(s): {', '.join(sorted(unknown))}; "
                         f"known: {', '.join(FIGURE_DEFAULTS)}")
    return {str(k): dict(v or {}) for k, v in config.items()}


def _figure_options(config: Dict[str, Dict[str, object]], *names: str,
                    overrides: Optional[Dict[str, object]] = None) -> Dict[str, object]:
    """FIGURE_DEFAULTS <- overrides <- config['default'] <- config[name] for each name."""
    opts = dict(FIGURE_DEFAULTS)
    opts.update({k: v for k, v in (overrides or {}).items() if v is not None})
    opts.update(config.get("default", {}))
    for name in names:
        opts.update(config.get(name, {}))
    return opts


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
    """Save by the extension of ``out`` (svg when it has none), tightly cropped."""
    out = os.fspath(out)
    parent = os.path.dirname(out)
    if parent:
        os.makedirs(parent, exist_ok=True)
    ext = os.path.splitext(out)[1].lstrip(".").lower()
    fig.savefig(out, format=ext or "svg", dpi=150, bbox_inches="tight")
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
    """Plot per-step latency from a driver log against real-time replay position."""

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
    p50, p99, ymax = (float(np.percentile(lat_ms, q)) for q in (50, 99, 100))

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
        ax.set_xlabel(x_label, fontsize=12)
        ax.set_ylabel(f"Per-step latency ({y_unit})", fontsize=12)
        ax.set_title(title or (
            f"Per-step latency over replay — {src_name}\n"
            f"{lat_ns.size} steps, span {span_s:.1f}s, "
            f"p50 {p50:.3f}ms / p99 {p99:.3f}ms / max {ymax:.3f}ms"
        ))
        ax.grid(True, which="both", alpha=0.3)
        ax.legend(loc="upper right", fontsize=16)
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


def plot_latency_from_csv(
        source: CsvSource,
        out: Optional[Union[str, "os.PathLike[str]"]] = "latency_from_csv.png",
        *,
        y_unit: str = "ms",
        y_log: bool = False,
        threshold_ms: Optional[float] = None,
        drop_warmup: int = 0,
        max_points: int = 400_000,
        render: bool = True,
        title: Optional[str] = None,
) -> LatencyReplaySummary:
    """Plot the per-step latency of every run in the CSV source on one figure."""
    all_series = parse_result_csv(source)
    if not all_series:
        raise ValueError("no parseable run series found in source")
    opts = _figure_options({}, overrides={
        "y_unit": y_unit, "y_log": y_log, "threshold_ms": threshold_ms,
        "drop_warmup": drop_warmup, "max_points": max_points, "title": title,
    })
    return _render_series(all_series, out if render else None, opts)


def _render_series(
    all_series: List[RunSeries],
    out: Optional[Union[str, "os.PathLike[str]"]],
    opts: Dict[str, object],
) -> LatencyReplaySummary:
    """Draw the rolling-mean latency of every run over its step index.

    ``opts`` holds every key of :data:`FIGURE_DEFAULTS`.  With ``out`` None,
    only the summary is computed.
    """
    y_unit = str(opts["y_unit"])
    if y_unit not in Y_UNIT_FROM_NS:
        raise ValueError(f"y_unit must be one of {sorted(Y_UNIT_FROM_NS)}")
    yfac = Y_UNIT_FROM_NS[y_unit]
    drop_warmup = int(opts["drop_warmup"] or 0)

    def kept(run: RunSeries) -> np.ndarray:
        return run.latency_ns[drop_warmup:] if drop_warmup < run.steps else run.latency_ns

    all_lat_ms = np.concatenate([kept(s)[~np.isnan(kept(s))] for s in all_series] or [np.array([])]) / 1e6
    if all_lat_ms.size:
        p50, p99, ymax = (float(v) for v in (np.percentile(all_lat_ms, 50), np.percentile(all_lat_ms, 99),
                                             all_lat_ms.max()))
    else:
        p50 = p99 = ymax = 0.0
    total_steps = sum(s.steps for s in all_series)
    span_steps = max((kept(s).size for s in all_series), default=0)
    timed_out = any(s.status in (_STATUS_ATO, _STATUS_MTO) for s in all_series)

    out_path: Optional[str] = None
    if out is not None:
        colors = dict(_SERIES_COLORS, **(opts["colors"] or {}))
        labels = opts["labels"] or {}
        window = max(1, int(opts["window"] or 1))
        fig, ax = plt.subplots(figsize=tuple(opts["figsize"]))
        seen: set = set()
        for run in all_series:
            lat = kept(run)
            x = np.arange(lat.size, dtype=np.float64)
            y = lat * yfac
            mask = ~np.isnan(y)
            x, y = x[mask], y[mask]
            if y.size == 0:
                continue
            xs, ys = _downsample(x, y, int(opts["max_points"] or 0))
            if window > 1:
                ys = pd.Series(ys).rolling(window=window, center=True, min_periods=1).mean().to_numpy()
            color = colors.get(run.name, "tab:gray")
            label = labels.get(run.name, run.name) if run.name not in seen else None
            seen.add(run.name)
            ax.plot(xs, ys, linewidth=float(opts["linewidth"]), color=color, label=label,
                    alpha=float(opts["alpha"]))
            if opts["mark_timeouts"] and run.status in (_STATUS_ATO, _STATUS_MTO):
                ax.plot(xs[-1], ys[-1], marker="x", markersize=10, markeredgewidth=2, color=color,
                        linestyle="none", label="timeout" if "timeout" not in seen else None)
                seen.add("timeout")

        if opts["y_log"]:
            ax.set_yscale("log")
        if opts["y_tick_format"] == "plain":
            from matplotlib.ticker import FuncFormatter, NullFormatter
            ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
            ax.yaxis.set_minor_formatter(NullFormatter())
        elif opts["y_tick_format"] != "auto":
            raise ValueError(f"y_tick_format must be 'auto' or 'plain', got {opts['y_tick_format']!r}")
        if opts["threshold_ms"] is not None:
            thr = float(opts["threshold_ms"])
            ax.axhline(thr * 1e6 * yfac, color="black", ls="--", lw=1, label=f"threshold {thr:g} ms")
        if opts["xlim"]:
            ax.set_xlim(*opts["xlim"])
        else:
            ax.set_xlim(left=0)
        if opts["ylim"]:
            ax.set_ylim(*opts["ylim"])
        fontsize = opts["fontsize"]
        ax.set_xlabel(str(opts["xlabel"]), fontsize=fontsize)
        ax.set_ylabel(opts["ylabel"] if opts["ylabel"] is not None else f"Per-step latency ({y_unit})",
                      fontsize=fontsize)
        if opts["title"]:
            ax.set_title(str(opts["title"]), fontsize=opts["title_fontsize"])
        if opts["tick_fontsize"]:
            ax.tick_params(labelsize=opts["tick_fontsize"])
        if opts["grid"]:
            ax.grid(True, which="both", alpha=0.3)
        handles, names = ax.get_legend_handles_labels()
        if opts["legend"] and handles:
            # tools first, then the timeout marker and the threshold line
            order = sorted(range(len(names)), key=lambda i: names[i] == "timeout" or names[i].startswith("threshold"))
            ax.legend([handles[i] for i in order], [names[i] for i in order],
                      loc=str(opts["legend_loc"]), fontsize=opts["legend_fontsize"])
        fig.tight_layout()
        out_path = os.fspath(out)
        _save_fig(fig, out_path)

    return LatencyReplaySummary(
        out_path=out_path,
        steps=total_steps,
        span_s=float(span_steps),
        p50_ms=p50,
        p99_ms=p99,
        max_ms=ymax,
        x_source="step",
        timed_out=timed_out,
        timeout_message=None,
        footers={},
    )


# =========================================================================== #
# Plot — suite results folder (one figure per formula)
# =========================================================================== #

def plot_suite(
    suite_dir: Union[str, "os.PathLike[str]"],
    out_dir: Optional[Union[str, "os.PathLike[str]"]] = None,
    *,
    figure_config=None,
    fmt: str = "svg",
    render: bool = True,
    **common,
) -> Dict[str, LatencyReplaySummary]:
    """One latency figure per formula of a suite run, every tool on the same axes.

    Parameters
    ----------
    suite_dir:
        Results folder of the suite run (or one experiment folder).
    out_dir:
        Where the figures go; default ``<suite_dir>/latency_plots``.
    figure_config:
        Dict, JSON string, or JSON/YAML file: ``{"default": {...}, "<formula>": {...}}``
        with options from :data:`FIGURE_DEFAULTS`.  Figures are keyed by the
        formula name from the provenance; the setting block ("0", "1", ...)
        works as a key too.
    fmt:
        Image format for figures whose config sets no ``out``.
    common:
        Options from :data:`FIGURE_DEFAULTS` applied below ``figure_config``.

    Returns ``formula name -> summary`` in setting order.
    """
    config = load_figure_config(figure_config)
    grouped = load_suite(suite_dir)
    out_root = os.fspath(out_dir) if out_dir else os.path.join(os.fspath(suite_dir), "latency_plots")

    summaries: Dict[str, LatencyReplaySummary] = {}
    for formula, runs in grouped.items():
        blocks = sorted({_setting_block(r.setting) for r in runs})
        opts = _figure_options(config, *blocks, formula, overrides=common)
        out = None
        if render:
            name = opts["out"] or f"{formula}.{fmt}"
            out = name if os.path.isabs(str(name)) else os.path.join(out_root, str(name))
        summaries[formula] = _render_series(runs, out, opts)
    return summaries


# =========================================================================== #
# Plot — result CSVs (merged valid + timeout)
# =========================================================================== #

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
    src.add_argument("--suite", metavar="DIR",
                     help="results folder of a suite run: runs of all experiments are "
                          "grouped by formula and one figure is written per formula")

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
    ap.add_argument("--out-dir", default=None,
                    help="(suite only) folder for the figures (default: <suite>/latency_plots)")
    ap.add_argument("--format", default="svg",
                    help="(suite only) image format of figures without an 'out' in the config")
    ap.add_argument("--figure-config", metavar="JSON|FILE", default=None,
                    help="(suite only) per-figure options: inline JSON object or JSON/YAML file, "
                         "keyed by formula name or 'default'; see FIGURE_DEFAULTS")
    args = ap.parse_args(argv)

    try:
        if args.suite:
            summaries = plot_suite(
                args.suite, args.out_dir, figure_config=args.figure_config, fmt=args.format,
                y_unit=args.y_unit, y_log=args.y_log or None, threshold_ms=args.threshold_ms,
                drop_warmup=args.drop_warmup, max_points=args.max_points,
            )
            for formula, summary in summaries.items():
                print(f"{formula:<24} steps {summary.steps:>8}  p50 {summary.p50_ms:9.3f} ms  "
                      f"p99 {summary.p99_ms:9.3f} ms  max {summary.max_ms:9.3f} ms"
                      f"{'  TIMEOUT' if summary.timed_out else ''}  -> {summary.out_path}")
            return 0
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
        for key, val in summary.footers.items():
            print(f"  {key}: {val}")
    if summary.timed_out:
        print(f"TIMEOUT        : {summary.timeout_message or 'yes'}")
    if summary.out_path:
        print(f"wrote          : {summary.out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
