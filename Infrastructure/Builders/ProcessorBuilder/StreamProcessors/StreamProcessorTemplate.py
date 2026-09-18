import importlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional


class StreamProcessorException(Exception):
    pass


class StreamProcessorTemplate(ABC):
    buffering: bool = False
    deterministic: bool = True

    def __init__(self, name: str):
        self.name = name
        self.dropped = 0

    def setup(self, params: Dict) -> None:
        pass

    @abstractmethod
    def feed(self, line: str) -> List[str]:
        pass

    def flush(self) -> List[str]:
        return []

    def released_origins(self) -> Optional[List[int]]:
        return None

    def stats(self) -> Dict:
        return {}


def discover_stream_processors(path_to_archive: str) -> List[str]:
    root = Path(f"{path_to_archive}/Implementations/Builders/ProcessorBuilder/StreamProcessors")
    if not root.is_dir():
        return []
    return sorted(
        item.name for item in root.iterdir()
        if item.is_dir() and not item.name.startswith('_') and item.name != '__pycache__'
    )


def load_stream_processor(name: str):
    cls = getattr(
        importlib.import_module(
            f"Archive.Implementations.Builders.ProcessorBuilder.StreamProcessors.{name}.{name}"),
        name)
    if not (isinstance(cls, type) and issubclass(cls, StreamProcessorTemplate)):
        raise StreamProcessorException(
            f"{name} is not a StreamProcessorTemplate subclass")
    return cls
