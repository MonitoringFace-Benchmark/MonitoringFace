import os
import importlib
from pathlib import Path


def _discover_monitors():
    monitors = {}
    monitors_dir = Path(__file__).parent
    
    # Iterate through all subdirectories in the Monitors folder
    for item in monitors_dir.iterdir():
        if not item.is_dir() or item.name.startswith('_') or item.name == '__pycache__':
            continue
        
        folder_name = item.name
        module_file = item / f"{folder_name}.py"
        
        # Check if the corresponding .py file exists
        if module_file.exists():
            try:
                # Dynamically import the module
                module_path = f"Infrastructure.Monitors.{folder_name}.{folder_name}"
                module = importlib.import_module(module_path)
                
                # Get the class with the same name as the folder
                if hasattr(module, folder_name):
                    monitor_class = getattr(module, folder_name)
                    monitors[folder_name] = monitor_class
            except (ImportError, AttributeError) as e:
                print(f"Warning: Could not load monitor {folder_name}: {e}")
    
    return monitors


# Discover all available monitors at module load time
_AVAILABLE_MONITORS = _discover_monitors()


def identifier_to_monitor(tool_manager, identifier, branch, name, params):
    if identifier not in _AVAILABLE_MONITORS:
        available = ', '.join(_AVAILABLE_MONITORS.keys())
        raise ValueError(
            f"Unknown monitor identifier: '{identifier}'. "
            f"Available monitors: {available}"
        )
    
    monitor_class = _AVAILABLE_MONITORS[identifier]
    return monitor_class(tool_manager.get_image(identifier, branch), name, params)



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