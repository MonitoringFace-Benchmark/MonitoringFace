import importlib
from pathlib import Path

from Infrastructure.printing import print_headline, print_footline


def _discover_monitors():
    monitors = {}
    monitors_dir = Path(__file__).parent
    for item in monitors_dir.iterdir():
        if not item.is_dir() or item.name.startswith('_') or item.name == '__pycache__':
            continue
        
        folder_name = item.name
        module_file = item / f"{folder_name}.py"

        if module_file.exists():
            try:
                module_path = f"Infrastructure.Monitors.{folder_name}.{folder_name}"
                module = importlib.import_module(module_path)

                if hasattr(module, folder_name):
                    monitor_class = getattr(module, folder_name)
                    monitors[folder_name] = monitor_class
            except (ImportError, AttributeError) as e:
                print(f"Warning: Could not load monitor {folder_name}: {e}")
    return monitors


def identifier_to_monitor(tool_manager, identifier, branch, name, params):
    available_monitors = _discover_monitors()
    if identifier not in available_monitors:
        available = ', '.join(available_monitors.keys())
        raise ValueError(
            f"Unknown monitor identifier: '{identifier}'. "
            f"Available monitors: {available}"
        )
    
    monitor_class = available_monitors[identifier]
    return monitor_class(tool_manager.get_image(identifier, branch), name, params)


class MonitorManager:
    def __init__(self, tool_manager, monitors_to_build):
        print_headline("(Starting) Building MonitorManager")
        self.monitors = {}
        failed_builds = []
        for (identifier, name, branch, params) in monitors_to_build:
            try:
                print(f"-> Attempting to construct Monitor {identifier} - {branch}")
                self.monitors[name] = identifier_to_monitor(
                    tool_manager=tool_manager, identifier=identifier,
                    branch=branch, name=name, params=params
                )
                print(f"    -> (Success)")
            except Exception:
                print(f"-> (Failure)")
                failed_builds += [f"{identifier} - {branch}"]

        if failed_builds:
            print(f"\nFailed to Construct:")
            for fail in failed_builds:
                print(f" - {fail}")

        print_footline("(Finished) Building MonitorManager")

    def get_monitor(self, name):
        return self.monitors.get(name)

    def get_monitors(self, names):
        return [self.get_monitor(name) for name in names]