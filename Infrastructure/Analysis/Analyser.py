"""
Analyser module for performance analysis of benchmark results.

Provides metrics computation and visualization for monitoring tool benchmarks.
"""

import os
from pathlib import Path
from typing import Optional, List, Dict, Tuple

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


class Analyser:
    """
    Analyser class for processing and visualizing benchmark results.

    Loads results from a result folder (valid, timeout, tool_error, result_error CSVs)
    and provides performance metrics and visualizations.
    """

    def __init__(self, result_folder: str):
        """
        Initialize the Analyser with a result folder path.

        Args:
            result_folder: Path to the folder containing result CSV files.
        """
        self.result_folder = Path(result_folder)
        self.name = self.result_folder.name

        # Load all available result dataframes
        self.valid: Optional[pd.DataFrame] = None
        self.timeout: Optional[pd.DataFrame] = None
        self.tool_error: Optional[pd.DataFrame] = None
        self.result_error: Optional[pd.DataFrame] = None
        self.missing: Optional[pd.DataFrame] = None

        self._load_results()

    def _load_results(self) -> None:
        """Load all CSV files from the result folder."""
        for file in self.result_folder.iterdir():
            if not file.suffix == '.csv':
                continue

            name = file.stem
            if name.endswith('_valid'):
                self.valid = pd.read_csv(file)
            elif name.endswith('_timeout'):
                self.timeout = pd.read_csv(file)
            elif name.endswith('_tool_error'):
                self.tool_error = pd.read_csv(file)
            elif name.endswith('_result_error'):
                self.result_error = pd.read_csv(file)
            elif name.endswith('_missing'):
                self.missing = pd.read_csv(file)

    # ==================== Summary Statistics ====================

    def summary(self) -> Dict[str, int]:
        """
        Get a summary of result counts by status.

        Returns:
            Dictionary with counts for each result type.
        """
        return {
            'valid': len(self.valid) if self.valid is not None else 0,
            'timeout': len(self.timeout) if self.timeout is not None else 0,
            'tool_error': len(self.tool_error) if self.tool_error is not None else 0,
            'result_error': len(self.result_error) if self.result_error is not None else 0,
            'missing': len(self.missing) if self.missing is not None else 0
        }

    def tools(self) -> List[str]:
        """Get list of unique tool names from valid results."""
        if self.valid is None:
            return []
        return self.valid['Name'].unique().tolist()

    def settings(self) -> List[str]:
        """Get list of unique settings from valid results."""
        if self.valid is None:
            return []
        return self.valid['Setting'].unique().tolist()

    # ==================== Performance Metrics ====================

    def mean_runtime_by_tool(self) -> pd.Series:
        """Compute mean runtime for each tool."""
        if self.valid is None or self.valid.empty:
            return pd.Series(dtype=float)
        return self.valid.groupby('Name')['runtime'].mean()

    def median_runtime_by_tool(self) -> pd.Series:
        """Compute median runtime for each tool."""
        if self.valid is None or self.valid.empty:
            return pd.Series(dtype=float)
        return self.valid.groupby('Name')['runtime'].median()

    def std_runtime_by_tool(self) -> pd.Series:
        """Compute standard deviation of runtime for each tool."""
        if self.valid is None or self.valid.empty:
            return pd.Series(dtype=float)
        return self.valid.groupby('Name')['runtime'].std()

    def total_time_by_tool(self) -> pd.Series:
        """Compute total time (pre + runtime + post) for each tool."""
        if self.valid is None or self.valid.empty:
            return pd.Series(dtype=float)
        df = self.valid.copy()
        df['total'] = df['pre'] + df['runtime'] + df['post']
        return df.groupby('Name')['total'].mean()

    def mean_memory_by_tool(self) -> pd.Series:
        """Compute mean max memory usage for each tool."""
        if self.valid is None or self.valid.empty:
            return pd.Series(dtype=float)
        # max_mem is in KB, convert to MB for readability
        return self.valid.groupby('Name')['max_mem'].mean() / 1024

    def percentile_runtime_by_tool(self, percentile: float = 95) -> pd.Series:
        """Compute percentile runtime for each tool."""
        if self.valid is None or self.valid.empty:
            return pd.Series(dtype=float)
        return self.valid.groupby('Name')['runtime'].quantile(percentile / 100)

    def runtime_statistics(self) -> pd.DataFrame:
        """
        Comprehensive runtime statistics for all tools.

        Returns:
            DataFrame with mean, median, std, min, max, p95 for each tool.
        """
        if self.valid is None or self.valid.empty:
            return pd.DataFrame()

        stats = self.valid.groupby('Name')['runtime'].agg([
            'mean', 'median', 'std', 'min', 'max',
            ('p25', lambda x: x.quantile(0.25)),
            ('p75', lambda x: x.quantile(0.75)),
            ('p95', lambda x: x.quantile(0.95)),
            'count'
        ])
        return stats.round(4)

    def memory_statistics(self) -> pd.DataFrame:
        """
        Comprehensive memory statistics for all tools.

        Returns:
            DataFrame with mean, median, std, min, max for each tool (in MB).
        """
        if self.valid is None or self.valid.empty:
            return pd.DataFrame()

        # Convert to MB
        df = self.valid.copy()
        df['max_mem_mb'] = df['max_mem'] / 1024

        stats = df.groupby('Name')['max_mem_mb'].agg([
            'mean', 'median', 'std', 'min', 'max', 'count'
        ])
        return stats.round(2)

    def speedup_matrix(self, baseline: Optional[str] = None) -> pd.DataFrame:
        """
        Compute speedup matrix comparing tools.

        Args:
            baseline: Tool name to use as baseline. If None, uses the slowest tool.

        Returns:
            DataFrame with speedup factors (baseline_time / tool_time).
        """
        if self.valid is None or self.valid.empty:
            return pd.DataFrame()

        mean_times = self.mean_runtime_by_tool()

        if baseline is None:
            baseline = mean_times.idxmax()

        baseline_time = mean_times[baseline]
        speedup = baseline_time / mean_times
        return speedup.to_frame(name=f'speedup_vs_{baseline}')

    def success_rate_by_tool(self) -> pd.DataFrame:
        """
        Compute success rate for each tool across all result types.

        Returns:
            DataFrame with valid, timeout, error counts and success rate.
        """
        # Gather all tool names
        all_tools = set()
        if self.valid is not None:
            all_tools.update(self.valid['Name'].unique())
        if self.timeout is not None:
            all_tools.update(self.timeout['Name'].unique())
        if self.tool_error is not None:
            all_tools.update(self.tool_error['Name'].unique())
        if self.result_error is not None:
            all_tools.update(self.result_error['Name'].unique())

        results = []
        for tool in sorted(all_tools):
            valid_count = len(self.valid[self.valid['Name'] == tool]) if self.valid is not None else 0
            timeout_count = len(self.timeout[self.timeout['Name'] == tool]) if self.timeout is not None else 0
            tool_err_count = len(self.tool_error[self.tool_error['Name'] == tool]) if self.tool_error is not None else 0
            result_err_count = len(self.result_error[self.result_error['Name'] == tool]) if self.result_error is not None else 0

            total = valid_count + timeout_count + tool_err_count + result_err_count
            success_rate = (valid_count / total * 100) if total > 0 else 0

            results.append({
                'Tool': tool,
                'Valid': valid_count,
                'Timeout': timeout_count,
                'ToolError': tool_err_count,
                'ResultError': result_err_count,
                'Total': total,
                'SuccessRate': round(success_rate, 2)
            })

        return pd.DataFrame(results).set_index('Tool')

    # ==================== Visualization ====================

    def plot_runtime_comparison(self, save_path: Optional[str] = None, figsize: Tuple[int, int] = (12, 6)) -> plt.Figure:
        """
        Bar chart comparing mean runtime across tools.

        Args:
            save_path: Optional path to save the figure.
            figsize: Figure size tuple.

        Returns:
            Matplotlib Figure object.
        """
        if self.valid is None or self.valid.empty:
            raise ValueError("No valid results to plot")

        fig, ax = plt.subplots(figsize=figsize)

        means = self.mean_runtime_by_tool()
        stds = self.std_runtime_by_tool()

        x = np.arange(len(means))
        bars = ax.bar(x, means.values, yerr=stds.values, capsize=5, alpha=0.8)

        ax.set_xlabel('Tool')
        ax.set_ylabel('Runtime (seconds)')
        ax.set_title('Mean Runtime Comparison by Tool')
        ax.set_xticks(x)
        ax.set_xticklabels(means.index, rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight')

        return fig

    def plot_runtime_boxplot(self, save_path: Optional[str] = None, figsize: Tuple[int, int] = (12, 6)) -> plt.Figure:
        """
        Box plot of runtime distribution for each tool.

        Args:
            save_path: Optional path to save the figure.
            figsize: Figure size tuple.

        Returns:
            Matplotlib Figure object.
        """
        if self.valid is None or self.valid.empty:
            raise ValueError("No valid results to plot")

        fig, ax = plt.subplots(figsize=figsize)

        tools = self.tools()
        data = [self.valid[self.valid['Name'] == t]['runtime'].values for t in tools]

        bp = ax.boxplot(data, labels=tools, patch_artist=True)

        colors = plt.cm.tab10(np.linspace(0, 1, len(tools)))
        for patch, color in zip(bp['boxes'], colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)

        ax.set_xlabel('Tool')
        ax.set_ylabel('Runtime (seconds)')
        ax.set_title('Runtime Distribution by Tool')
        plt.xticks(rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight')

        return fig

    def plot_memory_comparison(self, save_path: Optional[str] = None, figsize: Tuple[int, int] = (12, 6)) -> plt.Figure:
        """
        Bar chart comparing mean memory usage across tools.

        Args:
            save_path: Optional path to save the figure.
            figsize: Figure size tuple.

        Returns:
            Matplotlib Figure object.
        """
        if self.valid is None or self.valid.empty:
            raise ValueError("No valid results to plot")

        fig, ax = plt.subplots(figsize=figsize)

        means = self.mean_memory_by_tool()

        x = np.arange(len(means))
        bars = ax.bar(x, means.values, alpha=0.8, color='steelblue')

        ax.set_xlabel('Tool')
        ax.set_ylabel('Max Memory (MB)')
        ax.set_title('Mean Memory Usage by Tool')
        ax.set_xticks(x)
        ax.set_xticklabels(means.index, rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight')

        return fig

    def plot_runtime_by_setting(self, save_path: Optional[str] = None, figsize: Tuple[int, int] = (14, 8)) -> plt.Figure:
        """
        Grouped bar chart of runtime by setting and tool.

        Args:
            save_path: Optional path to save the figure.
            figsize: Figure size tuple.

        Returns:
            Matplotlib Figure object.
        """
        if self.valid is None or self.valid.empty:
            raise ValueError("No valid results to plot")

        fig, ax = plt.subplots(figsize=figsize)

        pivot = self.valid.pivot_table(
            values='runtime',
            index='Setting',
            columns='Name',
            aggfunc='mean'
        )

        pivot.plot(kind='bar', ax=ax, width=0.8)

        ax.set_xlabel('Setting')
        ax.set_ylabel('Runtime (seconds)')
        ax.set_title('Runtime by Setting and Tool')
        ax.legend(title='Tool', bbox_to_anchor=(1.05, 1), loc='upper left')
        plt.xticks(rotation=45, ha='right')
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight')

        return fig

    def plot_success_rate(self, save_path: Optional[str] = None, figsize: Tuple[int, int] = (10, 6)) -> plt.Figure:
        """
        Stacked bar chart showing success/failure breakdown by tool.

        Args:
            save_path: Optional path to save the figure.
            figsize: Figure size tuple.

        Returns:
            Matplotlib Figure object.
        """
        success_df = self.success_rate_by_tool()

        if success_df.empty:
            raise ValueError("No results to plot")

        fig, ax = plt.subplots(figsize=figsize)

        tools = success_df.index.tolist()
        x = np.arange(len(tools))

        valid = success_df['Valid'].values
        timeout = success_df['Timeout'].values
        tool_err = success_df['ToolError'].values
        result_err = success_df['ResultError'].values

        ax.bar(x, valid, label='Valid', color='green', alpha=0.8)
        ax.bar(x, timeout, bottom=valid, label='Timeout', color='orange', alpha=0.8)
        ax.bar(x, tool_err, bottom=valid+timeout, label='Tool Error', color='red', alpha=0.8)
        ax.bar(x, result_err, bottom=valid+timeout+tool_err, label='Result Error', color='darkred', alpha=0.8)

        ax.set_xlabel('Tool')
        ax.set_ylabel('Count')
        ax.set_title('Result Breakdown by Tool')
        ax.set_xticks(x)
        ax.set_xticklabels(tools, rotation=45, ha='right')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)

        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight')

        return fig

    def plot_runtime_heatmap(self, save_path: Optional[str] = None, figsize: Tuple[int, int] = (12, 10)) -> plt.Figure:
        """
        Heatmap of runtime by tool and setting.

        Args:
            save_path: Optional path to save the figure.
            figsize: Figure size tuple.

        Returns:
            Matplotlib Figure object.
        """
        if self.valid is None or self.valid.empty:
            raise ValueError("No valid results to plot")

        fig, ax = plt.subplots(figsize=figsize)

        pivot = self.valid.pivot_table(
            values='runtime',
            index='Setting',
            columns='Name',
            aggfunc='mean'
        )

        im = ax.imshow(pivot.values, aspect='auto', cmap='YlOrRd')

        ax.set_xticks(np.arange(len(pivot.columns)))
        ax.set_yticks(np.arange(len(pivot.index)))
        ax.set_xticklabels(pivot.columns, rotation=45, ha='right')
        ax.set_yticklabels(pivot.index)

        cbar = ax.figure.colorbar(im, ax=ax)
        cbar.set_label('Runtime (seconds)')

        ax.set_xlabel('Tool')
        ax.set_ylabel('Setting')
        ax.set_title('Runtime Heatmap')

        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight')

        return fig

    def plot_scatter_runtime_memory(self, save_path: Optional[str] = None, figsize: Tuple[int, int] = (10, 8)) -> plt.Figure:
        """
        Scatter plot of runtime vs memory usage colored by tool.

        Args:
            save_path: Optional path to save the figure.
            figsize: Figure size tuple.

        Returns:
            Matplotlib Figure object.
        """
        if self.valid is None or self.valid.empty:
            raise ValueError("No valid results to plot")

        fig, ax = plt.subplots(figsize=figsize)

        tools = self.tools()
        colors = plt.cm.tab10(np.linspace(0, 1, len(tools)))

        for tool, color in zip(tools, colors):
            tool_data = self.valid[self.valid['Name'] == tool]
            ax.scatter(
                tool_data['runtime'],
                tool_data['max_mem'] / 1024,  # Convert to MB
                label=tool,
                color=color,
                alpha=0.6,
                s=50
            )

        ax.set_xlabel('Runtime (seconds)')
        ax.set_ylabel('Max Memory (MB)')
        ax.set_title('Runtime vs Memory Usage')
        ax.legend(title='Tool', bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(alpha=0.3)

        plt.tight_layout()

        if save_path:
            fig.savefig(save_path, dpi=150, bbox_inches='tight')

        return fig

    # ==================== Report Generation ====================

    def generate_report(self, output_dir: Optional[str] = None) -> str:
        """
        Generate a comprehensive text report of performance analysis.

        Args:
            output_dir: Optional directory to save the report.

        Returns:
            Report as a string.
        """
        lines = []
        lines.append("=" * 60)
        lines.append(f"PERFORMANCE ANALYSIS REPORT: {self.name}")
        lines.append("=" * 60)
        lines.append("")

        # Summary
        lines.append("SUMMARY")
        lines.append("-" * 40)
        summary = self.summary()
        for key, value in summary.items():
            lines.append(f"  {key.capitalize():15s}: {value}")
        lines.append("")

        # Tools
        lines.append("TOOLS ANALYZED")
        lines.append("-" * 40)
        for tool in self.tools():
            lines.append(f"  - {tool}")
        lines.append("")

        # Runtime Statistics
        lines.append("RUNTIME STATISTICS (seconds)")
        lines.append("-" * 40)
        runtime_stats = self.runtime_statistics()
        if not runtime_stats.empty:
            lines.append(runtime_stats.to_string())
        lines.append("")

        # Memory Statistics
        lines.append("MEMORY STATISTICS (MB)")
        lines.append("-" * 40)
        mem_stats = self.memory_statistics()
        if not mem_stats.empty:
            lines.append(mem_stats.to_string())
        lines.append("")

        # Success Rate
        lines.append("SUCCESS RATE")
        lines.append("-" * 40)
        success = self.success_rate_by_tool()
        if not success.empty:
            lines.append(success.to_string())
        lines.append("")

        # Speedup
        lines.append("SPEEDUP COMPARISON")
        lines.append("-" * 40)
        speedup = self.speedup_matrix()
        if not speedup.empty:
            lines.append(speedup.to_string())
        lines.append("")

        report = "\n".join(lines)

        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
            report_path = os.path.join(output_dir, f"{self.name}_report.txt")
            with open(report_path, 'w') as f:
                f.write(report)

        return report

    def generate_all_figures(self, output_dir: str) -> List[str]:
        """
        Generate and save all available figures.

        Args:
            output_dir: Directory to save figures.

        Returns:
            List of saved figure paths.
        """
        os.makedirs(output_dir, exist_ok=True)
        saved = []

        try:
            path = os.path.join(output_dir, f"{self.name}_runtime_comparison.png")
            self.plot_runtime_comparison(save_path=path)
            saved.append(path)
            plt.close()
        except ValueError:
            pass

        try:
            path = os.path.join(output_dir, f"{self.name}_runtime_boxplot.png")
            self.plot_runtime_boxplot(save_path=path)
            saved.append(path)
            plt.close()
        except ValueError:
            pass

        try:
            path = os.path.join(output_dir, f"{self.name}_memory_comparison.png")
            self.plot_memory_comparison(save_path=path)
            saved.append(path)
            plt.close()
        except ValueError:
            pass

        try:
            path = os.path.join(output_dir, f"{self.name}_runtime_by_setting.png")
            self.plot_runtime_by_setting(save_path=path)
            saved.append(path)
            plt.close()
        except ValueError:
            pass

        try:
            path = os.path.join(output_dir, f"{self.name}_success_rate.png")
            self.plot_success_rate(save_path=path)
            saved.append(path)
            plt.close()
        except ValueError:
            pass

        try:
            path = os.path.join(output_dir, f"{self.name}_runtime_heatmap.png")
            self.plot_runtime_heatmap(save_path=path)
            saved.append(path)
            plt.close()
        except ValueError:
            pass

        try:
            path = os.path.join(output_dir, f"{self.name}_scatter_runtime_memory.png")
            self.plot_scatter_runtime_memory(save_path=path)
            saved.append(path)
            plt.close()
        except ValueError:
            pass

        return saved

    def __repr__(self) -> str:
        summary = self.summary()
        return (
            f"Analyser('{self.name}', "
            f"valid={summary['valid']}, "
            f"timeout={summary['timeout']}, "
            f"errors={summary['tool_error'] + summary['result_error']})"
        )


if __name__ == "__main__":
    # Hardcode path here
    result_path = "/Users/krq770/PycharmProjects/MonitoringFace_curr/Infrastructure/results/timely_version_comparison_signature2_20260117_201921"

    analyser = Analyser(result_path)
    print(analyser)
    print()
    print("Summary:", analyser.summary())
    print()
    print("Runtime Statistics:")
    print(analyser.runtime_statistics())
    print()
    print("Memory Statistics:")
    print(analyser.memory_statistics())
    print()
    print("Success Rate:")
    print(analyser.success_rate_by_tool())
