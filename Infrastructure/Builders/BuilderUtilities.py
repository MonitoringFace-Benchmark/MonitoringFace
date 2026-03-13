import time
from typing import Dict, AnyStr, Any, Iterator, Tuple, Optional

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


def run_image(image_name, generic_contract: Dict[AnyStr, Any], verbose=False, time_on=None, time_out=None, is_tool_image=False):
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


def run_image_streaming(
    image_name: str,
    generic_contract: Dict[AnyStr, Any],
    inputs: Iterator[str],
    #latency_marker: Optional[str], force output command
    read_timeout: float = 1.0,
    verbose: bool = False
) -> Iterator[Tuple[str, Optional[int], Optional[float]]]:
    import subprocess
    import select
    import os

    command = generic_contract.get(COMMAND_KEY)
    command = list(filter(None, command)) if command is not None else None
    volumes = generic_contract.get(VOLUMES_KEY)
    workdir = generic_contract.get(WORKDIR_KEY)
    entrypoint = generic_contract.get(ENTRYPOINT_KEY)

    docker_cmd = ["docker", "run", "-i", "--rm"]

    if workdir:
        docker_cmd.extend(["-w", workdir])

    if volumes:
        for host_path, mount_info in volumes.items():
            bind_path = mount_info.get('bind', host_path)
            mode = mount_info.get('mode', 'rw')
            docker_cmd.extend(["-v", f"{host_path}:{bind_path}:{mode}"])

    if entrypoint:
        docker_cmd.extend(["--entrypoint", entrypoint])

    docker_cmd.append(image_name)

    if command:
        docker_cmd.extend(command)

    if verbose:
        print(f"Streaming command: {' '.join(docker_cmd)}")

    try:
        proc = subprocess.Popen(
            docker_cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0
        )

        fd = proc.stdout.fileno()
        import fcntl
        flags = fcntl.fcntl(fd, fcntl.F_GETFL)
        fcntl.fcntl(fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

        time.sleep(0.3)

        for input_data in inputs:
            if proc.poll() is not None:
                break

            if not input_data.endswith('\n'):
                input_data += '\n'
            if verbose:
                print("\nGive input:", input_data.strip())

            # Send input to stdin and measure time to first byte
            cycle_start = time.time()
            proc.stdin.write(input_data.encode('utf-8'))
            proc.stdin.flush()

            output = ""
            ttfb_ms = None
            start_time = time.time()
            while time.time() - start_time < read_timeout:
                try:
                    ready, _, _ = select.select([proc.stdout], [], [], 0.05)
                    if ready:
                        chunk = proc.stdout.read(4096)
                        if chunk:
                            if ttfb_ms is None:
                                ttfb_ms = (time.time() - cycle_start) * 1000
                            output += chunk.decode('utf-8', errors='ignore')
                            start_time = time.time()  # Reset timeout on data
                        else:
                            break
                except (BlockingIOError, IOError):
                    time.sleep(0.05)

            yield output, None, ttfb_ms

        proc.stdin.close()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

        final_output = ""
        try:
            remaining = proc.stdout.read()
            if remaining:
                final_output = remaining.decode('utf-8', errors='ignore')
        except Exception:
            pass

        yield final_output, proc.returncode, None

    except FileNotFoundError:
        yield "Error: docker command not found", 127, None
    except Exception as e:
        yield f"Error: {e}", 1, None


if __name__ == "__main__":
    # Example usage
    contract = {
        COMMAND_KEY: ["timelymon", "policy.policy", "--sig-file", "sig.sig", "-w", "1", "-m", "1", "-S", "1", "-l"],
        WORKDIR_KEY: "/data",
        VOLUMES_KEY: {'/Users/krq770/PycharmProjects/MonitoringFace_curr/Infrastructure/experiments/Test': {'bind': '/data', 'mode': 'rw'}}
    }

    inputs = [
        "C, tp=0, ts=0",
        "B, tp=0, ts=0, x1=4, x2=10",
        "A, tp=1, ts=1, x1=1",
        "A, tp=1, ts=1, x1=3",
        "A, tp=2, ts=2, x0=1",
        "A, tp=2, ts=2, x0=2",
        "A, tp=2, ts=2, x0=3",
        "B, tp=2, ts=2, x1=4, x2=10",
        "A, tp=3, ts=3, x1=999"
    ]

    for output, code, ttfb_ms in run_image_streaming(
            "timelymon_simplify_approximation_mf_image", contract, inputs=iter(inputs), verbose=True
    ):
        if ttfb_ms:
            print(f"Output: {output.strip()}, TTFB: {ttfb_ms:.2f}ms")
