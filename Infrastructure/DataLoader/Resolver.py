import os.path
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

from Infrastructure.DataLoader.DataLoader import DataLoader
from Infrastructure.DataLoader.Downloader import MonitoringFaceDownloader
from Infrastructure.DataTypes.Types.custome_type import Processor
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
    def __init__(self, name, branch, path_to_build_inner, path_to_archive, path_to_infra):
        self.image_name = f"{name.lower()}_{branch.lower()}{IMAGE_POSTFIX}"
        self.name = name
        self.path = path_to_build_inner
        self.path_archive = path_to_archive
        self.path_to_infra = path_to_infra

    def resolve(self) -> Optional[Location]:
        docker_file_exists = os.path.exists(f"{self.path_archive}/Dockerfile")
        prop_file_exists = os.path.exists(f"{self.path_archive}/tool.properties")
        if docker_file_exists and prop_file_exists:
            return Location.Local

        # check online
        if any(tool == self.name for tool in MonitoringFaceDownloader(self.path_to_infra).get_all_names()):
            return Location.Remote

        # not available
        return Location.Unavailable


class BenchmarkResolver(Resolver):
    def __init__(self, name, path_to_archive, path_to_infra):
        self.name = name
        self.path_to_archive = path_to_archive
        self.path_to_infra = path_to_infra

    def resolve(self) -> Optional[Location]:
        file_exists = os.path.exists(f"{self.path_to_archive}/Benchmarks/{self.name}")
        print(DataLoader(Processor.Benchmark, path_to_infra=self.path_to_infra).get_all_names())
        if file_exists:
            return Location.Local

        if any(tool == self.name for tool in DataLoader(Processor.Benchmark, path_to_infra=self.path_to_infra).get_all_names()):
            return Location.Remote

        return Location.Unavailable


class ProcessorResolver(Resolver):
    def __init__(self, name, path_to_build_inner, processor_type, path_to_archive, path_to_infra):
        self.image_name = f"{name.lower()}{IMAGE_POSTFIX}"
        self.name = name
        self.path = path_to_build_inner
        self.processor_type = processor_type
        self.path_archive = path_to_archive
        self.path_to_infra = path_to_infra

    def resolve(self) -> Optional[Location]:
        docker_file_exists = os.path.exists(f"{self.path_archive}/Dockerfile")
        prop_file_exists = os.path.exists(f"{self.path_archive}/tool.properties")
        # check local
        if docker_file_exists and prop_file_exists:
            return Location.Local

        # check online
        if any(tool == self.name for tool in DataLoader(self.processor_type, self.path_to_infra).get_all_names()):
            return Location.Remote

        # not available
        return Location.Unavailable
