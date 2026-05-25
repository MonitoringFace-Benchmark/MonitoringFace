import importlib
from pathlib import Path

from Infrastructure.Monitors.MonitorManager import MonitorManager
from Infrastructure.printing import print_headline, print_footline


def _discover_oracles(path_to_oracles):
    oracles = {}
    for item in Path(path_to_oracles).iterdir():
        if not item.is_dir() or item.name.startswith('_') or item.name == '__pycache__':
            continue

        folder_name = item.name
        module_file = item / f"{folder_name}.py"

        if module_file.exists():
            try:
                module_path = f"Archive.Implementations.Oracles.{folder_name}.{folder_name}"
                module = importlib.import_module(module_path)
                if hasattr(module, folder_name):
                    oracle_class = getattr(module, folder_name)
                    oracles[folder_name] = oracle_class
            except (ImportError, AttributeError) as e:
                print(f"Warning: Could not load monitor {folder_name}: {e}")
    return oracles


def identifier_to_oracle(monitor, identifier, params, path_to_oracles):
    available_oracles = _discover_oracles(path_to_oracles)
    if identifier not in available_oracles:
        available = ', '.join(available_oracles.keys())
        raise ValueError(
            f"Unknown monitor identifier: '{identifier}'. "
            f"Available monitors: {available}"
        )
    oracle_class = available_oracles[identifier]
    return oracle_class(monitor, params)


class OracleManager:
    def __init__(self, monitor_manager: MonitorManager, oracles_to_build, path_to_archive):
        print_headline("(Starting) Building OracleManager")
        self.oracles = {}
        failed_builds = []
        for (oracle_name, identifier, monitor_name, params) in oracles_to_build:
            try:
                print(f"-> Attempting to construct Oracle {identifier}")
                self.oracles[oracle_name] = identifier_to_oracle(
                    monitor_manager.get_monitor(monitor_name), identifier,
                    params, f"{path_to_archive}/Implementations/Oracles")
                print(f"    -> (Success)")
            except Exception:
                print(f"-> (Failure)")
                failed_builds += [f"{identifier}"]

        if failed_builds:
            print(f"\nFailed to Construct:")
            for fail in failed_builds:
                print(f" - {fail}")

        print_footline("(Finished) Building OracleManager")

    def get_oracle(self, name):
        return self.oracles.get(name)
