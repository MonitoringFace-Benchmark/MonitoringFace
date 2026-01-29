from abc import ABC, abstractmethod
from typing import AnyStr, Dict, Any, Tuple, List

from Infrastructure.InputOutputFormats import InputOutputFormats


class DataGeneratorTemplate(ABC):
    @abstractmethod
    def run_generator(self, contract_inner: Dict[AnyStr, Any], time_on=None, time_out=None) -> Tuple[int, AnyStr, int]:
        pass

    @abstractmethod
    def check_policy(self, path_inner, signature, formula) -> bool:
        pass

    @staticmethod
    @abstractmethod
    def output_formats() -> List[InputOutputFormats]:
        pass
