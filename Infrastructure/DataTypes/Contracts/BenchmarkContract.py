from dataclasses import dataclass

from Infrastructure.Builders.ProcessorBuilder.DataGenerators.DataGeneratorTemplate import DataGeneratorTemplate
from Infrastructure.Builders.ProcessorBuilder.PolicyGenerators.PolicyGeneratorTemplate import PolicyGeneratorTemplate
from Infrastructure.DataTypes.Contracts.AbstractContract import AbstractContract
from Infrastructure.DataTypes.Contracts.SubContracts.SyntheticContract import SyntheticExperiment


@dataclass
class BenchmarkContractAbstract:
    experiment_name: str


@dataclass
class SyntheticBenchmarkContract(BenchmarkContractAbstract):
    data_source: DataGeneratorTemplate
    policy_source: PolicyGeneratorTemplate
    policy_setup: AbstractContract
    experiment: SyntheticExperiment


@dataclass
class CaseStudyBenchmarkContract(BenchmarkContractAbstract):
    case_study_name: str
