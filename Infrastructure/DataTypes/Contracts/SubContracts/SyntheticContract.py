from dataclasses import dataclass


@dataclass
class SyntheticExperiment:
    num_operators: list[int]
    num_fvs: list[int]
    num_setting: list[int]
    num_data_set_sizes: list[int]
