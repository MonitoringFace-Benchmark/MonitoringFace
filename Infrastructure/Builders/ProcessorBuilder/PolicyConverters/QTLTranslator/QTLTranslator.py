import subprocess
from typing import AnyStr

from Infrastructure.Builders.ProcessorBuilder.ImageManager import Processor, ImageManager


class QTLTranslator:
    def __init__(self, name, path_to_project):
        self.image = ImageManager(name, Processor.PolicyConverters, path_to_project)

    def convert(self, path_to_folder: AnyStr, data_file: AnyStr, tool: AnyStr, name: AnyStr, dest: AnyStr, params):
        command = ["docker", "run", "--rm", 
                   "-iv", f"{path_to_folder}:/home/qtl-translator/work",
                   f"{self.image.image_name.lower()}"] + params + [f"{path_to_folder}/{data_file}"]
        
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode == 0:
            with open(f"{dest}/{name}.{tool}", "w") as f:
                for line in result.stdout.splitlines():
                    f.write(line + "\n")
        else:
            raise QTLTranslatorException("QTLTranslator Failed")


class QTLTranslatorException(Exception):
    pass