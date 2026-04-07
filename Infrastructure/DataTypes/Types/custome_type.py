from enum import Enum
from typing import AnyStr


class BranchOrRelease(Enum):
    Release = 0
    Branch = 1


class Processor(Enum):
    DataGenerators = 1,
    DataConverters = 2,
    PolicyGenerators = 3,
    PolicyConverters = 4,
    CaseStudies = 5,
    Benchmark = 6,
    GeneralUtilities = 7


def processor_to_identifier(p: Processor) -> AnyStr:
    if p == Processor.DataGenerators:
        return "DataGenerators"
    elif p == Processor.DataConverters:
        return "DataConverters"
    elif p == Processor.PolicyGenerators:
        return "PolicyGenerators"
    elif p == Processor.PolicyConverters:
        return "PolicyConverters"
    elif p == Processor.CaseStudies:
        return "CaseStudies"
    elif p == Processor.Benchmark:
        return "Benchmark"
    else:
        return "GeneralUtilities"


class OnlineOffline(Enum):
    Online = "online"
    Offline = "offline"

    def to_string(self) -> AnyStr:
        if self == OnlineOffline.Online:
            return "online"
        else:
            return "offline"


def online_offline_from_string(s: AnyStr) -> OnlineOffline:
    if s == "online":
        return OnlineOffline.Online
    elif s == "offline":
        return OnlineOffline.Offline
    else:
        raise ValueError(f"Invalid string for OnlineOffline: {s}")


class InputSpeed(Enum):
    REAL_TIME = "real-time"
    ACCELERATED = "accelerated"

    def to_string(self):
        if self == InputSpeed.REAL_TIME:
            return "real-time"
        elif self == InputSpeed.ACCELERATED:
            return "accelerated"
        else:
            raise ValueError(f"Unsupported InputSpeed value: {self}")


class DataSourceType(Enum):
    FILE = "file"
    SCRIPT = "script"

    def to_string(self):
        if self == DataSourceType.FILE:
            return "file"
        elif self == DataSourceType.SCRIPT:
            return "script"
        else:
            raise ValueError(f"Unsupported DataSourceType value: {self}")


class TimeUnits(Enum):
    SECONDS = "seconds"
    MILLISECONDS = "milliseconds"
    MICROSECONDS = "microseconds"

    def to_string(self):
        if self == TimeUnits.SECONDS:
            return "seconds"
        elif self == TimeUnits.MILLISECONDS:
            return "milliseconds"
        elif self == TimeUnits.MICROSECONDS:
            return "microseconds"
        else:
            raise ValueError(f"Unsupported TimeUnits value: {self}")


class FormatType(Enum):
    CSV = "csv"
    LOG = "log"

    def to_string(self):
        if self == FormatType.CSV:
            return "csv"
        elif self == FormatType.LOG:
            return "log"
        else:
            raise ValueError(f"Unsupported FormatType value: {self}")


class ResponseMode(Enum):
    EVENT_COUNT = "event-count"
    CURRENT_TIMEPOINT = "current-timepoint"

    def to_string(self):
        if self == ResponseMode.EVENT_COUNT:
            return "event-count"
        elif self == ResponseMode.CURRENT_TIMEPOINT:
            return "current-timepoint"
        else:
            raise ValueError(f"Unsupported ResponseMode value: {self}")
