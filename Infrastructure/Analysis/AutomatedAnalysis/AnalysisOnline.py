import re
from typing import Dict, List

import pandas as pd

from Infrastructure.Analysis.Aggregators.ResultAggregatorOnline import ResultAggregatorOnline
from Infrastructure.Analysis.AutomatedAnalysis.BaseAnalysis import AbstractAnalysis


class AnalysisOnline(AbstractAnalysis):
    @staticmethod
    def _extract_numeric_tokens(value) -> List[float]:
        if pd.isna(value):
            return []
        tokens = re.findall(r"-?\d+(?:\.\d+)?", str(value))
        out = []
        for t in tokens:
            try:
                out.append(float(t))
            except ValueError:
                pass
        return out

    @staticmethod
    def _extract_latency_values_from_setting(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
        out = df.copy()
        if "Setting" not in out.columns:
            return out

        vectors = out["Setting"].apply(AnalysisOnline._extract_numeric_tokens)
        max_len = int(vectors.map(len).max()) if not vectors.empty else 0

        for idx in range(max_len):
            col = f"{prefix}_latency_{idx}"
            out[col] = vectors.apply(lambda vals: vals[idx] if idx < len(vals) else pd.NA)

        return out

    @staticmethod
    def _build_tool_overview(valid, to_acc, to_max, tool_error, result_error, missing) -> pd.DataFrame:
        frames = [valid, to_acc, to_max, tool_error, result_error, missing]
        names = set()
        for df in frames:
            if "Name" in df.columns:
                names.update(df["Name"].dropna().unique().tolist())

        rows = []
        for name in sorted(names):
            ok = int((valid["Name"] == name).sum()) if "Name" in valid.columns else 0
            ato = int((to_acc["Name"] == name).sum()) if "Name" in to_acc.columns else 0
            mto = int((to_max["Name"] == name).sum()) if "Name" in to_max.columns else 0
            te = int((tool_error["Name"] == name).sum()) if "Name" in tool_error.columns else 0
            re = int((result_error["Name"] == name).sum()) if "Name" in result_error.columns else 0
            mi = int((missing["Name"] == name).sum()) if "Name" in missing.columns else 0
            total = ok + ato + mto + te + re + mi
            rows.append({
                "Name": name,
                "total_runs": total,
                "succeeded": ok,
                "timeout_accumulative_latency": ato,
                "timeout_maximum_latency": mto,
                "tool_error": te,
                "result_error": re,
                "missing": mi,
                "success_rate": (ok / total) if total else 0.0,
            })
        return pd.DataFrame(rows)

    @staticmethod
    def _build_successful_runs_table(valid: pd.DataFrame) -> pd.DataFrame:
        if valid.empty:
            return pd.DataFrame(columns=["Name", "Setting", "pre", "build", "total_elapsed", "total_count"])

        out = valid[["Name", "Setting", "pre", "build", "total_elapsed", "total_count"]].copy()
        out = AnalysisOnline._safe_numeric(out, ["pre", "build", "total_elapsed", "total_count"])
        return out.sort_values(["Name", "Setting"])

    @staticmethod
    def _build_timeout_table(timeout_df: pd.DataFrame, prefix: str) -> pd.DataFrame:
        if timeout_df.empty:
            return pd.DataFrame(columns=["Name", "Setting", "pre", "build", "total_elapsed", "total_count"])

        out = timeout_df[["Name", "Setting", "pre", "build", "total_elapsed", "total_count"]].copy()
        out = AnalysisOnline._safe_numeric(out, ["pre", "build", "total_elapsed", "total_count"])
        out = AnalysisOnline._extract_latency_values_from_setting(out, prefix)
        return out.sort_values(["Name", "Setting"])

    @staticmethod
    def save_report(output_folder: str, report_name: str, analysis_results: Dict[str, pd.DataFrame]) -> str:
        import os
        os.makedirs(output_folder, exist_ok=True)
        for name, df in analysis_results.items():
            df.to_csv(os.path.join(output_folder, f"{name}.csv"), index=False)
        return output_folder

    def run(self, aggregator: ResultAggregatorOnline) -> Dict[str, pd.DataFrame]:
        valid = aggregator.get_valid()
        to_acc = aggregator.get_timeout_accumulative_latency()
        to_max = aggregator.get_timeout_maximum_latency()
        tool_error = aggregator.get_tool_error()
        result_error = aggregator.get_result_error()
        missing = aggregator.get_missing()

        tool_overview = self._build_tool_overview(valid, to_acc, to_max, tool_error, result_error, missing)
        successful_runs = self._build_successful_runs_table(valid)
        timeout_accumulative_latency_details = self._build_timeout_table(to_acc, "acc")
        timeout_maximum_latency_details = self._build_timeout_table(to_max, "max")

        return {
            "tool_overview": tool_overview,
            "successful_runs": successful_runs,
            "timeout_accumulative_latency_details": timeout_accumulative_latency_details,
            "timeout_maximum_latency_details": timeout_maximum_latency_details,
        }
