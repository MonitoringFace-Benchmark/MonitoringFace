import time
from typing import Dict, AnyStr, Any

import docker
from docker.errors import APIError, BuildError

from Infrastructure.DataLoader import init_repo_fetcher
from Infrastructure.DataLoader.Resolver import Location
from Infrastructure.DataTypes.FileRepresenters.PropertiesHandler import PropertiesHandler
from Infrastructure.Monitors.MonitorExceptions import TimedOut
from Infrastructure.constants import COMMAND_KEY, WORKDIR_KEY, VOLUMES_KEY, ENTRYPOINT_KEY


def verify_version(build_folder, image_name, location, release, branch):
    if location == Location.Local:
        return True

    fl = PropertiesHandler.from_file(build_folder + f"/tool.properties")
    ml = PropertiesHandler.from_file(build_folder + f"/meta.properties")

    if not release:
        git_fetcher = init_repo_fetcher(fl.get_attr("git"), fl.get_attr("owner"), fl.get_attr("repo"))
        version = ml.get_attr("version")
        remote_version = git_fetcher.get_hash(branch)
        if version is not None:
            return version == remote_version and image_exists(image_name)
        else:
            return False
    else:
        return True


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


def image_building(image_name, build_dir, args=None):
    client = docker.from_env()
    try:
        print(f"\nBuilding image '{image_name}' from {build_dir} ...")
        build_output = client.api.build(
            path=build_dir, tag=image_name, decode=True,
            buildargs=args, nocache=True, rm=True, forcerm=True
        )

        for chunk in build_output:
            if 'stream' in chunk:
                print(chunk['stream'], end='')
            elif 'error' in chunk:
                print(f"Error: {chunk['error']}")
            elif 'status' in chunk:
                msg = chunk.get('progress', chunk['status'])
                print(msg)

        print(f" Successfully built image: {image_name}")
        return True
    except BuildError as e:
        print(f" Docker build failed: {e}")
        return False
    except APIError as e:
        print(f" Docker API error: {e}")
        return False


def run_image(image_name, generic_contract: Dict[AnyStr, Any], time_on=None, time_out=None):
    client = docker.from_env()

    command = generic_contract.get(COMMAND_KEY)
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
                    container.kill()
                    container.remove(force=True)
                    raise TimedOut()
                time.sleep(0.1)

            if time_on is not None and (time.time() - start_time < time_on):
                container.remove(force=True)
                raise TimedOut()

            result = container.wait()
            logs = container.logs(stdout=True, stderr=True).decode("utf-8", errors="ignore")
            exit_code = result.get("StatusCode", 1)
            container.remove(force=True)
            return logs, exit_code
    except docker.errors.ContainerError as e:
        if container:
            container.remove(force=True)
        stdout = e.stderr.decode("utf-8") if isinstance(e.stderr, bytes) else str(e.stderr)
        return_code = e.exit_status
    except docker.errors.APIError as e:
        if container:
            container.remove(force=True)
        stdout = f"Docker API error: {e}"
        return_code = 125
    except docker.errors.ImageNotFound:
        if container:
            container.remove(force=True)
        stdout = "Error: Image not found"
        return_code = 127
    return stdout, return_code
