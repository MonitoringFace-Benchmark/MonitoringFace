import os
from enum import Enum
from typing import Tuple, Optional

import pandas as pd

from Infrastructure.Analysis.Aggregators.AbstractAggregator import AbstractAggregator


class Status(Enum):
    OK = "OK"
    ATO = "Accumulative Latency Time out"
    MTO = "Maximum Latency Time out"
    TE = "Tool Error"
    RE = "Result Error"
    MI = "Missing"


class ResultAggregatorOnline(AbstractAggregator):
    def __init__(self):
        self.valid_results = pd.DataFrame(columns=[
            "Status", "Name", "Setting", "pre", "build", "total_elapsed", "total_count"
        ])

        self.timeout_maximum_latency_results = pd.DataFrame(columns=[
            "Status", "Name", "Setting", "pre", "build", "total_elapsed", "total_count"
        ])

        self.timeout_accumulative_latency_results = pd.DataFrame(columns=[
            "Status", "Name", "Setting", "pre", "build", "total_elapsed", "total_count"
        ])

        self.tool_error_results = pd.DataFrame(columns=[
            "Status", "Name", "Setting", "error"
        ])

        self.result_error_results = pd.DataFrame(columns=[
            "Status", "Name", "Setting", "pre", "build", "total_elapsed", "total_count", "error_msg"
        ])

        self.missing_results = pd.DataFrame(columns=["Status", "Name", "Setting"])

    def add_valid(
            self,
            tool_name: str,
            setting_id: str,
            prep: float,
            build: float,
            total_elapsed: Optional[float],
            total_count: Optional[int]
    ) -> None:
        self.valid_results.loc[len(self.valid_results)] = [
            Status.OK, tool_name, setting_id, prep, build, total_elapsed, total_count
        ]

    def add_timeout_accumulative_latency(
            self,
            tool_name: str,
            setting_id: str,
            prep: float,
            build: float,
            total_elapsed: Optional[float],
            total_count: Optional[int]
    ) -> None:
        self.timeout_accumulative_latency_results.loc[len(self.timeout_accumulative_latency_results)] = [
            Status.ATO, tool_name, setting_id, prep, build, total_elapsed, total_count
        ]

    def add_timeout_maximum_latency(
            self,
            tool_name: str,
            setting_id: str,
            prep: float,
            build: float,
            total_elapsed: Optional[float],
            total_count: Optional[int]
    ) -> None:
        self.timeout_maximum_latency_results.loc[len(self.timeout_maximum_latency_results)] = [
            Status.MTO, tool_name, setting_id, prep, build, total_elapsed, total_count
        ]

    def add_tool_error(
            self,
            tool_name: str,
            setting_id: str,
            error: str
    ) -> None:
        self.tool_error_results.loc[len(self.tool_error_results)] = [
            Status.TE, tool_name, setting_id, str(error)
        ]

    def add_result_error(
            self,
            tool_name: str,
            setting_id: str,
            prep: float,
            build: float,
            total_elapsed: Optional[float],
            total_count: Optional[int],
            error_msg: str
    ) -> None:
        self.result_error_results.loc[len(self.result_error_results)] = [
            Status.RE, tool_name, setting_id, prep, build, total_elapsed, total_count, error_msg
        ]

    def add_missing(
            self,
            tool_name: str,
            setting_id: str
    ) -> None:
        self.missing_results.loc[len(self.missing_results)] = [
            Status.MI, tool_name, setting_id
        ]

    def get_valid(self) -> pd.DataFrame:
        return self.valid_results.copy()

    def get_timeout_accumulative_latency(self) -> pd.DataFrame:
        return self.timeout_accumulative_latency_results.copy()

    def get_timeout_maximum_latency(self) -> pd.DataFrame:
        return self.timeout_maximum_latency_results.copy()

    def get_tool_error(self) -> pd.DataFrame:
        return self.tool_error_results.copy()

    def get_result_error(self) -> pd.DataFrame:
        return self.result_error_results.copy()

    def get_missing(self) -> pd.DataFrame:
        return self.missing_results.copy()

    def get_all(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        return (
            self.get_valid(),
            self.get_timeout_accumulative_latency(),
            self.get_timeout_maximum_latency(),
            self.get_tool_error(),
            self.get_result_error(),
            self.get_missing()
        )

    def to_csv(self, path: str, name: str) -> None:
        os.makedirs(path, exist_ok=True)
        print(f"Writing results to: {path} with name: {name}")

        if not self.valid_results.empty:
            filepath = os.path.join(path, f"{name}_valid.csv")
            print(f"  Writing valid results ({len(self.valid_results)} rows) to: {filepath}")
            self.valid_results.to_csv(filepath, index=False)

        if not self.timeout_accumulative_latency_results.empty:
            filepath = os.path.join(path, f"{name}_timeout_accumulative_latency.csv")
            print(f"  Writing timeout_accumulative_latency results ({len(self.timeout_accumulative_latency_results)} rows) to: {filepath}")
            self.timeout_accumulative_latency_results.to_csv(filepath, index=False)

        if not self.timeout_maximum_latency_results.empty:
            filepath = os.path.join(path, f"{name}_timeout_maximum_latency.csv")
            print(f"  Writing timeout_maximum_latency results ({len(self.timeout_maximum_latency_results)} rows) to: {filepath}")
            self.timeout_maximum_latency_results.to_csv(filepath, index=False)

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
            f"ResultAggregatorOnline(\n"
            f"  valid={len(self.valid_results)},\n"
            f"  timeout_accumulative_latency={len(self.timeout_accumulative_latency_results)},\n"
            f"  timeout_maximum_latency={len(self.timeout_maximum_latency_results)},\n"
            f"  tool_error={len(self.tool_error_results)},\n"
            f"  result_error={len(self.result_error_results)},\n"
            f"  missing={len(self.missing_results)}\n"
            f")"
        )
