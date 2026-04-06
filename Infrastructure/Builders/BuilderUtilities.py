import time
import re
from typing import Dict, AnyStr, Any, List

import docker
from docker.errors import APIError, BuildError

from Infrastructure.DataTypes.Contracts.OnlineExperimentContract import OnlineExperimentContractGeneral, \
    OnlineExperimentContractTool
from Infrastructure.Monitors.MonitorExceptions import TimedOut, ToolException
from Infrastructure.constants import COMMAND_KEY, WORKDIR_KEY, VOLUMES_KEY, ENTRYPOINT_KEY
from Infrastructure.printing import print_headline, print_footline


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


def run_offline_image(image_name, generic_contract: Dict[AnyStr, Any], verbose=False, time_on=None, time_out=None,
                      is_tool_image=False):
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


def run_online_image(
        image_name: str,
        tool_command: List[str],
        online_experiment_contract: OnlineExperimentContractGeneral,
        tool_online_experiment_contract: OnlineExperimentContractTool,
):
    client = docker.from_env()
    workdir = "/app"

    command_fixed = [
        "--data-source", "data/data",
        "--binary-location", "/usr/local/bin",
        "--binary-name", "tool",
    ]
    command_tool_specific = tool_online_experiment_contract.get_tool_arguments()
    command_experiment_specific = online_experiment_contract.get_settings()
    if isinstance(tool_command, (list, tuple)):
        tool_command_list = [str(x) for x in tool_command]
    elif isinstance(tool_command, str):
        tool_command_list = tool_command.split()
    else:
        tool_command_list = [str(tool_command)]

    command_driver = command_fixed + command_tool_specific + command_experiment_specific + ["--"] + tool_command_list
    command_driver = [str(x) for x in command_driver if x is not None]

    container = None
    try:
        container = client.containers.run(
            image=image_name,
            command=command_driver,
            working_dir=workdir,
            stdout=True, stderr=True,
            detach=True, remove=False,
        )

        footer_acc_elapsed_s = None
        footer_total_count = None

        parsed_blocks = []
        current_block = {"output": None, "processed": None, "elapsed_ns": None}

        current_output = False
        check_for_final_error = False

        final_error = None
        unexpected_error = None

        for chunk in container.logs(stream=True, follow=True, stdout=True, stderr=True):
            text = chunk.decode("utf-8", errors="ignore") if isinstance(chunk, (bytes, bytearray)) else str(chunk)
            if text.startswith("[Error"):
                unexpected_error = text.strip()
                break

            if text == "\n":
                parsed_blocks.append(current_block)
                current_block = {"output": None, "processed": None, "elapsed_ns": None}
                continue

            if text.startswith("[Accumulative Elapsed]"):
                payload = text.split("]")[1]
                payload = payload.strip()
                if payload.endswith("s"):
                    payload = payload[:-1].strip()
                footer_acc_elapsed_s = float(payload)

            if text.startswith("[Total Count]"):
                payload = text.split("]")[1]
                payload = payload.strip()
                footer_total_count = int(payload)
                check_for_final_error = True

            if check_for_final_error and text.startswith("[Error"):
                final_error = text.strip()
                break

            if text.startswith("[Input"):
                continue

            if text.startswith("[Output"):
                current_block["output"] = []
                current_output = True
                continue

            if not text.startswith("[Processed") and current_output:
                payload = text.strip()
                current_block["output"].append(payload)
            else:
                current_output = False

            if text.startswith("[Processed"):
                payload = text.split("]")[1]
                payload = payload.strip()
                current_block["processed"] = int(payload)

            if text.startswith("[Elapsed"):
                payload = text.split("]")[1]
                payload = payload.strip()
                if payload.endswith("ns"):
                    payload = payload[:-2].strip()
                current_block["elapsed_ns"] = int(payload)

        result = container.wait()
        exit_code = result.get("StatusCode", 1) if isinstance(result, dict) else 1
        if unexpected_error:
            raise ToolException(f"Unexpected failure with exit code ({exit_code}) {unexpected_error}")
        return parsed_blocks, footer_acc_elapsed_s, footer_total_count, final_error, exit_code
    except docker.errors.ContainerError as e:
        stderr_text = e.stderr.decode("utf-8", errors="ignore") if isinstance(e.stderr, (bytes, bytearray)) else str(
            e.stderr)
        return stderr_text, e.exit_status, [], None, None
    except docker.errors.APIError as e:
        return f"Docker API error: {e}", 125, [], None, None
    except docker.errors.ImageNotFound:
        return "Error: Image not found", 127, [], None, None
    finally:
        if container is not None:
            try:
                container.remove(force=True)
            except docker.errors.APIError:
                pass
