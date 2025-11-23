from abc import ABC, abstractmethod
from typing import AnyStr


# using datagolf as generator sets oracle true, verimon on the other hand needs to actively set the result.out
# The time limiter must be verimon when set as oracle in other cases it can be chosen freely
# datagolf most likely just reformats the file instead of preprocessing and computation
# or the generator is the orcale from the beginning, the generator uses the oracle directly

# the oracle has to be passed to the generator builder


class AbstractOracleTemplate(ABC):
    def __init__(self):
        pass

    @abstractmethod
    def pre_process_data(self, path_to_folder: AnyStr, data_file: AnyStr, signature_file: AnyStr, formula_file: AnyStr):
        pass

    @abstractmethod
    def compute_result(self, time_on=None, time_out=None) -> (AnyStr, int):
        pass

    @abstractmethod
    def post_process_data(self, std_out_str, output_file_name):
        pass
