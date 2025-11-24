from Infrastructure.Builders.ToolBuilder.ToolManager import ToolManager
from Infrastructure.DataTypes.Contracts.SubContracts.TimeBounds import TimeGuarded, TimeGuardingTool
from Infrastructure.DataTypes.Types.custome_type import BranchOrRelease
from Infrastructure.Monitors.MonPoly.MonPoly import MonPoly
from Infrastructure.Monitors.MonitorManager import MonitorManager
from Infrastructure.Monitors.TimelyMon.TimelyMon import TimelyMon
from Infrastructure.Oracles.DataGolfOracle.DataGolfOracle import DataGolfOracle
from Infrastructure.Oracles.OracleManager import OracleManager
from Infrastructure.Oracles.VeriMonOracle.VeriMonOracle import VeriMonOracle
from Infrastructure.Parser.ParserConstants import TOOL_MANAGER, MONITORS, ORACLES, TIME_GUARD


def deconstruct_tool_manager(tool_manager: ToolManager):
    tools = dict()
    for index, image in enumerate(tool_manager.images.values()):
        tools[str(index)] = {
            "name": str(image.name),
            "branch": str(image.branch),
            "release": str(image.release)
        }
    return {TOOL_MANAGER: tools}


def construct_tool_manager(json_dump, path_to_build):
    def parse_branch_or_release(val_):
        if val_ == "BranchOrRelease.Branch":
            return BranchOrRelease.Branch
        else:
            return BranchOrRelease.Release

    tools = json_dump[TOOL_MANAGER]
    tools_to_build = [[items["name"], items["branch"], parse_branch_or_release(items["release"])] for items in tools.values()]

    return ToolManager(tools_to_build=tools_to_build, path_to_build=path_to_build)


def deconstruct_monitor_manager(monitor_manager: MonitorManager):
    def monitor_to_identifier(monitor_):
        if isinstance(monitor_, TimelyMon):
            return "TimelyMon"
        elif isinstance(monitor_, MonPoly):
            return "MonPoly"

    monitors = dict()
    for monitor in monitor_manager.monitors:
        monitors[monitor.image.name] = {
            "identifier": monitor_to_identifier(monitor), "name": monitor.image.name,
            "branch": monitor.image.branch, "params": str(monitor.params)
        }
    return {MONITORS: monitors}


def construct_monitor_manager(json_dump, tool_manager: ToolManager):
    monitors_to_build = [[items["identifier"], items["name"], items["branch"], items["params"]] for items in json_dump[MONITORS].values()]
    return MonitorManager(tool_manager=tool_manager, monitors_to_build=monitors_to_build)


def deconstruct_oracle_manager(oracle_manager: OracleManager):
    def oracle_to_identifier(oracle_):
        if isinstance(oracle_, VeriMonOracle):
            return "VeriMonOracle"
        elif isinstance(oracle_, DataGolfOracle):
            return "DataGolfOracle"

    oracles = dict()
    for oracle_key in oracle_manager.oracles.keys():
        oracle = oracle_manager.oracles[oracle_key]
        oracles[oracle_key] = {
            "identifier": oracle_to_identifier(oracle),
            "name": oracle.verimon.name,
            "params": str(oracle.parameters)
        }
    return {ORACLES: oracles}


def construct_oracle_manager(json_dump, monitor_manager: MonitorManager):
    oracles_to_build = [[key, items["identifier"], items["name"], items["params"]] for (key, items) in json_dump[ORACLES]]
    return OracleManager(monitor_manager=monitor_manager, oracles_to_build=oracles_to_build)


def deconstruct_time_guarded(time_guarded: TimeGuarded):
    def guard_type_to_str(gt):
        if gt == TimeGuardingTool.Monitor:
            return "Monitor"
        elif gt == TimeGuardingTool.Oracle:
            return "Oracle"
        else:
            return "Generator"

    return {
        TIME_GUARD: {
            "time_guarded": str(time_guarded.time_guarded),
            "guard_type": guard_type_to_str(time_guarded.guard_type),
            "lower_bound": time_guarded.lower_bound,
            "upper_bound": time_guarded.upper_bound,
            "guard": time_guarded.guard
        }
    }


def construct_time_guarded(json_dump, monitor_manager: MonitorManager):
    def str_to_guard_type(gt):
        if gt == "Monitor":
            return TimeGuardingTool.Monitor
        elif gt == "Oracle":
            return TimeGuardingTool.Oracle
        else:
            return TimeGuardingTool.Generator

    vals = json_dump[TIME_GUARD]
    return TimeGuarded(
        time_guarded=vals["time_guarded"], lower_bound=vals["lower_bound"], upper_bound=vals["upper_bound"],
        guard_type=str_to_guard_type(vals["guard_type"]), guard_name=vals["guard"], monitor_manager=monitor_manager
    )


if __name__ == "__main__":
    val = {TOOL_MANAGER: {'0': {'name': 'TimelyMon', 'branch': 'input_optims', 'release': 'BranchOrRelease.Branch'}, '1': {'name': 'TimelyMon', 'branch': 'development', 'release': 'BranchOrRelease.Branch'}, '2': {'name': 'MonPoly', 'branch': 'master', 'release': 'BranchOrRelease.Branch'}}}
    print(construct_tool_manager(val, ""))
