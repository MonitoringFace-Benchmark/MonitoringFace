import os
import subprocess
import urllib.request

from Infrastructure.cli import main as cli_main


def validate_setup():
    try:
        urllib.request.urlopen('https://www.google.com', timeout=3).getcode()
    except Exception:
        raise RuntimeError("Network connection is not available!")

    docker_ok = subprocess.call(['docker', 'info'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
    if not docker_ok:
        raise RuntimeError("Docker is not available!")


if __name__ == "__main__":
    validate_setup()
    cli_main(path_to_module=os.getcwd())
