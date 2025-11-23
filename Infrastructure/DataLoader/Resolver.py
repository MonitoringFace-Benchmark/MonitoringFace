import os.path
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

from Infrastructure.DataLoader.DataLoader import DataLoader
from Infrastructure.DataLoader.Downloader import MonitoringFaceDownloader
from Infrastructure.constants import IMAGE_POSTFIX


class Location(Enum):
    Local = 1
    Remote = 2
    Unavailable = 3


class Resolver(ABC):
    @abstractmethod
    def resolve(self):
        pass


class ToolResolver(Resolver):
    def __init__(self, name, branch, path_to_build_inner):
        self.image_name = f"{name.lower()}_{branch.lower()}{IMAGE_POSTFIX}"
        self.name = name
        self.path = path_to_build_inner

    def resolve(self) -> Optional[Location]:
        # check local
        if os.path.exists(f"{self.path}/Dockerfile"):
            return Location.Local

        # check online
        if any(tool == self.name for tool in MonitoringFaceDownloader().get_all_names()):
            return Location.Remote

        # not available
        return Location.Unavailable


class ProcessorResolver(Resolver):
    def __init__(self, name, path_to_build_inner, processor_type):
        self.image_name = f"{name.lower()}{IMAGE_POSTFIX}"
        self.name = name
        self.path = path_to_build_inner
        self.processor_type = processor_type

    def resolve(self) -> Optional[Location]:
        # check local
        if os.path.exists(f"{self.path}/{self.name}/Dockerfile"):
            return Location.Local

        # check online
        if any(tool == self.name for tool in DataLoader(self.processor_type).get_all_names()):
            return Location.Remote

        # not available
        return Location.Unavailable
