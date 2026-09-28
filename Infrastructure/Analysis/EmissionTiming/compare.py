"""Correctness gate and per-verdict lead across tools of one setting.

Timing is only meaningful on correct output, so every tool is first checked
against the reference tool verdict by verdict (time-point and valuation).
The lead of a tool on a verdict is the baseline's emission time minus the
tool's, in log seconds; verdicts either side emitted only in its
end-of-input tail have no emission time and are counted separately.
"""
import statistics
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from Infrastructure.Analysis.EmissionTiming.extract import Emission, PointId, ToolRun

Key = Tuple[PointId, Tuple[str, ...]]


@dataclass
class ToolReport:
    tool: str
    verdicts: int
    duplicates: int
    unmapped: int
    extra: int
    missing: int
    unordered_match: bool
    shared_with_baseline: int = 0
    tail_only: int = 0
    later_than_baseline: int = 0
    lead: Dict[str, Optional[float]] = field(default_factory=dict)


@dataclass
class SettingReport:
    setting: str
    reference: str
    baseline: str
    points_agree: bool
    tools: List[ToolReport]
    rows: List[dict]


def _first_emissions(run: ToolRun, unordered: bool) -> Tuple[Dict[Key, Emission], int]:
    first: Dict[Key, Emission] = {}
    counts: Counter = Counter()
    for e in run.emissions:
        key = (e.point, tuple(sorted(e.valuation)) if unordered else e.valuation)
        counts[key] += 1
        if key not in first or e.round < first[key].round:
            first[key] = e
    return first, sum(c - 1 for c in counts.values())


def _distribution(values: List[float]) -> Dict[str, Optional[float]]:
    if not values:
        return {k: None for k in ("min", "median", "mean", "p90", "p99", "max")}
    ordered = sorted(values)
    pick = lambda q: ordered[int(q * (len(ordered) - 1))]
    return {"min": ordered[0], "median": statistics.median(ordered), "mean": round(statistics.mean(ordered), 3),
            "p90": pick(0.9), "p99": pick(0.99), "max": ordered[-1]}


def compare_setting(runs: List[ToolRun], reference: str, baseline: str) -> SettingReport:
    by_tool = {r.tool: r for r in runs}
    for name in (reference, baseline):
        if name not in by_tool:
            raise ValueError(f"setting {runs[0].setting}: no frames for tool {name!r} "
                             f"(have {sorted(by_tool)})")
    timestamps = {r.tool: r.point_timestamps for r in runs}
    points_agree = len({tuple(t) for t in timestamps.values()}) == 1

    ordered = {r.tool: _first_emissions(r, unordered=False) for r in runs}
    unordered = {r.tool: _first_emissions(r, unordered=True) for r in runs}
    ref_keys = set(ordered[reference][0])
    ref_keys_unordered = set(unordered[reference][0])

    reports, rows = [], []
    for run in runs:
        keys = set(ordered[run.tool][0])
        use_unordered = keys != ref_keys and set(unordered[run.tool][0]) == ref_keys_unordered
        table = unordered if use_unordered else ordered
        mine, duplicates = table[run.tool]
        base, _ = table[baseline]
        ref = set(table[reference][0])
        report = ToolReport(run.tool, len(mine), duplicates, run.unmapped,
                            len(set(mine) - ref), len(ref - set(mine)), use_unordered)
        leads = []
        for key in sorted(set(mine) & set(base)):
            report.shared_with_baseline += 1
            mine_t, base_t = mine[key].log_time, base[key].log_time
            if mine_t is None or base_t is None:
                report.tail_only += 1
                lead = None
            else:
                lead = base_t - mine_t
                leads.append(lead)
                report.later_than_baseline += lead < 0
            rows.append({"tool": run.tool, "point_ts": key[0][0], "point_rank": key[0][1],
                         "valuation": "|".join(key[1]), "round": mine[key].round,
                         "log_time": mine_t, "baseline_log_time": base_t, "lead_s": lead})
        report.lead = _distribution(leads)
        reports.append(report)
    return SettingReport(runs[0].setting, reference, baseline, points_agree, reports, rows)


def compare(runs: List[ToolRun], reference: str, baseline: str) -> List[SettingReport]:
    settings: Dict[str, List[ToolRun]] = {}
    for run in runs:
        settings.setdefault(run.setting, []).append(run)
    return [compare_setting(group, reference, baseline) for _, group in sorted(settings.items())]
