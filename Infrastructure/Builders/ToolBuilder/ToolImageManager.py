import os.path

from Infrastructure.DataLoader import init_repo_fetcher
from Infrastructure.DataLoader.Downloader import MonitoringFaceDownloader
from Infrastructure.DataLoader.Resolver import Location
from Infrastructure.Builders.BuilderUtilities import image_building, run_image, to_prop_file, image_exists, ImageBuildException
from Infrastructure.DataTypes.FileRepresenters.PropertiesHandler import PropertiesHandler
from Infrastructure.DataTypes.Types.custome_type import BranchOrRelease
from Infrastructure.Builders.ToolBuilder.AbstractToolImageManager import AbstractToolImageManager
from Infrastructure.constants import (IMAGE_POSTFIX, BUILD_ARG_GIT_BRANCH, VOLUMES_KEY, COMMAND_KEY, WORKDIR_KEY,
                                      DOCKERFILE_VALUE, DOCKERFILE_KEY, PROP_FILES_VALUE, PROP_FILES_KEY,
                                      META_FILE_VALUE, VERSION_KEY, SYMLINK_KEY)


def to_file(path, name, content):
    with open(path + f"{name}", mode='w') as f:
        f.write(content)


def remote_content_handler(path_to_named_archive, path_to_infra, name):
    content = MonitoringFaceDownloader(path_to_infra).get_content(name)
    if content is None:
        raise ImageBuildException("Cannot fetch data from Repository")

    os.makedirs(path_to_named_archive, exist_ok=True)
    if PROP_FILES_KEY in content and DOCKERFILE_KEY in content:
        to_file(path_to_named_archive, PROP_FILES_VALUE, content[PROP_FILES_KEY])
        to_file(path_to_named_archive, DOCKERFILE_VALUE, content[DOCKERFILE_KEY])
    elif SYMLINK_KEY in content:
        to_file(path_to_named_archive, DOCKERFILE_VALUE, content[DOCKERFILE_KEY])
    else:
        raise ImageBuildException("Incomplete data fetched from Repository")


class IndirectToolImageManager(AbstractToolImageManager):
    def __init__(self, name, linked_name, branch, release, path_to_repo, path_to_archive, path_to_infra, location):
        self.original_name = name
        self.linked_name = linked_name
        self.binary_name = linked_name.lower()
        self.branch = branch
        self.args = {BUILD_ARG_GIT_BRANCH: branch}

        self.named_archive = f"{path_to_archive}/Tools/{self.original_name}"
        self.linked_named_archive = f"{path_to_archive}/Tools/{self.linked_name}"
        self.image_name = f"{self.linked_name.lower()}_{self.branch.lower()}{IMAGE_POSTFIX}"

        self.path_to_infra = path_to_infra
        self.parent_path = f"{path_to_repo}/Monitor/{self.original_name}"
        self.path = f"{self.parent_path}/{self.branch}"

        if location == Location.Remote:
            os.makedirs(self.path, exist_ok=True)
            self._build_image()

        in_build = os.path.exists(f"{self.path}{META_FILE_VALUE}")
        if not in_build:
            self._build_image()
        elif not image_exists(self.image_name):
            # Files exist but Docker image is missing - rebuild it
            print(f"Dockerfile exists but image missing for {self.original_name} - {self.branch}, building...")
            self._build_image()
        else:
            current_version = PropertiesHandler.from_file(f"{self.path}{META_FILE_VALUE}").get_attr(VERSION_KEY)
            fl = PropertiesHandler.from_file(self.linked_named_archive + PROP_FILES_VALUE)
            version = init_repo_fetcher(fl, self.path_to_infra).get_hash(self.branch)
            if not current_version == version:
                if release == BranchOrRelease.Branch:
                    self._build_image()
            else:
                print(f"    Exists {self.original_name} - {branch}")

    def _build_image(self):
        fl = PropertiesHandler.from_file(self.linked_named_archive + PROP_FILES_VALUE)
        version = init_repo_fetcher(fl, self.path_to_infra).get_hash(self.branch)
        to_prop_file(self.path, META_FILE_VALUE, {VERSION_KEY: version})
        return image_building(self.image_name, self.linked_named_archive, self.args)

    def run(self, path_to_data, parameters, time_on=None, time_out=None):
        inner_contract_ = dict()
        inner_contract_[VOLUMES_KEY] = {path_to_data: {'bind': '/data', 'mode': 'rw'}}
        inner_contract_[COMMAND_KEY] = ["/usr/bin/time", "-v", "-o", "scratch/stats.txt"] + [self.binary_name] + parameters
        inner_contract_[WORKDIR_KEY] = "/data"
        return run_image(self.image_name, inner_contract_, time_on, time_out)


class DirectToolImageManager(AbstractToolImageManager):
    def __init__(self, name, branch, release, path_to_build, path_to_archive, path_to_infra, location):
        self.name = name
        self.branch = branch
        self.args = {BUILD_ARG_GIT_BRANCH: branch}
        self.image_name = f"{name.lower()}_{branch.lower()}{IMAGE_POSTFIX}"

        self.named_archive = f"{path_to_archive}/Tools/{name}"
        self.path_to_infra = path_to_infra
        self.parent_path = f"{path_to_build}/Monitor/{self.name}"
        self.path = f"{self.parent_path}/{branch}"

        if location == Location.Remote:
            os.makedirs(self.path, exist_ok=True)
            self._build_image()

        in_build = os.path.exists(f"{self.path}{META_FILE_VALUE}")
        if not in_build:
            self._build_image()
        elif not image_exists(self.image_name):
            # Files exist but Docker image is missing - rebuild it
            print(f"Dockerfile exists but image missing for {self.name} - {self.branch}, building...")
            self._build_image()
        else:
            current_version = PropertiesHandler.from_file(f"{self.path}{META_FILE_VALUE}").get_attr(VERSION_KEY)
            fl = PropertiesHandler.from_file(self.named_archive + PROP_FILES_VALUE)
            version = init_repo_fetcher(fl, self.path_to_infra).get_hash(self.branch)
            if not current_version == version:
                if release == BranchOrRelease.Branch:
                    self._build_image()
            else:
                print(f"    Exists {self.name} - {self.branch}")

    def _build_image(self):
        fl = PropertiesHandler.from_file(self.named_archive + PROP_FILES_VALUE)
        version = init_repo_fetcher(fl, self.path_to_infra).get_hash(self.branch)
        os.makedirs(self.path, exist_ok=True)
        to_prop_file(self.path, META_FILE_VALUE, {VERSION_KEY: version})
        return image_building(self.image_name, self.named_archive, self.args)

    def run(self, path_to_data, parameters, time_on=None, time_out=None):
        inner_contract_ = dict()
        inner_contract_[VOLUMES_KEY] = {path_to_data: {'bind': '/data', 'mode': 'rw'}}
        inner_contract_[COMMAND_KEY] = ["/usr/bin/time", "-v", "-o", "scratch/stats.txt"] + [self.name.lower()] + parameters
        inner_contract_[WORKDIR_KEY] = "/data"
        return run_image(self.image_name, inner_contract_, time_on, time_out)
