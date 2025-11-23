from dataclasses import fields

from Infrastructure.DataTypes.Contracts.SubContracts.CaseStudyContract import CaseStudyContract
from Infrastructure.Builders.ProcessorBuilder.CaseStudiesGenerators.CaseStudyTemplate import CaseStudyTemplate
from Infrastructure.Builders.ProcessorBuilder.ImageManager import ImageManager, Processor
from Infrastructure.constants import WORKDIR_KEY, WORKDIR_VAL, VOLUMES_KEY


class CaseStudyGenerator(CaseStudyTemplate):
    def __init__(self, name, path_to_build):
        self.image = ImageManager(name, Processor.CaseStudies, path_to_build)

    def run_generator(self, generic_contract, time_on=None, time_out=None):
        valid_fields = {f.name for f in fields(CaseStudyContract)}
        case_contract = CaseStudyContract(**{k: v for k, v in generic_contract.items() if k in valid_fields})

        inner_contract = dict()
        inner_contract[VOLUMES_KEY] = {case_contract.path: {'bind': '/data', 'mode': 'rw'}}
        inner_contract[WORKDIR_KEY] = WORKDIR_VAL

        return self.image.run(inner_contract, time_on=time_on, time_out=time_out)
