import subprocess
from typing import AnyStr

from Infrastructure.Builders.ProcessorBuilder.DataConverter.DataConverterTemplate import DataConverterTemplate
from Infrastructure.Builders.ProcessorBuilder.ImageManager import Processor, ImageManager
from Infrastructure.Monitors.MonitorExceptions import ReplayerException


class ReplayerConverter(DataConverterTemplate):
    def __init__(self, name, path_to_build):
        self.image = ImageManager(name, Processor.DataConverters, path_to_build)

    def convert(self, path_to_folder: AnyStr, data_file: AnyStr, tool: AnyStr, name: AnyStr, dest: AnyStr, params):
        command = ["docker", "run", "--rm", "--entrypoint", "java",
                   "-iv", f"{path_to_folder}:/work",
                   f"{self.image.image_name.lower()}", "-cp", "classes:libs/*",
                   "org.entry.Dispatcher", "Replayer",
                   "-f", f"{tool}"] + params

        with open(f"{path_to_folder}/{data_file}", 'r') as input_file:
            result = subprocess.run(command, stdin=input_file, capture_output=True, text=True)
            if result.returncode == 0:
                with open(f"{dest}/{name}.{tool}", "w") as f:
                    for line in filter(lambda x: not x.startswith(">W"), result.stdout.splitlines()):
                        f.write(line + "\n")
            else:
                raise ReplayerException("Replayer Failed")
