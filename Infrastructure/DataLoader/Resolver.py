import os.path
import sys
from abc import ABC, abstractmethod
from enum import Enum
from typing import Optional

from Infrastructure.DataLoader.DataLoader import DataLoader
from Infrastructure.DataLoader.Downloader import MonitoringFaceDownloader
from Infrastructure.DataTypes.FileRepresenters.FileHandling import to_file
from Infrastructure.DataTypes.Types.custome_type import Processor


class Location(Enum):
    Local = 1
    Remote = 2
    Unavailable = 3


class Resolver(ABC):
    @abstractmethod
    def resolve(self):
        pass


class ToolResolver(Resolver):
    def __init__(self, name, path_to_archive, path_to_named_archive, path_to_infra):
        self.name = name
        self.path_to_archive = path_to_archive
        self.path_named_archive = path_to_named_archive
        self.path_to_infra = path_to_infra

    def symbolic_linked(self) -> Optional[str]:
        symbolic_link_file = f"{self.path_named_archive}/symbolic_link"
        symbolic_link_exists = os.path.exists(symbolic_link_file)
        if symbolic_link_exists:
            with open(symbolic_link_file, "r") as f:
                link_target = f.read().strip()
            return os.path.basename(link_target)
        return None

    def resolve(self) -> Optional[Location]:
        symbolic_link_file = f"{self.path_named_archive}/symbolic_link"
        symbolic_link_exists = os.path.exists(symbolic_link_file)
        if symbolic_link_exists:
            with open(symbolic_link_file, "r") as f:
                link_target = f.read().strip()
            name = os.path.basename(link_target)
            path_archive = f"{self.path_to_archive}/{link_target}"
        else:
            name = self.name
            path_archive = self.path_named_archive

        docker_file_exists = os.path.exists(f"{path_archive}/Dockerfile")
        prop_file_exists = os.path.exists(f"{path_archive}/tool.properties")
        if docker_file_exists and prop_file_exists:
            return Location.Local

        if any(tool == name for tool in MonitoringFaceDownloader(self.path_to_infra).get_all_names()):
            return Location.Remote

        return Location.Unavailable


class BenchmarkResolver(Resolver):
    def __init__(self, name, path_to_archive, path_to_infra):
        self.name = name
        self.path_to_archive = path_to_archive
        self.path_to_infra = path_to_infra
        self.data_loader = DataLoader(Processor.Benchmark, path_to_infra=self.path_to_infra)

    def resolve(self) -> Optional[Location]:
        file_exists = os.path.exists(f"{self.path_to_archive}/Benchmarks/{self.name}")
        if file_exists:
            return Location.Local

        if any(tool == self.name for tool in self.data_loader.get_all_names()):
            return Location.Remote

        return Location.Unavailable

    def get_remote_config(self, path_to_archive_benchmark, name):
        os.makedirs(path_to_archive_benchmark, exist_ok=True)

        content = self.data_loader.get_content(name)
        if content is None:
            raise ValueError(f"Cannot fetch Benchmark ({name}) from Repository")
        to_file(path_to_archive_benchmark, content, name=name)


class ProcessorResolver(Resolver):
    def __init__(self, name, processor_type, path_to_archive, path_to_infra):
        self.name = name
        self.processor_type = processor_type
        self.path_archive = path_to_archive
        self.path_named_archive = f"{self.path_archive}/{self.name}"
        self.path_to_infra = path_to_infra

    def symbolic_linked(self) -> Optional[str]:
        symbolic_link_file = f"{self.path_named_archive}/symbolic_link"
        symbolic_link_exists = os.path.exists(symbolic_link_file)
        if symbolic_link_exists:
            with open(symbolic_link_file, "r") as f:
                link_target = f.read().strip()
            return os.path.basename(link_target)
        return None

    def resolve(self) -> Optional[Location]:
        symbolic_link_file = f"{self.path_named_archive}/symbolic_link"
        symbolic_link_exists = os.path.exists(symbolic_link_file)
        if symbolic_link_exists:
            with open(symbolic_link_file, "r") as f:
                link_target = f.read().strip()
            name = os.path.basename(link_target)
            path_archive = f"{self.path_archive}/{name}"
        else:
            name = self.name
            path_archive = self.path_named_archive

        docker_file_exists = os.path.exists(f"{path_archive}/Dockerfile")
        prop_file_exists = os.path.exists(f"{path_archive}/tool.properties")
        # check local
        if docker_file_exists and prop_file_exists:
            return Location.Local

        if any(tool == name for tool in DataLoader(self.processor_type, self.path_to_infra).get_all_names()):
            return Location.Remote

        return Location.Unavailable
