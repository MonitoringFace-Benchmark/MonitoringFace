import subprocess
from typing import AnyStr, List, Tuple

from Infrastructure.Builders.ProcessorBuilder.DataConverters.DataConverterTemplate import DataConverterTemplate
from Infrastructure.Builders.ProcessorBuilder.ImageManager import Processor, ImageManager
from Infrastructure.InputOutputFormats import InputOutputFormats
from Infrastructure.Monitors.MonitorExceptions import ReplayerException


class ReplayerConverter(DataConverterTemplate):
    def __init__(self, name, path_to_project):
        self.image = ImageManager(name, Processor.DataConverters, path_to_project)

    def convert(
        self, path_to_folder: str, input_file: str,
        path_to_output_folder: str, output_file: str,
        source, target, params
    ):
        command = ["docker", "run", "--rm", "--entrypoint", "java",
                   "-iv", f"{path_to_folder}:/work",
                   f"{self.image.image_name.lower()}", "-cp", "classes:libs/*",
                   "org.entry.Dispatcher", "Replayer", "-i", f"{source}", "-f", f"{target}"] + params

        with open(f"{path_to_folder}/{input_file}", 'r') as input_file:
            result = subprocess.run(command, stdin=input_file, capture_output=True, text=True)
            if result.returncode == 0:
                with open(f"{path_to_output_folder}/{output_file}", "w") as f:
                    for line in filter(lambda x: not x.startswith(">W"), result.stdout.splitlines()):
                        f.write(line + "\n")
            else:
                raise ReplayerException("Replayer Failed")

    @staticmethod
    def conversion_scheme() -> List[Tuple[InputOutputFormats, InputOutputFormats]]:
        return [
            (InputOutputFormats.MONPOLY, InputOutputFormats.CSV),
            (InputOutputFormats.MONPOLY, InputOutputFormats.CSV_LINEAR),
            (InputOutputFormats.MONPOLY, InputOutputFormats.DEJAVU),
            (InputOutputFormats.MONPOLY, InputOutputFormats.DEJAVU_ENCODED),
            (InputOutputFormats.MONPOLY, InputOutputFormats.DEJAVU_LINEAR),

            (InputOutputFormats.CSV, InputOutputFormats.MONPOLY),
            (InputOutputFormats.CSV, InputOutputFormats.MONPOLY_LINEAR),
            (InputOutputFormats.CSV, InputOutputFormats.DEJAVU),
            (InputOutputFormats.CSV, InputOutputFormats.DEJAVU_ENCODED),
            (InputOutputFormats.CSV, InputOutputFormats.DEJAVU_LINEAR),

            (InputOutputFormats.DEJAVU, InputOutputFormats.MONPOLY),
            (InputOutputFormats.DEJAVU, InputOutputFormats.MONPOLY_LINEAR),
            (InputOutputFormats.DEJAVU, InputOutputFormats.CSV),
            (InputOutputFormats.DEJAVU, InputOutputFormats.CSV_LINEAR),
        ]
