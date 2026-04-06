from abc import ABC, abstractmethod
from typing import Dict, Any

import pandas as pd

from Infrastructure.Analysis.Aggregators.AbstractAggregator import AbstractAggregator
from Infrastructure.Analysis.Aggregators.ResultAggregatorOffline import ResultAggregatorOffline
from Infrastructure.Analysis.Aggregators.ResultAggregatorOnline import ResultAggregatorOnline


class AbstractAnalysis(ABC):
    @abstractmethod
    def run(self, aggregator: AbstractAggregator) -> Dict[str, pd.DataFrame]:
        pass


class AnalysisOffline(AbstractAnalysis):
    def run(self, aggregator: ResultAggregatorOffline) -> Dict[str, pd.DataFrame]:
        valid = aggregator.get_valid()
        timeout = aggregator.get_timeout()
        tool_error = aggregator.get_tool_error()
        result_error = aggregator.get_result_error()
        missing = aggregator.get_missing()

        all_frames = [valid, timeout, tool_error, result_error, missing]
        total_runs = sum(len(df) for df in all_frames)

        status_overview = pd.DataFrame([
            {"metric": "total", "value": total_runs},
            {"metric": "ok", "value": len(valid)},
            {"metric": "timeout", "value": len(timeout)},
            {"metric": "tool_error", "value": len(tool_error)},
            {"metric": "result_error", "value": len(result_error)},
            {"metric": "missing", "value": len(missing)},
            {"metric": "ok_rate", "value": (len(valid) / total_runs) if total_runs > 0 else 0.0},
        ])

        per_tool = []
        names = set()
        for df in all_frames:
            if "Name" in df.columns:
                names.update(df["Name"].dropna().unique().tolist())

        for name in sorted(names):
            ok = len(valid[valid["Name"] == name])
            to = len(timeout[timeout["Name"] == name])
            te = len(tool_error[tool_error["Name"] == name])
            re = len(result_error[result_error["Name"] == name])
            mi = len(missing[missing["Name"] == name])
            total = ok + to + te + re + mi
            per_tool.append({
                "Name": name,
                "total": total,
                "ok": ok,
                "timeout": to,
                "tool_error": te,
                "result_error": re,
                "missing": mi,
                "ok_rate": (ok / total) if total > 0 else 0.0,
            })

        per_tool_df = pd.DataFrame(per_tool)

        time_summary = pd.DataFrame(columns=["metric", "value"])
        if not valid.empty:
            for col in ["pre", "compilation", "runtime", "post", "wall_time", "max_mem", "cpu"]:
                if col in valid.columns:
                    series = pd.to_numeric(valid[col], errors="coerce")
                    if series.notna().any():
                        time_summary.loc[len(time_summary)] = {"metric": f"{col}_mean", "value": float(series.mean())}
                        time_summary.loc[len(time_summary)] = {"metric": f"{col}_median", "value": float(series.median())}
                        time_summary.loc[len(time_summary)] = {"metric": f"{col}_max", "value": float(series.max())}

        return {
            "status_overview": status_overview,
            "per_tool_status": per_tool_df,
            "valid_runtime_summary": time_summary,
        }


