import os
from typing import AnyStr, Dict, Any

from Infrastructure.DataLoader import init_repo_fetcher
from Infrastructure.DataLoader.DataLoader import DataLoader
from Infrastructure.DataLoader.Resolver import ProcessorResolver, Location
from Infrastructure.DataTypes.FileRepresenters.PropertiesHandler import PropertiesHandler
from Infrastructure.DataTypes.Types.custome_type import Processor, processor_to_identifier
from Infrastructure.Builders.ProcessorBuilder.AbstractImageManager import AbstractImageManager
from Infrastructure.Builders.BuilderUtilities import image_exists, image_building, run_image, to_prop_file, ImageBuildException
from Infrastructure.Monitors.MonitorExceptions import BuildException
from Infrastructure.constants import IMAGE_POSTFIX, VERSION_KEY, META_FILE_VALUE, PROP_FILES_VALUE, BRANCH_KEY, DOCKERFILE_VALUE


def to_file(file, content):
    with open(file, "w") as f:
        f.write(content)


def remote_content_handler(downloader, path_named_archive, name):
    content = downloader.get_content(name)
    if content is None:
        raise BuildException("Cannot fetch data from Repository")
    to_file(path_named_archive + DOCKERFILE_VALUE, content)


class ImageManager(AbstractImageManager):
    def __init__(self, name, proc: Processor, path_to_project_inner):
        super().__init__()
        self.name = name
        self.proc = proc
        self.identifier = processor_to_identifier(proc)
        self.path = path_to_project_inner + "/Infrastructure/build"
        self.path_to_infra = path_to_project_inner + "/Infrastructure"
        self.downloader = DataLoader(proc, self.path_to_infra)
        self.path_to_archive = f"{path_to_project_inner}/Archive/{self.identifier}"
        self.path_named_archive = path_to_project_inner + f"/Archive/{self.identifier}/{self.name}"

        pr = ProcessorResolver(self.name, self.proc, self.path_to_archive, self.path_to_infra)
        self.location = pr.resolve()

        self.path_to_build = f"{self.path}/{self.identifier}/{self.name}"
        os.makedirs(self.path_to_build, exist_ok=True)
        os.makedirs(self.path_named_archive, exist_ok=True)

        if self.location == Location.Unavailable:
            raise BuildException(f"{self.identifier} - {self.name} does not exists either Local or Remote")
        elif self.location == Location.Remote:
            remote_content_handler(self.downloader, self.path_named_archive, self.name)

        linked = pr.symbolic_linked()
        self.image_name = f"{linked.lower() if linked else name.lower()}_{self.identifier.lower()}{IMAGE_POSTFIX}"
        if linked:
            new_path_to_named_archive = f"{self.path_to_archive}/{linked}"
            new_tl = ProcessorResolver(linked, self.proc, self.path_to_archive, self.path_to_infra)
            new_location = new_tl.resolve()
            self.linked_location = new_location
            if new_location == Location.Unavailable:
                raise ImageBuildException(f"Linked {linked} does not exists either Local or Remote")
            elif new_location == Location.Remote:
                remote_content_handler(self.downloader, new_path_to_named_archive, linked)

        if not linked:
            if self.location == Location.Local:
                in_build = os.path.exists(f"{self.path_to_build}{META_FILE_VALUE}")
                if not in_build:
                    self._build_image()
                else:
                    current_version = PropertiesHandler.from_file(self.path_to_build + META_FILE_VALUE).get_attr(VERSION_KEY)
                    fl = PropertiesHandler.from_file(self.path_named_archive + PROP_FILES_VALUE)
                    version = init_repo_fetcher(fl, self.path_to_infra).get_hash(fl.get_attr(BRANCH_KEY))
                    if not image_exists(self.image_name):
                        self._build_image()
                    elif not current_version == version:
                        self._build_image()
                    else:
                        print(f"    Exists {self.identifier} - {self.name}")
            else:
                self._build_image()
        else:
            path_to_linked_archive = f"{self.path_to_archive}/{linked}"
            if self.linked_location == Location.Local:
                in_build = os.path.exists(f"{self.path_to_build}{META_FILE_VALUE}")
                if not in_build:
                    self._build_linked_image(path_to_linked_archive, self.image_name)
                else:
                    current_version = PropertiesHandler.from_file(self.path_to_build + META_FILE_VALUE).get_attr(VERSION_KEY)
                    fl = PropertiesHandler.from_file(path_to_linked_archive + PROP_FILES_VALUE)
                    version = init_repo_fetcher(fl, self.path_to_infra).get_hash(fl.get_attr(BRANCH_KEY))

                    if not image_exists(self.image_name):
                        self._build_linked_image(path_to_linked_archive, self.image_name)
                    elif not current_version == version:
                        self._build_linked_image(path_to_linked_archive, self.image_name)
                    else:
                        print(f"    Exists {self.identifier} - {self.name}")
            else:
                self._build_linked_image(path_to_linked_archive, self.image_name)

    def _build_image(self):
        fl = PropertiesHandler.from_file(self.path_named_archive + PROP_FILES_VALUE)
        version = init_repo_fetcher(fl, self.path_to_infra).get_hash(fl.get_attr(BRANCH_KEY))
        to_prop_file(f"{self.path}/{self.identifier}/{self.name}", META_FILE_VALUE, {VERSION_KEY: version})
        return image_building(self.image_name, self.path_named_archive)

    def _build_linked_image(self, path_to_linked_archive, image_name):
        fl = PropertiesHandler.from_file(path_to_linked_archive + PROP_FILES_VALUE)
        version = init_repo_fetcher(fl, self.path_to_infra).get_hash(fl.get_attr(BRANCH_KEY))
        to_prop_file(f"{self.path}/{self.identifier}/{self.name}", META_FILE_VALUE, {VERSION_KEY: version})
        return image_building(image_name, path_to_linked_archive)

    def run(self, generic_contract: Dict[AnyStr, Any], time_on=None, time_out=None):
        return run_image(image_name=self.image_name, generic_contract=generic_contract, time_on=time_on, time_out=time_out)
