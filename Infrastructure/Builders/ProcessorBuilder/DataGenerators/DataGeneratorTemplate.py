from abc import ABC, abstractmethod
from typing import AnyStr, Dict, Any, Tuple, List

from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats


class DataGeneratorTemplate(ABC):
    @abstractmethod
    def run_generator(self, contract_inner: Dict[AnyStr, Any], time_on=None, time_out=None) -> Tuple[int, AnyStr, int]:
        pass

    @abstractmethod
    def check_policy(self, path_inner, signature, formula) -> bool:
        pass

    @staticmethod
    @abstractmethod
    def output_formats() -> List[InputOutputTraceFormats]:
        pass
