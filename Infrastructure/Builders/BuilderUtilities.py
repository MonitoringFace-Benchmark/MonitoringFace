import io
import os
import shutil
import tarfile
import time
from typing import Dict, AnyStr, Any, Tuple, List

import docker
from docker.errors import APIError, BuildError

from Infrastructure.Monitors.MonitorExceptions import TimedOut
from Infrastructure.constants import COMMAND_KEY, WORKDIR_KEY, VOLUMES_KEY, ENTRYPOINT_KEY


def to_prop_file(path, name, content: dict):
    with open(path + f"{name}", mode='w') as f:
        for (k, v) in content.items():
            f.write(f"{k}={v}\n")


def image_exists(name):
    try:
        docker_env = docker.from_env()
        image_lists = filter(None, map(lambda im: im.tags, docker_env.images.list()))
        for img in map(lambda s: s.split(":")[0], map(lambda x: x[0], image_lists)):
            if img == name:
                return True
        return False
    except APIError as e:
        print(f"Error getting docker images: {e}")
        return False


class ImageBuildException(Exception):
    pass


def image_building(image_name, build_dir, args=None):
    client = docker.from_env()
    try:
        print(f"\nBuilding image '{image_name}' from {build_dir} ...")
        build_output = client.api.build(
            path=build_dir, tag=image_name, decode=True,
            buildargs=args, nocache=True, rm=True, forcerm=True
        )

        error_in_build = False

        for chunk in build_output:
            if 'stream' in chunk:
                print(chunk['stream'], end='')
            elif 'error' in chunk:
                error_in_build = True
                print(f"Error: {chunk['error']}")
            elif 'status' in chunk:
                msg = chunk.get('progress', chunk['status'])
                print(msg)

        if error_in_build:
            raise ImageBuildException(f" Failed to built image: {image_name}")

        print(f" Successfully built image: {image_name}")
        return True
    except BuildError as e:
        print(f" Docker build failed: {e}")
        return False
    except APIError as e:
        print(f" Docker API error: {e}")
        return False


def run_image_offline(image_name, generic_contract: Dict[AnyStr, Any], verbose=False, time_on=None, time_out=None, is_tool_image=False):
    client = docker.from_env()

    command = generic_contract.get(COMMAND_KEY)
    command = list(filter(None, command)) if command is not None else None
    if verbose and is_tool_image:
        print(" ".join(command))
    volumes = generic_contract.get(VOLUMES_KEY)
    workdir = generic_contract.get(WORKDIR_KEY)
    entrypoint = generic_contract.get(ENTRYPOINT_KEY)

    container = None
    try:
        if time_out is None:
            start_time = time.time()
            result = client.containers.run(
                image=image_name, command=command,
                volumes=volumes, working_dir=workdir,
                remove=True, stdout=True, stderr=True,
                entrypoint=entrypoint
            )

            if time_on is not None and (time.time() - start_time < time_on):
                raise TimedOut()

            stdout = result.decode("utf-8") if isinstance(result, bytes) else str(result)
            return_code = 0
        else:
            container = client.containers.run(
                image=image_name, command=command,
                volumes=volumes, working_dir=workdir,
                stdout=True, stderr=True, detach=True,
                entrypoint=entrypoint
            )

            start_time = time.time()
            while container.status != "exited":
                container.reload()
                if time.time() - start_time > time_out:
                    try:
                        container.kill()
                    except docker.errors.APIError:
                        pass  # Container may have already exited
                    try:
                        container.remove(force=True)
                    except docker.errors.APIError:
                        pass  # Container may have already been removed
                    raise TimedOut()
                time.sleep(0.1)

            if time_on is not None and (time.time() - start_time < time_on):
                try:
                    container.remove(force=True)
                except docker.errors.APIError:
                    pass
                raise TimedOut()

            result = container.wait()
            logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="ignore")
            exit_code = result.get("StatusCode", 1)
            try:
                container.remove(force=True)
            except docker.errors.APIError:
                pass
            return logs, exit_code
    except docker.errors.ContainerError as e:
        if container:
            try:
                container.remove(force=True)
            except docker.errors.APIError:
                pass
        stdout = e.stderr.decode("utf-8") if isinstance(e.stderr, bytes) else str(e.stderr)
        return_code = e.exit_status
    except docker.errors.APIError as e:
        if container:
            try:
                container.remove(force=True)
            except docker.errors.APIError:
                pass
        stdout = f"Docker API error: {e}"
        return_code = 125
    except docker.errors.ImageNotFound:
        if container:
            try:
                container.remove(force=True)
            except docker.errors.APIError:
                pass
        stdout = "Error: Image not found"
        return_code = 127
    return stdout, return_code


def extract_binary(image_name: str, tmp_binary_location: str, verbose=False) -> Tuple[str, str]:
    client = docker.from_env()
    extracted_binary_path = None
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
    return extracted_binary_path, binary_name


# todo need to mount the right directory or specified in build?
def build_with_extracted_binary(
        path_to_secondary_dockerfile: str, secondary_image_name: str,
        python_infrastructure_files: List[str],
        extracted_binary_path: str, binary_destination: str = "/tool", verbose=False
) -> bool:
    if not os.path.exists(extracted_binary_path):
        raise FileNotFoundError(f"Extracted binary not found at {extracted_binary_path}")

    build_context_dir = path_to_secondary_dockerfile
    binary_name = os.path.basename(extracted_binary_path)
    binary_in_context = os.path.join(build_context_dir, binary_name)

    copied_items = []
    try:
        # Copy binary to build context
        if extracted_binary_path != binary_in_context:
            shutil.copy2(extracted_binary_path, binary_in_context)
            if verbose:
                print(f"Copied binary '{binary_name}' to build context: {binary_in_context}")
            copied_items.append(binary_in_context)

        # Copy Python infrastructure files to build context
        for infra_file in python_infrastructure_files:
            if not os.path.exists(infra_file):
                if verbose:
                    print(f"Warning: Infrastructure file not found: {infra_file}")
                continue

            dest_path = os.path.join(build_context_dir, os.path.basename(infra_file))
            try:
                if os.path.isdir(infra_file):
                    if os.path.exists(dest_path):
                        shutil.rmtree(dest_path)
                    shutil.copytree(infra_file, dest_path)
                    if verbose:
                        print(f"Copied directory to build context: {dest_path}")
                else:
                    # Copy file
                    shutil.copy2(infra_file, dest_path)
                    if verbose:
                        print(f"Copied file to build context: {dest_path}")
                copied_items.append(dest_path)
            except Exception as e:
                print(f"Error copying {infra_file}: {e}")
                continue

        # Build the secondary image
        success = image_building(secondary_image_name, build_context_dir)
        if success and verbose:
            print(f"Secondary image '{secondary_image_name}' built successfully with binary at {binary_destination}")
        return success
    finally:
        for item in copied_items:
            try:
                if os.path.isdir(item):
                    shutil.rmtree(item)
                    if verbose:
                        print(f"Cleaned up directory: {item}")
                elif os.path.isfile(item):
                    os.remove(item)
                    if verbose:
                        print(f"Cleaned up file: {item}")
            except Exception as e:
                print(f"Warning: Failed to clean up {item}: {e}")
