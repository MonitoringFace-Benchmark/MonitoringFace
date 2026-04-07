import os
from typing import Dict, Tuple

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import pandas as pd

from Infrastructure.Analysis.Aggregators.ResultAggregatorOffline import ResultAggregatorOffline
from Infrastructure.Analysis.AutomatedAnalysis.BaseAnalysis import AbstractAnalysis


class AnalysisOffline(AbstractAnalysis):

    @staticmethod
    def _render_table_page(pdf: PdfPages, title: str, df: pd.DataFrame, max_rows: int = 30) -> None:
        fig, ax = plt.subplots(figsize=(11.69, 8.27))
        ax.axis("off")
        ax.set_title(title, fontsize=14, fontweight="bold", pad=12)

        if df.empty:
            ax.text(0.5, 0.5, "No data available", ha="center", va="center", fontsize=12)
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)
            return

        shown = df.head(max_rows).copy()
        for col in shown.columns:
            if pd.api.types.is_float_dtype(shown[col]):
                shown[col] = shown[col].map(lambda x: f"{x:.4f}" if pd.notna(x) else "")

        table = ax.table(
            cellText=shown.values,
            colLabels=shown.columns,
            loc="center",
            cellLoc="center",
        )
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.2)

        if len(df) > max_rows:
            ax.text(
                0.01,
                0.01,
                f"Showing first {max_rows} of {len(df)} rows",
                transform=ax.transAxes,
                fontsize=8,
                ha="left",
                va="bottom",
            )

        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

    @staticmethod
    def _plot_line_by_prefix(
            pdf: PdfPages,
            df: pd.DataFrame,
            value_col: str,
            title: str,
            ylabel: str,
    ) -> None:
        fig, ax = plt.subplots(figsize=(11.69, 8.27))
        ax.set_title(title, fontsize=14, fontweight="bold")
        ax.set_xlabel("dataset_size")
        ax.set_ylabel(ylabel)

        if df.empty or value_col not in df.columns:
            ax.text(0.5, 0.5, "No data available", ha="center", va="center", fontsize=12)
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)
            return

        work = df.dropna(subset=["setting_prefix", "dataset_size", value_col]).copy()
        if work.empty:
            ax.text(0.5, 0.5, "No plottable data", ha="center", va="center", fontsize=12)
            pdf.savefig(fig, bbox_inches="tight")
            plt.close(fig)
            return

        for (prefix, tool), grp in work.groupby(["setting_prefix", "Name"]):
            grp = grp.sort_values("dataset_size")
            label = f"{tool} | {prefix}"
            ax.plot(grp["dataset_size"], grp[value_col], marker="o", linewidth=1.5, label=label)

        ax.grid(True, alpha=0.3)
        ax.legend(loc="best", fontsize=7, ncol=2)
        pdf.savefig(fig, bbox_inches="tight")
        plt.close(fig)

    def save_report(self, output_folder: str, report_name: str, analysis_results: Dict[str, pd.DataFrame]) -> str:
        os.makedirs(output_folder, exist_ok=True)

        for name, df in analysis_results.items():
            df.to_csv(os.path.join(output_folder, f"{name}.csv"), index=False)

        pdf_path = os.path.join(output_folder, f"{report_name}.pdf")
        with PdfPages(pdf_path) as pdf:
            tool_overview = analysis_results.get("tool_overview", pd.DataFrame())
            scalability_mean = analysis_results.get("scalability_mean", pd.DataFrame())
            memory_ranking = analysis_results.get("memory_ranking", pd.DataFrame())
            stage_breakdown = analysis_results.get("stage_breakdown", pd.DataFrame())
            setting_tool_comparison = analysis_results.get("setting_tool_comparison", pd.DataFrame())

            self._render_table_page(pdf, "Offline Report - Tool Overview", tool_overview)
            self._render_table_page(pdf, "Setting/Tool Comparison", setting_tool_comparison)

            self._plot_line_by_prefix(
                pdf,
                scalability_mean,
                value_col="runtime_mean",
                title="Scalability - Runtime Mean by Dataset Size",
                ylabel="runtime_mean",
            )
            self._plot_line_by_prefix(
                pdf,
                scalability_mean,
                value_col="wall_time_mean",
                title="Scalability - Wall Time Mean by Dataset Size",
                ylabel="wall_time_mean",
            )

            self._render_table_page(pdf, "Memory Ranking (Lowest to Highest max_mem)", memory_ranking, max_rows=40)
            self._render_table_page(pdf, "Stage Breakdown (pre/compilation/runtime/post/total)", stage_breakdown, max_rows=40)
        return pdf_path

    @staticmethod
    def _with_setting_parts(df: pd.DataFrame) -> pd.DataFrame:
        out = df.copy()
        if "Setting" not in out.columns:
            out["setting_prefix"] = None
            out["dataset_size"] = pd.NA
            return out

        setting_str = out["Setting"].astype(str)
        split_parts = setting_str.str.rsplit("_", n=1)
        out["setting_prefix"] = split_parts.str[0]
        dataset_raw = split_parts.str[1]
        out["dataset_size"] = pd.to_numeric(dataset_raw, errors="coerce").astype("Int64")
        return out

    @staticmethod
    def _safe_numeric(df: pd.DataFrame, cols) -> pd.DataFrame:
        out = df.copy()
        for col in cols:
            if col in out.columns:
                out[col] = pd.to_numeric(out[col], errors="coerce")
        return out

    @staticmethod
    def _build_tool_overview(
        valid: pd.DataFrame,
        timeout: pd.DataFrame,
        tool_error: pd.DataFrame,
        result_error: pd.DataFrame,
        missing: pd.DataFrame,
    ) -> pd.DataFrame:
        frames = [valid, timeout, tool_error, result_error, missing]
        names = set()
        for df in frames:
            if "Name" in df.columns:
                names.update(df["Name"].dropna().unique().tolist())

        rows = []
        for name in sorted(names):
            ok = int((valid["Name"] == name).sum()) if "Name" in valid.columns else 0
            to = int((timeout["Name"] == name).sum()) if "Name" in timeout.columns else 0
            te = int((tool_error["Name"] == name).sum()) if "Name" in tool_error.columns else 0
            re = int((result_error["Name"] == name).sum()) if "Name" in result_error.columns else 0
            mi = int((missing["Name"] == name).sum()) if "Name" in missing.columns else 0
            total = ok + to + te + re + mi

            rows.append(
                {
                    "Name": name,
                    "total_runs": total,
                    "succeeded": ok,
                    "not_validated": re,
                    "errored": te,
                    "timed_out": to,
                    "missing": mi,
                    "success_rate": (ok / total) if total else 0.0,
                }
            )
        return pd.DataFrame(rows)

    @staticmethod
    def _build_scalability_tables(valid: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        if valid.empty:
            empty_cols_points = ["Name", "Setting", "setting_prefix", "dataset_size", "runtime", "wall_time"]
            empty_cols_mean = ["Name", "setting_prefix", "dataset_size", "runtime_mean", "wall_time_mean", "n_runs"]
            return (
                pd.DataFrame(columns=empty_cols_points),
                pd.DataFrame(columns=empty_cols_mean),
                pd.DataFrame(columns=["Name", "setting_prefix", "dataset_size", "runtime"]),
                pd.DataFrame(columns=["Name", "setting_prefix", "dataset_size", "wall_time"]),
            )

        points = valid[["Name", "Setting", "setting_prefix", "dataset_size", "runtime", "wall_time"]].copy()
        points = AnalysisOffline._safe_numeric(points, ["runtime", "wall_time"])

        mean = (
            points.dropna(subset=["setting_prefix", "dataset_size"])
            .groupby(["Name", "setting_prefix", "dataset_size"], as_index=False)
            .agg(
                runtime_mean=("runtime", "mean"),
                wall_time_mean=("wall_time", "mean"),
                n_runs=("runtime", "count"),
            )
            .sort_values(["setting_prefix", "dataset_size", "Name"])
        )

        runtime_points = points[["Name", "setting_prefix", "dataset_size", "runtime"]].copy()
        wall_time_points = points[["Name", "setting_prefix", "dataset_size", "wall_time"]].copy()
        return points, mean, runtime_points, wall_time_points

    @staticmethod
    def _build_setting_tool_comparison(valid: pd.DataFrame) -> pd.DataFrame:
        if valid.empty:
            return pd.DataFrame(
                columns=[
                    "Setting",
                    "setting_prefix",
                    "dataset_size",
                    "Name",
                    "runtime_avg",
                    "wall_time_avg",
                    "max_mem_avg",
                    "cpu_avg",
                    "n_runs",
                ]
            )

        work = valid.copy()
        work = AnalysisOffline._safe_numeric(work, ["runtime", "wall_time", "max_mem", "cpu"])

        comp = (
            work.groupby(["Setting", "setting_prefix", "dataset_size", "Name"], as_index=False)
            .agg(
                runtime_avg=("runtime", "mean"),
                wall_time_avg=("wall_time", "mean"),
                max_mem_avg=("max_mem", "mean"),
                cpu_avg=("cpu", "mean"),
                n_runs=("runtime", "count"),
            )
            .sort_values(["setting_prefix", "dataset_size", "Setting", "Name"])
        )
        return comp

    @staticmethod
    def _build_memory_ranking(valid: pd.DataFrame) -> pd.DataFrame:
        if valid.empty:
            return pd.DataFrame(columns=["Name", "Setting", "setting_prefix", "dataset_size", "max_mem"])

        mem = valid[["Name", "Setting", "setting_prefix", "dataset_size", "max_mem"]].copy()
        mem["max_mem"] = pd.to_numeric(mem["max_mem"], errors="coerce")
        mem = mem.dropna(subset=["max_mem"]).sort_values(["max_mem", "Name", "Setting"], ascending=[True, True, True])
        return mem

    @staticmethod
    def _build_stage_breakdown(valid: pd.DataFrame) -> pd.DataFrame:
        cols = ["Name", "Setting", "setting_prefix", "dataset_size", "pre", "compilation", "runtime", "post", "wall_time"]
        if valid.empty:
            return pd.DataFrame(columns=cols + ["total_time", "max_total_time", "max_runtime", "max_wall_time"])

        stage = valid[cols].copy()
        stage = AnalysisOffline._safe_numeric(stage, ["pre", "compilation", "runtime", "post", "wall_time"])
        stage["total_time"] = stage[["pre", "compilation", "runtime", "post"]].sum(axis=1, min_count=1)

        max_total = stage["total_time"].max(skipna=True)
        max_runtime = stage["runtime"].max(skipna=True)
        max_wall = stage["wall_time"].max(skipna=True)

        stage["max_total_time"] = stage["total_time"] == max_total if pd.notna(max_total) else False
        stage["max_runtime"] = stage["runtime"] == max_runtime if pd.notna(max_runtime) else False
        stage["max_wall_time"] = stage["wall_time"] == max_wall if pd.notna(max_wall) else False

        return stage.sort_values(["setting_prefix", "dataset_size", "Name", "Setting"])

    def run(self, aggregator: ResultAggregatorOffline) -> Dict[str, pd.DataFrame]:
        valid = self._with_setting_parts(aggregator.get_valid())
        timeout = aggregator.get_timeout()
        tool_error = aggregator.get_tool_error()
        result_error = aggregator.get_result_error()
        missing = aggregator.get_missing()

        tool_overview = self._build_tool_overview(valid, timeout, tool_error, result_error, missing)
        scalability_points, scalability_mean, runtime_points, wall_time_points = self._build_scalability_tables(valid)
        setting_tool_comparison = self._build_setting_tool_comparison(valid)
        memory_ranking = self._build_memory_ranking(valid)
        stage_breakdown = self._build_stage_breakdown(valid)

        return {
            "tool_overview": tool_overview,
            "setting_tool_comparison": setting_tool_comparison,
            "scalability_points": scalability_points,
            "scalability_mean": scalability_mean,
            "runtime_points": runtime_points,
            "wall_time_points": wall_time_points,
            "memory_ranking": memory_ranking,
            "stage_breakdown": stage_breakdown,
        }
