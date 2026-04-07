from typing import Optional


class PathManager:
    def __init__(self):
        self.paths = dict()

    def add_path(self, path_id: str, path):
        self.paths[path_id] = path

    def get_path(self, path_id: str) -> Optional[str]:
        if path_id in self.paths:
            return self.paths[path_id]
        raise ValueError("PathManager: Path ID not found: " + path_id)
