from typing import Optional, List
from Infrastructure.DataTypes.Types.custome_type import DataSourceType, TimeUnits, FormatType, InputSpeed


class OnlineExperimentContractGeneral:
    def __init__(
        self, data_source_type: DataSourceType, mode: InputSpeed, maximum_latency: Optional[int],
        accumulated_latency: Optional[int], timestamp_units: TimeUnits,
        batch_delimiter: Optional[str]

    ):
        self.data_source_type = data_source_type
        self.timestamp_units = timestamp_units

        self.mode = mode

        self.batch_delimiter = batch_delimiter

        self.maximum_latency = maximum_latency
        self.accumulated_latency = accumulated_latency

    def get_mode(self) -> List[str]:
        return ["--mode", self.mode.to_string()]

    def get_batch_delimiter(self) -> List[str]:
        if self.batch_delimiter is None:
            return []
        return ["--batch-delimiter", self.batch_delimiter]

    def get_timestamp_units(self) -> List[str]:
        return ["--timestamp-units", self.timestamp_units.to_string()]

    def get_data_source_type(self) -> List[str]:
        return ["--data-source-type", self.data_source_type.to_string()]

    def get_accumulated_latency(self) -> List[str]:
        if self.accumulated_latency is None:
            return []
        return ["--accumulated-latency", str(self.accumulated_latency)]

    def get_maximum_latency(self) -> List[str]:
        if self.maximum_latency is None:
            return []
        return ["--maximum-latency", str(self.maximum_latency)]

    def get_settings(self) -> List[str]:
        settings = []
        settings += self.get_mode()
        settings += self.get_data_source_type()
        settings += self.get_timestamp_units()
        settings += self.get_batch_delimiter()
        settings += self.get_accumulated_latency()
        settings += self.get_maximum_latency()
        return settings


class OnlineExperimentContractTool:
    def __init__(self, formatting: FormatType, response_mode, input_aggregations, latency_marker: Optional[str] = None, warm_up_input: Optional[str] = None):
        self.formatting = formatting
        self.response_mode = response_mode
        self.input_aggregations = input_aggregations
        self.latency_marker = latency_marker
        self.warm_up_input = warm_up_input

    def get_format(self) -> List[str]:
        return ["--format", self.formatting.to_string()]

    def get_response_mode(self) -> List[str]:
        return ["--response-mode", self.response_mode.to_string()]

    def get_input_aggregations(self) -> List[str]:
        if self.input_aggregations is None:
            return []
        return ["--input-aggregations", self.input_aggregations]

    def get_latency_marker(self) -> List[str]:
        if self.latency_marker is None:
            return []
        return ["--latency-marker", self.latency_marker]

    def get_warm_up_input(self) -> List[str]:
        if self.warm_up_input is None:
            return []
        return ["--warm-up-input", self.warm_up_input]

    def get_tool_arguments(self) -> List[str]:
        arguments = []
        arguments += self.get_input_aggregations()
        arguments += self.get_format()
        arguments += self.get_response_mode()
        arguments += self.get_latency_marker()
        arguments += self.get_warm_up_input()
        return arguments
