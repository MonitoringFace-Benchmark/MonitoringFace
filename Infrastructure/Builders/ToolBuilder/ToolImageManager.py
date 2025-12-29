import os.path

from Infrastructure.DataLoader import init_repo_fetcher
from Infrastructure.DataLoader.Downloader import MonitoringFaceDownloader
from Infrastructure.DataLoader.Resolver import ToolResolver, Location
from Infrastructure.Builders.BuilderUtilities import image_building, run_image, to_prop_file, image_exists
from Infrastructure.DataTypes.FileRepresenters.PropertiesHandler import PropertiesHandler
from Infrastructure.DataTypes.Types.custome_type import BranchOrRelease
from Infrastructure.Monitors.MonitorExceptions import BuildException
from Infrastructure.Builders.ToolBuilder.AbstractToolImageManager import AbstractToolImageManager
from Infrastructure.constants import (IMAGE_POSTFIX, BUILD_ARG_GIT_BRANCH, VOLUMES_KEY, COMMAND_KEY, WORKDIR_KEY,
                                      DOCKERFILE_VALUE, DOCKERFILE_KEY, PROP_FILES_VALUE, PROP_FILES_KEY, META_FILE_VALUE,
                                      GIT_KEY, OWNER_KEY, REPO_KEY, VERSION_KEY)


def to_file(path, name, content):
    with open(path + f"{name}", mode='w') as f:
        f.write(content)


class ToolImageManager(AbstractToolImageManager):
    def __init__(self, name, branch, release, path_to_repo, path_to_archive, path_to_infra):
        self.name = name
        self.branch = branch
        self.release = release
        self.path_to_archive = f"{path_to_archive}/Tools/{self.name}"
        self.path_to_infra = path_to_infra
        self.image_name = f"{self.name.lower()}_{self.branch.lower()}{IMAGE_POSTFIX}"

        path_to_monitor = f"{path_to_repo}/Monitor"
        os.makedirs(path_to_monitor, exist_ok=True)

        self.parent_path = f"{path_to_repo}/Monitor/{self.name}"
        os.makedirs(self.parent_path, exist_ok=True)

        self.path = f"{self.parent_path}/{self.branch}"
        os.makedirs(self.path, exist_ok=True)

        self.args = {BUILD_ARG_GIT_BRANCH: branch}

        self.location = ToolResolver(self.name, self.branch, self.path, self.path_to_archive, self.path_to_infra).resolve()
        if self.location == Location.Unavailable:
            raise BuildException(f"{self.name} does not exists either Local or Remote")
        elif self.location == Location.Local:
            in_build = os.path.exists(f"{self.path}{META_FILE_VALUE}")
            if not in_build:
                self._build_image()
            elif not image_exists(self.image_name):
                # Files exist but Docker image is missing - rebuild it
                print(f"Dockerfile exists but image missing for {self.name} - {self.branch}, building...")
                self._build_image()
            else:
                current_version = PropertiesHandler.from_file(f"{self.path}{META_FILE_VALUE}").get_attr(VERSION_KEY)
                fl = PropertiesHandler.from_file(self.path_to_archive + PROP_FILES_VALUE)
                version = init_repo_fetcher(fl.get_attr(GIT_KEY), fl.get_attr(OWNER_KEY),
                                            fl.get_attr(REPO_KEY), self.path_to_infra).get_hash(self.branch)
                if not image_exists(self.image_name):
                    self._build_image()
                elif not current_version == version:
                    if release == BranchOrRelease.Branch:
                        self._build_image()
                else:
                    print(f"    Exists {self.name} - {self.branch}")
        else:
            os.makedirs(self.path_to_archive, exist_ok=True)
            os.makedirs(self.path, exist_ok=True)
            self._build_image()

    def _build_image(self):
        if self.location == Location.Remote:
            content = MonitoringFaceDownloader().get_content(self.name)
            if content is None:
                raise BuildException("Cannot fetch data from Repository")
            to_file(self.path_to_archive, PROP_FILES_VALUE, content[PROP_FILES_KEY])
            to_file(self.path_to_archive, DOCKERFILE_VALUE, content[DOCKERFILE_KEY])
        fl = PropertiesHandler.from_file(self.path_to_archive + PROP_FILES_VALUE)
        version = init_repo_fetcher(fl.get_attr(GIT_KEY), fl.get_attr(OWNER_KEY),
                                    fl.get_attr(REPO_KEY), self.path_to_infra).get_hash(self.branch)
        to_prop_file(self.path, META_FILE_VALUE, {VERSION_KEY: version})
        return image_building(self.image_name, self.path_to_archive, self.args)

    def run(self, path_to_data, parameters, time_on=None, time_out=None):
        inner_contract_ = dict()
        inner_contract_[VOLUMES_KEY] = {path_to_data: {'bind': '/data', 'mode': 'rw'}}
        inner_contract_[COMMAND_KEY] = ["/usr/bin/time", "-v", "-o", "scratch/stats.txt"] + [self.name.lower()] + parameters
        inner_contract_[WORKDIR_KEY] = "/data"
        return run_image(self.image_name, inner_contract_, time_on, time_out)
