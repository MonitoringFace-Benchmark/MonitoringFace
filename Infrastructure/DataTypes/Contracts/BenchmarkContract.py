from dataclasses import dataclass
from enum import Enum

from Infrastructure.DataTypes.Contracts.AbstractContract import AbstractContract


class BenchmarkContractAbstract:
    pass


class DataGenerators(Enum):
    DATAGOLF = 1,
    DATAGENERATOR = 2,
    CASESTUDY = 3


class PolicyGenerators(Enum):
    MFOTLGENERATOR = 1,
    PATTERNS = 1


@dataclass
class SyntheticBenchmarkContract(BenchmarkContractAbstract):
    name: str
    data_source: DataGenerators
    policy_source: PolicyGenerators
    policy_setup: AbstractContract


@dataclass
class CaseStudyBenchmarkContract(BenchmarkContractAbstract):
    name: str
    data_source: DataGenerators
    case_study_name: str


def build_synthetic_contract(name, data, policy, policy_setup, data_setup):
    contract = SyntheticBenchmarkContract
    contract.name = name
    contract.data_source = data
    contract.policy_source = policy
    contract.policy_setup = policy_setup
    contract.data_setup = data_setup
    return contract


def build_case_study_contract(data, policy, name):
    contract = CaseStudyBenchmarkContract
    contract.name = name
    contract.data_source = data
    contract.policy_source = policy
    return contract
