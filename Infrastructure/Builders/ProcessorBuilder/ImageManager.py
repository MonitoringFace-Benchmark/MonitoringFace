import os
from typing import AnyStr, Dict, Any

from Infrastructure.DataLoader.DataLoader import DataLoader
from Infrastructure.DataLoader.Resolver import ProcessorResolver, Location
from Infrastructure.DataTypes.Types.custome_type import Processor
from Infrastructure.Builders.ProcessorBuilder.AbstractImageManager import AbstractImageManager
from Infrastructure.Builders.BuilderUtilities import image_exists, image_building, run_image
from Infrastructure.Monitors.MonitorExceptions import BuildException
from Infrastructure.constants import IMAGE_POSTFIX


def processor_to_identifier(p: Processor) -> AnyStr:
    if p == Processor.DataGenerators:
        return "DataGenerators"
    elif p == Processor.DataConverters:
        return "DataConverters"
    elif p == Processor.PolicyGenerators:
        return "PolicyGenerators"
    elif p == Processor.PolicyConverters:
        return "PolicyConverters"
    elif p == Processor.CaseStudies:
        return "CaseStudies"
    else:
        return "GeneralUtilities"


def to_file(file, content):
    with open(file, "w") as f:
        f.write(content)


class ImageManager(AbstractImageManager):
    def __init__(self, name, proc: Processor, path_to_build_inner):
        super().__init__()
        self.downloader = DataLoader(proc)

        self.name = name
        self.path = path_to_build_inner
        self.processor = proc
        self.identifier = processor_to_identifier(proc)
        self.image_name = f"{name.lower()}_{self.identifier.lower()}{IMAGE_POSTFIX}"

        parent = self.path + "/" + self.identifier
        if not os.path.exists(parent):
            os.mkdir(parent)
            os.mkdir(parent + f"/{self.name}")
            self._build_image()
        elif os.path.exists(parent) and not os.path.exists(parent + f"/{self.name}"):
            os.mkdir(parent + f"/{self.name}")
            self._build_image()
        else:
            if not image_exists(self.image_name):
                self._build_image()

    def _build_image(self):
        resolver_location = ProcessorResolver(self.name, self.path, self.processor).resolve()
        build_dir = self.path + f"/{self.identifier}/{self.name}"
        if resolver_location == Location.Remote:
            content = self.downloader.get_content(self.name)
            print(build_dir)
            to_file(build_dir + "/Dockerfile", content)
        elif resolver_location == Location.Unavailable:
            raise BuildException()
        image_building(self.image_name, build_dir)

    def run(self, generic_contract: Dict[AnyStr, Any], time_on=None, time_out=None):
        return run_image(image_name=self.image_name, generic_contract=generic_contract, time_on=time_on, time_out=time_out)
