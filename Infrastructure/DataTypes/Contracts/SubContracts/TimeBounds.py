from enum import Enum


class TimeGuardingTool(Enum):
    Generator = 1,
    Oracle = 2,
    Monitor = 3


class TimeGuarded:
    def __init__(self, time_guarded, guard_type, guard_name, monitor_manager, lower_bound=None, upper_bound=None):
        self.time_guarded = time_guarded
        self.guard_type = guard_type

        self.lower_bound = lower_bound
        self.upper_bound = upper_bound

        self.guard_name = guard_name
        self.guard = monitor_manager.get_monitor(self.guard_name)
