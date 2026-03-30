import os
import io
import shutil
import tarfile
from enum import Enum
from typing import Optional

import docker
from docker.errors import APIError

from Infrastructure.Builders.BuilderUtilities import image_building, ImageBuildException, image_exists
from Infrastructure.Builders.ToolBuilder.AbstractToolImageManager import AbstractToolImageManager
from Infrastructure.constants import Policy_File, Signature_File, ADDITIONAL_FOLDER


class DataSourceType(Enum):
    FILE = "file"
    SCRIPT = "script"


def build_pipeline(
        tool_image_manager: AbstractToolImageManager,
        path_to_build, path_to_archive, data_source_type: DataSourceType, data_source: str,
        policy_file: str, signature_file: Optional[str], target_image_name: str
):
    path = f"{path_to_build}/OnlineExperimentDriver"
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)

    driver_docker = f"{path_to_archive}/Utilities/OnlineExperimentDriver"
    driver_tool_name = "online_experiment_driver"
    build_stage(
        temporary_build_folder=path, tool_image_manager=tool_image_manager,
        driver_docker=driver_docker, driver_tool_name=driver_tool_name,
        data_source=data_source, policy_file=policy_file, signature_file=signature_file
    )

    # build the final image with the copied dockerfile and the copied data
    shutil.copy(f"{path_to_archive}/Utilities/OnlineExperimentTemplate/Dockerfile", path)
    image_building(target_image_name, build_dir=path, args={"host_dir": path})


def build_stage(
        tool_image_manager: AbstractToolImageManager, temporary_build_folder: str,
        driver_docker: str, driver_tool_name: str,
        data_source: str, policy_file: str, signature_file: Optional[str]
):
    # build, extract and move tool binary to build folder
    extract_binary(tool_image_manager.get_image_name(), temporary_build_folder, "tool")

    # build, extract and move driver binary to build folder
    if not build_image_wrapper(driver_docker, driver_tool_name):
        raise ImageBuildException(f"Failed to build driver image: {driver_tool_name}")
    extract_binary(driver_tool_name, temporary_build_folder, "driver")

    # pass the file or data script to the build folder
    move_data_source(temporary_build_folder, data_source)
    file_dict = {Policy_File(): policy_file, Signature_File(): signature_file}
    move_additional_data(temporary_build_folder, ADDITIONAL_FOLDER, file_dict)


def move_data_source(temporary_build_folder: str, data_source: str):
    dest_dir = os.path.join(temporary_build_folder, "data")
    os.makedirs(dest_dir, exist_ok=True)

    dest_path = os.path.join(dest_dir, "data")
    shutil.copy(data_source, dest_path)


def move_additional_data(temporary_build_folder: str, folder_name: str, additional_data: dict[str, str]):
    dest_dir = os.path.join(temporary_build_folder, folder_name)
    os.makedirs(dest_dir, exist_ok=True)
    for data_name, data_path in additional_data.items():
        if not data_path:
            continue
        dest_path = os.path.join(dest_dir, data_name)
        shutil.copy(data_path, dest_path)


def build_image_wrapper(dockerfile_path: str, image_name: str) -> bool:
    print(f"image name: {image_name}")
    print(f"dockerfile path: {dockerfile_path}")
    if not image_exists(image_name):
        if not image_building(image_name, dockerfile_path):
            raise ImageBuildException(f"Failed to build image: {image_name}")
    else:
        print(f"Image {image_name} already exists. Skipping build.")
    return True