class AnalysisOnline(AbstractAnalysis):
    def run(self, aggregator: ResultAggregatorOnline) -> Dict[str, pd.DataFrame]:
        valid = aggregator.get_valid()
        to_acc = aggregator.get_timeout_accumulative_latency()
        to_max = aggregator.get_timeout_maximum_latency()
        tool_error = aggregator.get_tool_error()
        result_error = aggregator.get_result_error()
        missing = aggregator.get_missing()

        all_frames = [valid, to_acc, to_max, tool_error, result_error, missing]
        total_runs = sum(len(df) for df in all_frames)

        status_overview = pd.DataFrame([
            {"metric": "total", "value": total_runs},
            {"metric": "ok", "value": len(valid)},
            {"metric": "timeout_accumulative_latency", "value": len(to_acc)},
            {"metric": "timeout_maximum_latency", "value": len(to_max)},
            {"metric": "tool_error", "value": len(tool_error)},
            {"metric": "result_error", "value": len(result_error)},
            {"metric": "missing", "value": len(missing)},
            {"metric": "ok_rate", "value": (len(valid) / total_runs) if total_runs > 0 else 0.0},
        ])

        per_tool = []
        names = set()
        for df in all_frames:
            if "Name" in df.columns:
                names.update(df["Name"].dropna().unique().tolist())

        for name in sorted(names):
            ok = len(valid[valid["Name"] == name])
            ato = len(to_acc[to_acc["Name"] == name])
            mto = len(to_max[to_max["Name"] == name])
            te = len(tool_error[tool_error["Name"] == name])
            re = len(result_error[result_error["Name"] == name])
            mi = len(missing[missing["Name"] == name])
            total = ok + ato + mto + te + re + mi

            # Progress ratio quantifies partial processing in timeout scenarios.
            timeout_events = pd.concat([
                to_acc[to_acc["Name"] == name]["total_count"] if "total_count" in to_acc.columns else pd.Series(dtype=float),
                to_max[to_max["Name"] == name]["total_count"] if "total_count" in to_max.columns else pd.Series(dtype=float),
            ], ignore_index=True)
            ok_events = valid[valid["Name"] == name]["total_count"] if "total_count" in valid.columns else pd.Series(dtype=float)

            timeout_mean = pd.to_numeric(timeout_events, errors="coerce").mean() if not timeout_events.empty else None
            ok_mean = pd.to_numeric(ok_events, errors="coerce").mean() if not ok_events.empty else None
            progress_ratio = (float(timeout_mean) / float(ok_mean)) if (ok_mean not in [None, 0] and pd.notna(ok_mean) and pd.notna(timeout_mean)) else None

            per_tool.append({
                "Name": name,
                "total": total,
                "ok": ok,
                "timeout_accumulative_latency": ato,
                "timeout_maximum_latency": mto,
                "tool_error": te,
                "result_error": re,
                "missing": mi,
                "ok_rate": (ok / total) if total > 0 else 0.0,
                "timeout_events_mean": timeout_mean,
                "ok_events_mean": ok_mean,
                "timeout_progress_ratio": progress_ratio,
            })

        per_tool_df = pd.DataFrame(per_tool)

        runtime_summary = pd.DataFrame(columns=["metric", "value"])
        merged_for_time = pd.concat([valid, to_acc, to_max], ignore_index=True)
        if not merged_for_time.empty:
            for col in ["pre", "build", "total_elapsed", "total_count"]:
                if col in merged_for_time.columns:
                    series = pd.to_numeric(merged_for_time[col], errors="coerce")
                    if series.notna().any():
                        runtime_summary.loc[len(runtime_summary)] = {"metric": f"{col}_mean", "value": float(series.mean())}
                        runtime_summary.loc[len(runtime_summary)] = {"metric": f"{col}_median", "value": float(series.median())}
                        runtime_summary.loc[len(runtime_summary)] = {"metric": f"{col}_max", "value": float(series.max())}

        return {
            "status_overview": status_overview,
            "per_tool_status": per_tool_df,
            "online_runtime_progress_summary": runtime_summary,
        }


def dispatch_analysis(aggregator: AbstractAggregator) -> AbstractAnalysis:
    if isinstance(aggregator, ResultAggregatorOnline):
        return AnalysisOnline()
    if isinstance(aggregator, ResultAggregatorOffline):
        return AnalysisOffline()
    raise TypeError(f"Unsupported aggregator type for analysis: {type(aggregator)}")


def run_analysis(aggregator: AbstractAggregator) -> Dict[str, pd.DataFrame]:
    return dispatch_analysis(aggregator).run(aggregator)

