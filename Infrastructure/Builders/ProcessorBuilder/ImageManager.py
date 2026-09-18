import os
from typing import AnyStr, Dict, Any

from Infrastructure.DataLoader import init_repo_fetcher
from Infrastructure.DataLoader.DataLoader import DataLoader
from Infrastructure.DataLoader.Resolver import ProcessorResolver, Location
from Infrastructure.DataTypes.FileRepresenters.PropertiesHandler import PropertiesHandler
from Infrastructure.DataTypes.Types.custome_type import Processor, processor_to_identifier
from Infrastructure.Builders.ProcessorBuilder.AbstractImageManager import AbstractImageManager
from Infrastructure.Builders.ProcessorBuilder.ComponentPins import get_pin, docker_ref
from Infrastructure.Builders.BuilderUtilities import image_exists, image_building, run_offline_image, to_prop_file, ImageBuildException
from Infrastructure.Monitors.MonitorExceptions import BuildException
from Infrastructure.constants import IMAGE_POSTFIX, VERSION_KEY, META_FILE_VALUE, PROP_FILES_VALUE, BRANCH_KEY, \
    DOCKERFILE_VALUE, BUILD_ARG_GIT_BRANCH, BUILD_ARG_GIT_COMMIT


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
        self.path_to_archive = f"{path_to_project_inner}/Archive/Docker/{self.identifier}"
        self.path_named_archive = path_to_project_inner + f"/Archive/Docker/{self.identifier}/{self.name}"

        pr = ProcessorResolver(self.name, self.proc, self.path_to_archive, self.path_to_infra)
        self.location = pr.resolve()

        os.makedirs(self.path_named_archive, exist_ok=True)

        if self.location == Location.Unavailable:
            raise BuildException(f"{self.identifier} - {self.name} does not exists either Local or Remote")
        elif self.location == Location.Remote:
            remote_content_handler(self.downloader, self.path_named_archive, self.name)

        linked = pr.symbolic_linked()
        if linked:
            self._build_archive = f"{self.path_to_archive}/{linked}"
            new_tl = ProcessorResolver(linked, self.proc, self.path_to_archive, self.path_to_infra)
            effective_location = new_tl.resolve()
            if effective_location == Location.Unavailable:
                raise ImageBuildException(f"Linked {linked} does not exists either Local or Remote")
            elif effective_location == Location.Remote:
                remote_content_handler(self.downloader, self._build_archive, linked)
        else:
            self._build_archive = self.path_named_archive
            effective_location = self.location

        self.pin_branch, self.pin_commit = get_pin(self.name, linked)

        props_file = self._build_archive + PROP_FILES_VALUE
        props_branch = None
        if os.path.exists(props_file):
            props_branch = PropertiesHandler.from_file(props_file).get_attr(BRANCH_KEY)
        self.branch = self.pin_branch or props_branch

        ref = docker_ref(self.pin_commit or self.branch or "unversioned")
        base = (linked or name).lower()
        self.image_name = f"{base}_{self.identifier.lower()}_{ref}{IMAGE_POSTFIX}"
        self.path_to_build = f"{self.path}/{self.identifier}/{self.name}/{ref}"
        os.makedirs(self.path_to_build, exist_ok=True)

        if self.pin_commit:
            self.build_args = {BUILD_ARG_GIT_BRANCH: self.branch, BUILD_ARG_GIT_COMMIT: self.pin_commit}
        else:
            self.build_args = {BUILD_ARG_GIT_BRANCH: self.branch}

        self.resolved_version = None
        self._ensure_image(effective_location, props_file)

    def _ensure_image(self, effective_location, props_file):
        if self.pin_commit:
            version = self.pin_commit
        else:
            version = None
            if os.path.exists(props_file) and self.branch:
                fl = PropertiesHandler.from_file(props_file)
                version = init_repo_fetcher(fl, self.path_to_infra).get_hash(self.branch)
            if self.pin_branch is None:
                print(f"    WARNING: {self.identifier} - {self.name} is unpinned; tracking "
                      f"{self.branch}@{version} (add a components: entry to pin it)")
        self.resolved_version = version

        meta = self.path_to_build + META_FILE_VALUE
        if effective_location != Location.Local or not os.path.exists(meta) or not image_exists(self.image_name):
            self._stamp_and_build(version)
            return
        current = PropertiesHandler.from_file(meta).get_attr(VERSION_KEY)
        if current != str(version):
            self._stamp_and_build(version)
        else:
            print(f"    Exists {self.identifier} - {self.name} ({version})")

    def _stamp_and_build(self, version):
        to_prop_file(self.path_to_build, META_FILE_VALUE, {VERSION_KEY: version})
        if self._build_image() is False:
            raise ImageBuildException(f"Image build failed for {self.identifier} - {self.name} ({self.image_name})")

    def _build_image(self):
        return image_building(self.image_name, self._build_archive, self.build_args)

    def run(self, generic_contract: Dict[AnyStr, Any], time_on=None, time_out=None):
        return run_offline_image(image_name=self.image_name, generic_contract=generic_contract, time_on=time_on, time_out=time_out)
