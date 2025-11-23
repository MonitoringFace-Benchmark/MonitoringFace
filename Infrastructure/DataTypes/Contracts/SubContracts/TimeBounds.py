from dataclasses import dataclass
from enum import Enum
from typing import Optional

from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate


class TimeGuardingTool(Enum):
    Generator = 1,
    Oracle = 2,
    Monitor = 3


@dataclass
class TimeGuarded:
    time_guarded: bool
    lower_bound: Optional[int]
    upper_bound: Optional[int]

    guard_type: TimeGuardingTool
    guard: Optional[AbstractMonitorTemplate]