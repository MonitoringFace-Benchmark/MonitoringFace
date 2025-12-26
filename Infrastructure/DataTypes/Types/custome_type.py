from enum import Enum
from typing import AnyStr


class ExperimentType(Enum):
    Pattern = 1
    Signature = 2
    CaseStudy = 3


class BranchOrRelease(Enum):
    Release = 0
    Branch = 1


class Processor(Enum):
    DataGenerators = 1,
    DataConverters = 2,
    PolicyGenerators = 3,
    PolicyConverters = 4,
    CaseStudies = 5,
    Benchmark = 6,
    GeneralUtilities = 7


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
    elif p == Processor.Benchmark:
        return "Benchmark"
    else:
        return "GeneralUtilities"
