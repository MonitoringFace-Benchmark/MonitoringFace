from enum import Enum


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
    GeneralUtilities = 6

