import os.path

from Infrastructure.DataLoader import init_repo_fetcher
from Infrastructure.DataLoader.Downloader import MonitoringFaceDownloader
from Infrastructure.DataLoader.Resolver import ToolResolver, Location
from Infrastructure.Builders.BuilderUtilities import image_building, run_image, image_exists
from Infrastructure.DataTypes.FileRepresenters.PropertiesHandler import PropertiesHandler
from Infrastructure.Monitors.MonitorExceptions import BuildException
from Infrastructure.Builders.ToolBuilder.AbstractToolImageManager import AbstractToolImageManager
from Infrastructure.constants import IMAGE_POSTFIX, BUILD_ARG_GIT_BRANCH, VOLUMES_KEY, COMMAND_KEY, WORKDIR_KEY


def to_file(path, name, content):
    with open(path + f"{name}", mode='w') as f:
        f.write(content)


def to_prop_file(path, name, content: dict):
    with open(path + f"{name}", mode='w') as f:
        for (k, v) in content.items():
            f.write(f"{k}={v}\n")


class ToolImageManager(AbstractToolImageManager):
    def __init__(self, name, branch, release, path_to_repo):
        self.name = name
        self.branch = branch
        self.release = release
        self.image_name = f"{self.name.lower()}_{self.branch.lower()}{IMAGE_POSTFIX}"

        path_to_monitor = f"{path_to_repo}/Monitor"
        if not os.path.exists(path_to_monitor):
            os.mkdir(path_to_monitor)

        self.parent_path = f"{path_to_repo}/Monitor/{self.name}"
        self.path = f"{self.parent_path}/{self.branch}"
        self.args = {BUILD_ARG_GIT_BRANCH: branch}

        self.location = ToolResolver(self.name, self.branch, self.path).resolve()
        if self.location == Location.Unavailable:
            raise BuildException(f"{self.name} does not exists either Local or Remote")

        if not os.path.exists(self.parent_path):
            # tool is remote
            os.mkdir(self.parent_path)
            os.mkdir(self.path)
            self._build_image()
        elif not os.path.exists(self.path):
            # branch is remote
            os.mkdir(self.path)
            self._build_image()
        else:
            # tool and branch are either local or previously downloaded
            prop_file_exists = os.path.exists(self.path + "/tool.properties")
            docker_file_exists = os.path.exists(self.path + "/Dockerfile")
            if not (prop_file_exists and docker_file_exists):
                self._build_image()
            elif not image_exists(self.image_name):
                # Files exist but Docker image is missing - rebuild it
                print(f"Dockerfile exists but image missing for {self.name} - {self.branch}, building...")
                self._build_image()
            else:
                print(f"Exists {self.name} - {self.branch}")

    def _build_image(self):
        if self.location == Location.Remote:
            content = MonitoringFaceDownloader().get_content(self.name)
            if content is None:
                raise BuildException("Cannot fetch data from Repository")
            to_file(self.path, "/tool.properties", content["tool.properties"])
            fl = PropertiesHandler.from_file(self.path + f"/tool.properties")
            version = init_repo_fetcher(fl.get_attr("git"), fl.get_attr("owner"), fl.get_attr("repo")).get_hash(self.branch)
            to_file(self.path, "/Dockerfile", content["Dockerfile"])
            to_prop_file(self.path, "/meta.properties", {"version": version})
        return image_building(self.image_name, self.path, self.args)

    def run(self, path_to_data, parameters, time_on=None, time_out=None):
        inner_contract_ = dict()
        inner_contract_[VOLUMES_KEY] = {path_to_data: {'bind': '/data', 'mode': 'rw'}}
        inner_contract_[COMMAND_KEY] = ["/usr/bin/time", "-v", "-o", "scratch/stats.txt"] + [self.name.lower()] + parameters
        inner_contract_[WORKDIR_KEY] = "/data"
        return run_image(self.image_name, inner_contract_, time_on, time_out)
