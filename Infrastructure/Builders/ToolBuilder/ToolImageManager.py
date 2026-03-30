import os.path
from typing import Optional

from Infrastructure.Frontend.CLI.cli_args import CLIArgs
from Infrastructure.DataLoader import init_repo_fetcher
from Infrastructure.DataLoader.Downloader import MonitoringFaceDownloader
from Infrastructure.DataLoader.Resolver import Location
from Infrastructure.Builders.BuilderUtilities import image_building, run_image_offline, to_prop_file, image_exists, ImageBuildException
from Infrastructure.DataTypes.FileRepresenters.PropertiesHandler import PropertiesHandler
from Infrastructure.DataTypes.Types.custome_type import BranchOrRelease, OnlineOffline
from Infrastructure.Builders.ToolBuilder.AbstractToolImageManager import AbstractToolImageManager
from Infrastructure.constants import (IMAGE_POSTFIX, BUILD_ARG_GIT_BRANCH, VOLUMES_KEY, COMMAND_KEY, WORKDIR_KEY,
                                      DOCKERFILE_VALUE, DOCKERFILE_KEY, PROP_FILES_VALUE, PROP_FILES_KEY,
                                      META_FILE_VALUE, VERSION_KEY, SYMLINK_KEY, BUILD_ARG_GIT_COMMIT)


def to_file(path, name, content):
    with open(path + f"{name}", mode='w') as f:
        f.write(content)


def remote_content_handler(path_to_named_archive, path_to_infra, name, interaction: Optional[OnlineOffline] = None):
    content = MonitoringFaceDownloader(path_to_infra).get_content(name)
    if content is None:
        raise ImageBuildException("Cannot fetch data from Repository")

    os.makedirs(path_to_named_archive, exist_ok=True)

    docker_file_location = f"{path_to_named_archive}/{interaction}" if interaction else path_to_named_archive
    if PROP_FILES_KEY in content and DOCKERFILE_KEY in content:
        to_file(path_to_named_archive, PROP_FILES_VALUE, content[PROP_FILES_KEY])
        to_file(docker_file_location, DOCKERFILE_VALUE, content[DOCKERFILE_KEY])
    elif SYMLINK_KEY in content:
        to_file(docker_file_location, DOCKERFILE_VALUE, content[DOCKERFILE_KEY])
    else:
        raise ImageBuildException("Incomplete data fetched from Repository")


class IndirectToolImageManager(AbstractToolImageManager):
    def __init__(self, name, linked_name, branch, commit, release, path_to_repo, path_to_archive, path_to_infra, location, cli_args: CLIArgs, runtime_setting: OnlineOffline):
        self.original_name = name
        self.runtime_setting = runtime_setting
        self.linked_name = linked_name
        self.binary_name = linked_name.lower()
        self.cli_args = cli_args
        self.branch = branch
        self.commit = commit
        self.args = {BUILD_ARG_GIT_BRANCH: branch, BUILD_ARG_GIT_COMMIT: commit} if commit else {BUILD_ARG_GIT_BRANCH: branch}

        self.named_archive = f"{path_to_archive}/Tools/{self.original_name}"
        self.linked_named_archive = f"{path_to_archive}/Tools/{self.linked_name}"
        self.image_name = f"{self.linked_name.lower()}_{commit}_{runtime_setting.to_string()}{IMAGE_POSTFIX}" if commit else f"{self.linked_name.lower()}_{self.branch.lower()}_{runtime_setting.to_string()}{IMAGE_POSTFIX}"

        self.path_to_infra = path_to_infra
        self.parent_path = f"{path_to_repo}/Monitor/{self.original_name}"
        self.path = f"{self.parent_path}/{self.commit}" if commit else f"{self.parent_path}/{self.branch}"

        if location == Location.Remote:
            os.makedirs(self.path, exist_ok=True)
            self._build_image()

        in_build = os.path.exists(f"{self.path}{META_FILE_VALUE}")
        os.makedirs(self.path, exist_ok=True)
        if not in_build:
            self._build_image()
        elif not image_exists(self.image_name):
            if self.commit:
                print(f"Dockerfile exists but image missing for {self.original_name} - {self.commit}, building...")
            else:
                print(f"Dockerfile exists but image missing for {self.original_name} - {self.branch}, building...")
            self._build_image()
        else:
            current_version = PropertiesHandler.from_file(f"{self.path}{META_FILE_VALUE}").get_attr(VERSION_KEY)
            if commit:
                version = commit
            else:
                fl = PropertiesHandler.from_file(self.linked_named_archive + PROP_FILES_VALUE)
                version = init_repo_fetcher(fl, self.path_to_infra).get_hash(self.branch)

            if not current_version == version:
                if release == BranchOrRelease.Branch:
                    self._build_image()
            else:
                if self.commit:
                    print(f"    Exists {self.original_name} - {self.commit}")
                else:
                    print(f"    Exists {self.original_name} - {self.branch}")

    def get_image_name(self) -> str:
        return self.image_name

    def get_cli_args(self) -> CLIArgs:
        return self.cli_args

    def _build_image(self):
        if self.commit:
            to_prop_file(self.path, META_FILE_VALUE, {VERSION_KEY: self.commit})
        else:
            fl = PropertiesHandler.from_file(self.linked_named_archive + PROP_FILES_VALUE)
            version = init_repo_fetcher(fl, self.path_to_infra).get_hash(self.branch)
            to_prop_file(self.path, META_FILE_VALUE, {VERSION_KEY: version})
        return image_building(self.image_name, f"{self.linked_named_archive}/{self.runtime_setting.to_string()}", self.args)

    def run_offline(self, path_to_data, parameters, time_on=None, time_out=None, measure=True, name=None):
        inner_contract_ = dict()
        inner_contract_[VOLUMES_KEY] = {path_to_data: {'bind': '/data', 'mode': 'rw'}}

        inner_name = name if name is not None else self.binary_name
        if measure and self.cli_args.measure:
            tool_cmd = " ".join([inner_name] + parameters)
            inner_contract_[COMMAND_KEY] = ["/bin/sh", "-c",
                                            f"mkdir -p /data/scratch && /usr/bin/time -v -o /tmp/stats.txt {tool_cmd}; "
                                            f"e=$?; cp /tmp/stats.txt /data/scratch/stats.txt 2>/dev/null; exit $e"]
        else:
            inner_contract_[COMMAND_KEY] = [inner_name] + parameters
        inner_contract_[WORKDIR_KEY] = "/data"
        return run_image_offline(self.image_name, inner_contract_, verbose=self.cli_args.verbose, time_on=time_on, time_out=time_out, is_tool_image=True)


