from enum import Enum
from typing import Optional

from Infrastructure.Monitors.AbstractMonitorTemplate import AbstractMonitorTemplate


class TimeGuardingTool(Enum):
    Generator = 1,
    Oracle = 2,
    Monitor = 3


class GenerationConstraints:
    def __init__(self, guarding_tool: Optional[TimeGuardingTool] = None, guard: Optional[AbstractMonitorTemplate] = None, lower_bound: int = None, upper_bound: int = None):
        self.guard_type = guarding_tool
        self.guard = guard
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound


class RunTimeConstraints:
    def __init__(self, upper_bound=None):
        self.upper_bound = upper_bound


class TimeConstraints:
    def __init__(self, run_time_constraints: Optional[RunTimeConstraints] = None, generation_constraints: Optional[GenerationConstraints] = None):
        self.run_time_constraints = run_time_constraints
        self.generation_constraints = generation_constraints

    def runtime_constraint(self):
        if self.run_time_constraints is None:
            return None
        return self.run_time_constraints.upper_bound

    def generation_constraint(self):
        return self.generation_constraints
