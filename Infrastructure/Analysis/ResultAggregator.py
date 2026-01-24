import os
from enum import Enum
from typing import Tuple

import pandas as pd

from Infrastructure.Analysis.Formatting import parse_wall_time
from Infrastructure.Analysis.Formatting import parse_memory
from Infrastructure.Analysis.Formatting import parse_cpu


class Status(Enum):
    OK = "OK"
    TO = "Time out"
    TE = "Tool Error"
    RE = "Result Error"
    MI = "Missing"


class ResultAggregator:
    """
    Handles results of run_tools in BenchmarkBuilder.
    Manages four result states: valid, timeout, tool_error, result_error.
    """

    def __init__(self):
        # Valid runs: full timing and stats
        self.valid_results = pd.DataFrame(columns=[
            "Status", "Name", "Setting", "pre", "compilation", "runtime", "post", "wall_time", "max_mem", "cpu"
        ])

        # Timed out runs: only status, tool name, setting, and timeout value
        self.timeout_results = pd.DataFrame(columns=[
            "Status", "Name", "Setting", "timeout"
        ])

        # Tool exceptions: status, tool name, setting, and error message
        self.tool_error_results = pd.DataFrame(columns=[
            "Status", "Name", "Setting", "error"
        ])

        # Result errors: same as valid but with error message
        self.result_error_results = pd.DataFrame(columns=[
            "Status", "Name", "Setting", "pre", "compilation", "runtime", "post", "wall_time", "max_mem", "cpu", "error_msg"
        ])

        # Missing tools: status, tool name, setting
        self.missing_results = pd.DataFrame(columns=[
            "Status", "Name", "Setting"
        ])

    def add_valid(
            self,
            tool_name: str,
            setting_id: str,
            prep: float,
            compiled: float,
            runtime: float,
            prop: float,
            wall_time: str,
            max_mem: str,
            cpu: str
    ) -> None:
        """Add a valid run result."""
        self.valid_results.loc[len(self.valid_results)] = [
            Status.OK, tool_name, setting_id, prep, compiled, runtime, prop,
            parse_wall_time(wall_time), parse_memory(max_mem), parse_cpu(cpu)
        ]

    def add_timeout(
            self,
            tool_name: str,
            setting_id: str,
            timeout: int
    ) -> None:
        """Add a timed out run result."""
        self.timeout_results.loc[len(self.timeout_results)] = [
            Status.TO, tool_name, setting_id, timeout
        ]

    def add_tool_error(
            self,
            tool_name: str,
            setting_id: str,
            error: str
    ) -> None:
        """Add a tool exception result."""
        self.tool_error_results.loc[len(self.tool_error_results)] = [
            Status.TE, tool_name, setting_id, str(error)
        ]

    def add_result_error(
            self,
            tool_name: str,
            setting_id: str,
            prep: float,
            compiled: float,
            runtime: float,
            prop: float,
            wall_time: str,
            max_mem: str,
            cpu: str,
            error_msg: str
    ) -> None:
        """Add a result error (verification failed)."""
        self.result_error_results.loc[len(self.result_error_results)] = [
            Status.RE, tool_name, setting_id, prep, compiled, runtime, prop,
            parse_wall_time(wall_time), parse_memory(max_mem), parse_cpu(cpu), error_msg
        ]

    def add_missing(
            self,
            tool_name: str,
            setting_id: str
    ) -> None:
        """Add a missing tool result."""
        self.missing_results.loc[len(self.missing_results)] = [
            Status.MI, tool_name, setting_id
        ]

    def get_valid(self) -> pd.DataFrame:
        """Get all valid run results."""
        return self.valid_results.copy()

    def get_timeout(self) -> pd.DataFrame:
        """Get all timeout results."""
        return self.timeout_results.copy()

    def get_tool_error(self) -> pd.DataFrame:
        """Get all tool error results."""
        return self.tool_error_results.copy()

    def get_result_error(self) -> pd.DataFrame:
        """Get all result error results."""
        return self.result_error_results.copy()

    def get_missing(self) -> pd.DataFrame:
        """Get all missing tool results."""
        return self.missing_results.copy()

    def get_all(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Get all result dataframes."""
        return (
            self.get_valid(),
            self.get_timeout(),
            self.get_tool_error(),
            self.get_result_error(),
            self.get_missing()
        )

    def to_csv(self, path: str, name: str) -> None:
        """
        Write all dataframes to CSV files in the specified folder.
        Creates files: {name}_valid.csv, {name}_timeout.csv, {name}_tool_error.csv, {name}_result_error.csv
        """
        os.makedirs(path, exist_ok=True)
        print(f"Writing results to: {path} with name: {name}")

        if not self.valid_results.empty:
            filepath = os.path.join(path, f"{name}_valid.csv")
            print(f"  Writing valid results ({len(self.valid_results)} rows) to: {filepath}")
            self.valid_results.to_csv(filepath, index=False)

        if not self.timeout_results.empty:
            filepath = os.path.join(path, f"{name}_timeout.csv")
            print(f"  Writing timeout results ({len(self.timeout_results)} rows) to: {filepath}")
            self.timeout_results.to_csv(filepath, index=False)

        if not self.tool_error_results.empty:
            filepath = os.path.join(path, f"{name}_tool_error.csv")
            print(f"  Writing tool_error results ({len(self.tool_error_results)} rows) to: {filepath}")
            self.tool_error_results.to_csv(filepath, index=False)

        if not self.result_error_results.empty:
            filepath = os.path.join(path, f"{name}_result_error.csv")
            print(f"  Writing result_error results ({len(self.result_error_results)} rows) to: {filepath}")
            self.result_error_results.to_csv(filepath, index=False)

        if not self.missing_results.empty:
            filepath = os.path.join(path, f"{name}_missing.csv")
            print(f"  Writing missing results ({len(self.missing_results)} rows) to: {filepath}")
            self.missing_results.to_csv(filepath, index=False)

    def __repr__(self) -> str:
        return (
            f"ResultAggregator(\n"
            f"  valid={len(self.valid_results)},\n"
            f"  timeout={len(self.timeout_results)},\n"
            f"  tool_error={len(self.tool_error_results)},\n"
            f"  result_error={len(self.result_error_results)},\n"
            f"  missing={len(self.missing_results)}\n"
            f")"
        )

