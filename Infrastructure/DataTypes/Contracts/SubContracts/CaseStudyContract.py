import dataclasses

from Infrastructure.DataTypes.Contracts.AbstractContract import AbstractContract


@dataclasses.dataclass
class CaseStudyContract:
    path: str


@dataclasses.dataclass
class CaseStudySetupContract(AbstractContract):
    name: str

    def default_contract(self):
        pass

    def instantiate_contract(self, params):
        pass


