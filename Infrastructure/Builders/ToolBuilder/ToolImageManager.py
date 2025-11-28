import os.path

from Infrastructure.DataLoader import init_repo_fetcher
from Infrastructure.DataLoader.Downloader import MonitoringFaceDownloader
from Infrastructure.DataLoader.Resolver import ToolResolver, Location
from Infrastructure.Builders.BuilderUtilities import image_building, run_image, to_prop_file
from Infrastructure.DataTypes.FileRepresenters.PropertiesHandler import PropertiesHandler
from Infrastructure.Monitors.MonitorExceptions import BuildException
from Infrastructure.Builders.ToolBuilder.AbstractToolImageManager import AbstractToolImageManager
from Infrastructure.constants import IMAGE_POSTFIX, BUILD_ARG_GIT_BRANCH, VOLUMES_KEY, COMMAND_KEY, WORKDIR_KEY


def to_file(path, name, content):
    with open(path + f"{name}", mode='w') as f:
        f.write(content)


class ToolImageManager(AbstractToolImageManager):
    def __init__(self, name, branch, release, path_to_repo, path_to_archive):
        self.name = name
        self.branch = branch
        self.release = release
        self.path_to_archive = f"{path_to_archive}/Tools/{self.name}"
        self.image_name = f"{self.name.lower()}_{self.branch.lower()}{IMAGE_POSTFIX}"

        path_to_monitor = f"{path_to_repo}/Monitor"
        if not os.path.exists(path_to_monitor):
            os.mkdir(path_to_monitor)

        self.parent_path = f"{path_to_repo}/Monitor/{self.name}"
        self.path = f"{self.parent_path}/{self.branch}"
        self.args = {BUILD_ARG_GIT_BRANCH: branch}

        self.location = ToolResolver(self.name, self.branch, self.path, self.path_to_archive).resolve()
        if self.location == Location.Unavailable:
            raise BuildException(f"{self.name} does not exists either Local or Remote")
        elif self.location == Location.Local:
            in_build = os.path.exists(f"{self.path}/meta.properties")
            if not in_build:
                self._build_image()
            else:
                current_version = PropertiesHandler.from_file(f"{self.path}/meta.properties").get_attr("version")
                fl = PropertiesHandler.from_file(self.path_to_archive + f"/tool.properties")
                version = init_repo_fetcher(fl.get_attr("git"), fl.get_attr("owner"), fl.get_attr("repo")).get_hash(self.branch)
                if not current_version == version:
                    self._build_image()
                else:
                    print(f"Exists {self.name} - {self.branch}")
        else:
            if not os.path.exists(self.path_to_archive):
                os.mkdir(self.path_to_archive)
            if not os.path.exists(self.parent_path):
                # tool is remote
                os.mkdir(self.parent_path)
                os.mkdir(self.path)
                self._build_image()
            elif not os.path.exists(self.path):
                # branch is remote
                os.mkdir(self.path)
                self._build_image()

    def _build_image(self):
        if self.location == Location.Remote:
            content = MonitoringFaceDownloader().get_content(self.name)
            if content is None:
                raise BuildException("Cannot fetch data from Repository")
            to_file(self.path_to_archive, "/tool.properties", content["tool.properties"])
            fl = PropertiesHandler.from_file(self.path_to_archive + f"/tool.properties")
            to_file(self.path_to_archive, "/Dockerfile", content["Dockerfile"])
            version = init_repo_fetcher(fl.get_attr("git"), fl.get_attr("owner"), fl.get_attr("repo")).get_hash(self.branch)
            to_prop_file(self.path, "/meta.properties", {"version": version})
        return image_building(self.image_name, self.path_to_archive, self.args)

    def run(self, path_to_data, parameters, time_on=None, time_out=None):
        inner_contract_ = dict()
        inner_contract_[VOLUMES_KEY] = {path_to_data: {'bind': '/data', 'mode': 'rw'}}
        inner_contract_[COMMAND_KEY] = ["/usr/bin/time", "-v", "-o", "scratch/stats.txt"] + [self.name.lower()] + parameters
        inner_contract_[WORKDIR_KEY] = "/data"
        return run_image(self.image_name, inner_contract_, time_on, time_out)