class DirectToolImageManager(AbstractToolImageManager):
    def __init__(self, name, branch, release, commit, path_to_build, path_to_archive, path_to_infra, location, cli_args: CLIArgs, runtime_setting: OnlineOffline):
        self.name = name
        self.runtime_setting = runtime_setting
        self.commit = commit
        self.branch = branch
        self.cli_args = cli_args
        self.args = {BUILD_ARG_GIT_BRANCH: branch, BUILD_ARG_GIT_COMMIT: commit} if commit else {BUILD_ARG_GIT_BRANCH: branch}
        self.image_name = f"{name.lower()}_{commit}_{runtime_setting.to_string()}{IMAGE_POSTFIX}" if commit else f"{name.lower()}_{branch.lower()}_{runtime_setting.to_string()}{IMAGE_POSTFIX}"

        self.named_archive = f"{path_to_archive}/Tools/{name}"
        self.path_to_infra = path_to_infra
        self.parent_path = f"{path_to_build}/Monitor/{self.name}"
        self.path = f"{self.parent_path}/{commit}" if commit else f"{self.parent_path}/{branch}"

        if location == Location.Remote:
            os.makedirs(self.path, exist_ok=True)
            self._build_image()

        in_build = os.path.exists(f"{self.path}{META_FILE_VALUE}")
        if not in_build:
            self._build_image()
        elif not image_exists(self.image_name):
            if self.commit:
                print(f"Dockerfile exists but image missing for {self.name} - {self.commit}, building...")
            else:
                print(f"Dockerfile exists but image missing for {self.name} - {self.branch}, building...")
            self._build_image()
        else:
            current_version = PropertiesHandler.from_file(f"{self.path}{META_FILE_VALUE}").get_attr(VERSION_KEY)
            if commit:
                version = commit
            else:
                fl = PropertiesHandler.from_file(self.named_archive + PROP_FILES_VALUE)
                version = init_repo_fetcher(fl, self.path_to_infra).get_hash(self.branch)
            if not current_version == version:
                if release == BranchOrRelease.Branch:
                    self._build_image()
            else:
                if commit:
                    print(f"    Exists {self.name} - {self.commit}")
                else:
                    print(f"    Exists {self.name} - {self.branch}")

    def get_image_name(self) -> str:
        return self.image_name

    def get_cli_args(self) -> CLIArgs:
        return self.cli_args

    def _build_image(self):
        os.makedirs(self.path, exist_ok=True)
        if self.commit:
            to_prop_file(self.path, META_FILE_VALUE, {VERSION_KEY: self.commit})
        else:
            fl = PropertiesHandler.from_file(self.named_archive + PROP_FILES_VALUE)
            version = init_repo_fetcher(fl, self.path_to_infra).get_hash(self.branch)
            to_prop_file(self.path, META_FILE_VALUE, {VERSION_KEY: version})
        return image_building(self.image_name, f"{self.named_archive}/{self.runtime_setting.to_string()}", self.args)

    def run_offline(self, path_to_data, parameters, time_on=None, time_out=None, measure=True, name=None):
        inner_contract_ = dict()
        inner_contract_[VOLUMES_KEY] = {path_to_data: {'bind': '/data', 'mode': 'rw'}}
        inner_name = name if name is not None else self.name.lower()
        if measure and self.cli_args.measure:
            tool_cmd = " ".join([inner_name] + parameters)
            inner_contract_[COMMAND_KEY] = ["/bin/sh", "-c",
                                            f"mkdir -p /data/scratch && /usr/bin/time -v -o /tmp/stats.txt {tool_cmd}; "
                                            f"e=$?; cp /tmp/stats.txt /data/scratch/stats.txt 2>/dev/null; exit $e"]
        else:
            inner_contract_[COMMAND_KEY] = [inner_name] + parameters
        inner_contract_[WORKDIR_KEY] = "/data"
        return run_image_offline(self.image_name, inner_contract_, verbose=self.cli_args.verbose, time_on=time_on, time_out=time_out, is_tool_image=True)
