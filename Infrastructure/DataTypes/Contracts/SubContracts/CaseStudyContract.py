import dataclasses

from Infrastructure.DataTypes.Contracts.AbstractContract import AbstractContract


@dataclasses.dataclass
class CaseStudyContract:
    path: str


class CaseStudySetupContract(AbstractContract):
    def __init__(self, name: str):
        self.name = name

    def default_contract(self):
        pass

    def instantiate_contract(self, params):
        pass


