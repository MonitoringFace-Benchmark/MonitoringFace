import json
import os
import io
import shutil
import tarfile
from typing import Optional, Dict, List

import docker
from docker.errors import APIError

from Infrastructure.Builders.BuilderUtilities import image_building, ImageBuildException, image_exists
from Infrastructure.Builders.ProcessorBuilder.ComponentPins import get_pin, docker_ref
from Infrastructure.Builders.ToolBuilder.AbstractToolImageManager import AbstractToolImageManager
from Infrastructure.constants import Policy_File, Signature_File, ADDITIONAL_FOLDER, BUILD_ARG_GIT_BRANCH, \
    BUILD_ARG_GIT_COMMIT

DRIVER_COMPONENT_NAME = "OnlineExperimentDriver"


def driver_image_details():
    """The driver is a component like any other: a `components:` pin selects
    its branch/commit, the ref lands in the image tag so pinned versions
    coexist, and unpinned keeps the historical name-cached main build."""
    branch, commit = get_pin(DRIVER_COMPONENT_NAME)
    if branch is None and commit is None:
        print(f"    WARNING: {DRIVER_COMPONENT_NAME} is unpinned; the cached main build is "
              f"reused as-is (add a components: entry to pin it)")
        return "online_experiment_driver", None
    ref = docker_ref(commit or branch)
    args = {BUILD_ARG_GIT_BRANCH: branch or "main"}
    if commit:
        args[BUILD_ARG_GIT_COMMIT] = commit
    return f"online_experiment_driver_{ref}", args


def bake_stream_processors(temporary_build_folder: str, path_to_project: str, spec: Optional[List[Dict]]):
    dest = os.path.join(temporary_build_folder, "processors")
    os.makedirs(dest, exist_ok=True)
    if not spec:
        return
    subtree = "Builders/ProcessorBuilder/StreamProcessors"
    for rel in (f"Infrastructure/{subtree}", f"Archive/Implementations/{subtree}"):
        shutil.copytree(
            os.path.join(path_to_project, rel), os.path.join(dest, rel),
            ignore=shutil.ignore_patterns("__pycache__"))
        parent = ""
        for part in rel.split("/")[:-1]:
            parent = os.path.join(parent, part)
            init = os.path.join(dest, parent, "__init__.py")
            if not os.path.exists(init):
                open(init, "w").close()
    with open(os.path.join(dest, "pipeline.json"), "w") as f:
        json.dump(spec, f, indent=1)


def build_pipeline(
        tool_image_manager: AbstractToolImageManager,
        path_to_build, path_to_archive, data_source: str, path_to_folder: str,
        policy_file: str, signature_file: Optional[str], target_image_name: str,
        compilation_details: Optional[Dict[str, str]] = None, verbose: bool = False,
        stream_spec: Optional[List[Dict]] = None
):
    path = f"{path_to_build}/OnlineExperimentDriver"
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)

    driver_docker = f"{path_to_archive}/Docker/Utilities/OnlineExperimentDriver"
    driver_tool_name, driver_args = driver_image_details()
    build_stage(
        temporary_build_folder=path, tool_image_manager=tool_image_manager,
        driver_docker=driver_docker, driver_tool_name=driver_tool_name, path_to_folder=path_to_folder,
        data_source=data_source, policy_file=policy_file, signature_file=signature_file,
        compilation_details=compilation_details, verbose=verbose, driver_args=driver_args
    )

    bake_stream_processors(path, os.path.dirname(path_to_archive.rstrip("/")), stream_spec)

    # build the final image with the copied dockerfile and the copied data
    shutil.copy(f"{path_to_archive}/Docker/Utilities/OnlineExperimentTemplate/Dockerfile", path)
    image_building(image_name=target_image_name, build_dir=path)


def build_stage(
        tool_image_manager: AbstractToolImageManager, temporary_build_folder: str,
        driver_docker: str, driver_tool_name: str, path_to_folder: str,
        data_source: str, policy_file: str, signature_file: Optional[str],
        compilation_details: Optional[Dict[str, str]] = None, verbose: bool = False,
        driver_args: Optional[Dict[str, str]] = None
):
    if compilation_details is None:
        extract_binary(tool_image_manager.get_image_name(), temporary_build_folder, "tool", verbose=verbose)
    else:
        tool_name = tool_image_manager.get_image_name()
        if not build_image_wrapper(tool_name, temporary_build_folder, args=compilation_details, verbose=verbose):
            raise ImageBuildException(f"Failed to build driver image: {tool_name}")
        extract_binary(tool_name, temporary_build_folder, "tool", verbose=verbose)

    # build, extract and move driver binary to build folder
    if not build_image_wrapper(driver_docker, driver_tool_name, args=driver_args, verbose=verbose):
        raise ImageBuildException(f"Failed to build driver image: {driver_tool_name}")
    extract_binary(driver_tool_name, temporary_build_folder, "driver", verbose=verbose)

    # pass the file or data script to the build folder
    move_data_source(temporary_build_folder, path_to_folder, data_source)
    file_dict = {Policy_File(): policy_file, Signature_File(): signature_file}
    move_additional_data(temporary_build_folder, path_to_folder, ADDITIONAL_FOLDER, file_dict)


def move_data_source(temporary_build_folder: str, path_to_folder: str, data_source: str):
    dest_dir = os.path.join(temporary_build_folder, "data")
    os.makedirs(dest_dir, exist_ok=True)

    dest_path = os.path.join(dest_dir, "data")
    shutil.copy(f"{path_to_folder}/{data_source}", dest_path)


def move_additional_data(temporary_build_folder: str, path_to_folder: str, folder_name: str, additional_data: dict[str, str]):
    dest_dir = os.path.join(temporary_build_folder, folder_name)
    os.makedirs(dest_dir, exist_ok=True)
    for data_name, data_path in additional_data.items():
        if not data_path:
            continue
        dest_path = os.path.join(dest_dir, data_name)
        shutil.copy(f"{path_to_folder}/{data_path}", dest_path)


def build_image_wrapper(dockerfile_path: str, image_name: str, args: Optional[Dict[str, str]] = None, verbose: bool = False) -> bool:
    if not image_exists(image_name):
        if not image_building(image_name, dockerfile_path, args):
            raise ImageBuildException(f"Failed to build image: {image_name}")
    else:
        if verbose:
            print(f"Image {image_name} already exists. Skipping build.")
    return True


def extract_binary(image_name: str, tmp_binary_location: str, binary_name: str, verbose: bool = False) -> tuple[str, str]:
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
                if verbose:
                    print(f"Binary extracted successfully from /usr/local/bin to {tmp_binary_location}")
                extracted_binary_path = tmp_binary_location
                binary_name = requested_name

                if os.path.exists(f"{tmp_binary_location}/bin"):
                    shutil.copy(f"{tmp_binary_location}/bin/tool", f"{tmp_binary_location}/tool")
                    shutil.rmtree(f"{tmp_binary_location}/bin")

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
                                if verbose:
                                    print(f"Warning: Failed to extract {member.name}: {e}")
                                continue
                if verbose:
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
