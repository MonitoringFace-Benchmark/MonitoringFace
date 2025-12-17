from dataclasses import dataclass
from enum import Enum

from Infrastructure.DataTypes.Contracts.AbstractContract import AbstractContract
from Infrastructure.DataTypes.Contracts.SubContracts.SyntheticContract import SyntheticExperiment


@dataclass
class BenchmarkContractAbstract:
    experiment_name: str


class DataGenerators(Enum):
    DATAGOLF = 1,
    DATAGENERATOR = 2,
    PATTERNS = 3


class PolicyGenerators(Enum):
    MFOTLGENERATOR = 1,
    PATTERNS = 1


@dataclass
class SyntheticBenchmarkContract(BenchmarkContractAbstract):
    data_source: DataGenerators
    policy_source: PolicyGenerators
    policy_setup: AbstractContract
    experiment: SyntheticExperiment


@dataclass
class CaseStudyBenchmarkContract(BenchmarkContractAbstract):
    case_study_name: str
