import os
import shutil

from Infrastructure.Builders.ProcessorBuilder.CaseStudiesGenerators.CaseStudyTemplate import CaseStudyTemplate
from Infrastructure.constants import PATH_KEY


class CaseStudyCopyGenerator(CaseStudyTemplate):
    def __init__(self, name, path_to_project):
        self.name = name
        self.path_to_archive = f"{path_to_project}/Archive/CaseStudies/{name}"
        if not os.path.exists(self.path_to_archive):
            raise FileNotFoundError(f"{self.path_to_archive} does not exist, locally.")

    def run_generator(self, generic_contract, time_on=None, time_out=None):
        path_to_named_experiments = generic_contract[PATH_KEY]
        if not os.path.exists(path_to_named_experiments):
            os.makedirs(path_to_named_experiments)
        for item in os.listdir(self.path_to_archive):
            src_path = f"{self.path_to_archive}/{item}"
            dst_path = f"{path_to_named_experiments}/{item}"
            if os.path.isfile(src_path):
                shutil.copy(src_path, dst_path)
            elif os.path.isdir(src_path):
                if os.path.exists(dst_path):
                    shutil.rmtree(dst_path)
                shutil.copytree(src_path, dst_path)
        return "Copy Successful", 0
