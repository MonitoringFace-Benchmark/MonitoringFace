from enum import Enum
from typing import Optional

from Infrastructure.Monitors.MonitorManager import MonitorManager


class TimeGuardingTool(Enum):
    Generator = 1,
    Oracle = 2,
    Monitor = 3


class ConstructionConstraints:
    def __init__(self, monitor_manager: MonitorManager, guarding_tool: Optional[TimeGuardingTool] = None, guard_name: str = None, lower_bound: int = None, upper_bound: int = None):
        self.guard_type = guarding_tool
        if self.guard_type == TimeGuardingTool.Monitor and guard_name is not None:
            self.guard = monitor_manager.get_monitor(guard_name)
        else:
            self.guard = None
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound


class RunTimeConstraints:
    def __init__(self, upper_bound=None):
        self.upper_bound = upper_bound


class TimeConstraints:
    def __init__(self, run_time_constraints: Optional[RunTimeConstraints] = None, construction_constraints: Optional[ConstructionConstraints] = None):
        self.run_time_constraints = run_time_constraints
        self.construction_constraints = construction_constraints

    def runtime_constraint(self):
        if self.run_time_constraints is None:
            return None
        return self.run_time_constraints.upper_bound

    def construction_constraint(self):
        if self.construction_constraints is None:
            return None
        return self.construction_constraints
