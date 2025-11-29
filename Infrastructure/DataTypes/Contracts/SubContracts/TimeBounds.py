from enum import Enum


class TimeGuardingTool(Enum):
    Generator = 1,
    Oracle = 2,
    Monitor = 3


class TimeGuarded:
    def __init__(self, time_guarded, guard_type, monitor_manager, guard_name=None, lower_bound=None, upper_bound=None):
        self.time_guarded = time_guarded
        self.guard_type = guard_type

        self.lower_bound = lower_bound
        self.upper_bound = upper_bound

        self.guard_name = guard_name
        if guard_type == TimeGuardingTool.Monitor:
            self.guard = monitor_manager.get_monitor(self.guard_name)
        else:
            self.guard = None