def extract_binary(image_name: str, tmp_binary_location: str, binary_name: str) -> tuple[str, str]:
    client = docker.from_env()
    extracted_binary_path = None
    requested_name = binary_name
    binary_name = None
    try:
        container = client.containers.create(image_name, detach=True)
        try:
            os.makedirs(tmp_binary_location, exist_ok=True)
            if not os.access(tmp_binary_location, os.W_OK):
                raise PermissionError(f"Destination directory {tmp_binary_location} is not writable")

            try:
                archive_bytes, _ = container.get_archive("/usr/local/bin")
                tar_stream = io.BytesIO(b"".join(archive_bytes))
                with tarfile.open(fileobj=tar_stream, mode='r:*') as tar:
                    tar.extractall(path=tmp_binary_location)
                print(f"Binary extracted successfully from /usr/local/bin to {tmp_binary_location}")
                extracted_binary_path = tmp_binary_location
                binary_name = "bin"
            except APIError:
                archive_bytes, _ = container.get_archive("/")
                tar_stream = io.BytesIO(b"".join(archive_bytes))
                with tarfile.open(fileobj=tar_stream, mode='r:*') as tar:
                    for member in tar.getmembers():
                        if member.name == '/' or member.name.startswith('/.') or '/' in member.name.lstrip('/'):
                            continue
                        if member.isfile():
                            try:
                                tar_obj = tar.extractfile(member)
                                dst_path = os.path.join(tmp_binary_location, member.name.lstrip('/'))
                                dst_dir = os.path.dirname(dst_path)
                                os.makedirs(dst_dir, exist_ok=True)
                                if os.path.exists(dst_path):
                                    os.remove(dst_path)
                                with open(dst_path, 'wb') as dst_file:
                                    shutil.copyfileobj(tar_obj, dst_file)
                                os.chmod(dst_path, 0o755)
                                if extracted_binary_path is None:
                                    extracted_binary_path = dst_path
                                    binary_name = os.path.basename(dst_path)
                            except OSError as e:
                                print(f"Warning: Failed to extract {member.name}: {e}")
                                continue
                print(f"Binary extracted successfully from root to {tmp_binary_location}")
        finally:
            container.remove(force=True)
    except APIError as e:
        raise APIError(f"Docker API error during binary extraction: {e}")
    except Exception as e:
        raise Exception(f"Error extracting binary from image {image_name}: {e}")

    if extracted_binary_path is None or binary_name is None:
        raise Exception(f"Failed to extract binary from image {image_name}")

    if os.path.isfile(extracted_binary_path):
        target_path = os.path.join(os.path.dirname(extracted_binary_path), requested_name)
        if target_path != extracted_binary_path:
            os.replace(extracted_binary_path, target_path)
            extracted_binary_path = target_path

    return extracted_binary_path, requested_name


if __name__ == "__main__":
    from Infrastructure.Builders.ToolBuilder.ToolImageManager import DirectToolImageManager
    from Infrastructure.DataTypes.Types.custome_type import BranchOrRelease, OnlineOffline
    from Infrastructure.DataLoader.Resolver import Location
    from Infrastructure.Frontend.CLI.cli_args import CLIArgs

    path_to_build = "/Users/krq770/PycharmProjects/MonitoringFace_curr/Infrastructure/build"
    path_to_archive = "/Users/krq770/PycharmProjects/MonitoringFace_curr/Archive"

    tool_manager = DirectToolImageManager(
        name="TimelyMon", branch="simplify_approximation", release=BranchOrRelease.Branch,
        commit=None, path_to_build=path_to_build,
        path_to_archive=path_to_archive,
        path_to_infra="/Users/krq770/PycharmProjects/MonitoringFace_curr/Infrastructure",
        location=Location.Local, cli_args=CLIArgs(), runtime_setting=OnlineOffline.Online
    )

    build_pipeline(
        tool_image_manager=tool_manager, path_to_build=path_to_build,
        path_to_archive=path_to_archive, data_source_type=DataSourceType.FILE,
        data_source="/Users/krq770/PycharmProjects/MonitoringFace_curr/Infrastructure/experiments/Test/data",
        policy_file="/Users/krq770/PycharmProjects/MonitoringFace_curr/Infrastructure/experiments/Test/policy.policy",
        signature_file="/Users/krq770/PycharmProjects/MonitoringFace_curr/Infrastructure/experiments/Test/signature.sig",
        target_image_name="online_experiment_image"
    )
