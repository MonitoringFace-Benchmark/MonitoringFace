from Infrastructure.Monitors.MonPoly.MonPoly import MonPoly
from Infrastructure.Monitors.TimelyMon.TimelyMon import TimelyMon


def identifier_to_monitor(tool_manager, identifier, branch, name, params):
    if identifier == "TimelyMon":
        return TimelyMon(tool_manager.get_image(identifier, branch), name, params)
    elif identifier == "MonPoly":
        return MonPoly(tool_manager.get_image(identifier, branch), name, params)


class MonitorManager:
    def __init__(self, tool_manager, monitors_to_build):
        self.monitors = {}
        for (identifier, name, branch, params) in monitors_to_build:
            self.monitors[name] = identifier_to_monitor(
                tool_manager=tool_manager, identifier=identifier,
                branch=branch, name=name, params=params
            )

    def get_monitor(self, name):
        return self.monitors.get(name)

    def get_monitors(self, names):
        return [self.get_monitor(name) for name in names]