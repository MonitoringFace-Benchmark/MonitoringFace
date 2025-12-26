import os
from typing import AnyStr, Dict, Any

from Infrastructure.DataLoader import init_repo_fetcher
from Infrastructure.DataLoader.DataLoader import DataLoader
from Infrastructure.DataLoader.Resolver import ProcessorResolver, Location
from Infrastructure.DataTypes.FileRepresenters.PropertiesHandler import PropertiesHandler
from Infrastructure.DataTypes.Types.custome_type import Processor, processor_to_identifier
from Infrastructure.Builders.ProcessorBuilder.AbstractImageManager import AbstractImageManager
from Infrastructure.Builders.BuilderUtilities import image_exists, image_building, run_image, to_prop_file
from Infrastructure.Monitors.MonitorExceptions import BuildException
from Infrastructure.constants import (IMAGE_POSTFIX, VERSION_KEY, META_FILE_VALUE, PROP_FILES_VALUE,
                                      GIT_KEY, OWNER_KEY, BRANCH_KEY, REPO_KEY, DOCKERFILE_VALUE)


def to_file(file, content):
    with open(file, "w") as f:
        f.write(content)


class ImageManager(AbstractImageManager):
    def __init__(self, name, proc: Processor, path_to_project_inner):
        super().__init__()
        self.downloader = DataLoader(proc)
        self.name = name
        self.processor = proc
        self.identifier = processor_to_identifier(proc)
        self.path = path_to_project_inner + "/Infrastructure/build"
        self.path_to_infra = path_to_project_inner + "/Infrastructure"
        self.path_archive = path_to_project_inner + f"/Archive/{self.identifier}/{self.name}"
        self.image_name = f"{name.lower()}_{self.identifier.lower()}{IMAGE_POSTFIX}"

        self.location = ProcessorResolver(self.name, self.path_archive, self.processor, self.path_archive).resolve()
        if not os.path.exists(f"{self.path}/{self.identifier}"):
            os.mkdir(f"{self.path}/{self.identifier}")

        self.path_to_build = f"{self.path}/{self.identifier}/{self.name}"
        if not os.path.exists(self.path_to_build):
            os.mkdir(self.path_to_build)

        if self.location == Location.Unavailable:
            raise BuildException(f"{self.identifier} - {self.name} does not exists either Local or Remote")
        elif self.location == Location.Local:
            in_build = os.path.exists(f"{self.path_to_build}{META_FILE_VALUE}")
            if not in_build:
                self._build_image()
            else:
                current_version = PropertiesHandler.from_file(self.path_to_build + META_FILE_VALUE).get_attr(VERSION_KEY)
                fl = PropertiesHandler.from_file(self.path_archive + PROP_FILES_VALUE)
                version = init_repo_fetcher(fl.get_attr(GIT_KEY), fl.get_attr(OWNER_KEY),
                                            fl.get_attr(REPO_KEY), self.path_to_infra).get_hash(fl.get_attr(BRANCH_KEY))
                if not image_exists(self.image_name):
                    self._build_image()
                elif not current_version == version:
                    self._build_image()
                else:
                    print(f"    Exists {self.identifier} - {self.name}")
        else:
            if not os.path.exists(self.path_archive):
                os.mkdir(self.path_archive)
            parent_path = self.path + f"/{self.identifier}"
            child_path = parent_path + f"/{self.name}"
            if not os.path.exists(parent_path):
                os.mkdir(parent_path)
            if not os.path.exists(child_path):
                os.mkdir(child_path)
                self._build_image()

    def _build_image(self):
        if self.location == Location.Remote:
            content = self.downloader.get_content(self.name)
            if content is None:
                raise BuildException("Cannot fetch data from Repository")
            to_file(self.path_archive + DOCKERFILE_VALUE, content)
        fl = PropertiesHandler.from_file(self.path_archive + PROP_FILES_VALUE)
        version = init_repo_fetcher(fl.get_attr(GIT_KEY), fl.get_attr(OWNER_KEY),
                                    fl.get_attr(REPO_KEY), self.path_to_infra).get_hash(fl.get_attr(BRANCH_KEY))
        to_prop_file(f"{self.path}/{self.identifier}/{self.name}", META_FILE_VALUE, {VERSION_KEY: version})
        return image_building(self.image_name, self.path_archive)

    def run(self, generic_contract: Dict[AnyStr, Any], time_on=None, time_out=None):
        return run_image(image_name=self.image_name, generic_contract=generic_contract, time_on=time_on, time_out=time_out)
