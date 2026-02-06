from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple, List

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats


class PolicyTransformationException(Exception):
    pass


class PolicyConverterTemplate(ABC):
    @abstractmethod
    def auto_convert(
            self, path_to_folder: str, input_file: str, path_to_output_folder: str, output_file: str,
            source: InputOutputPolicyFormats, target: InputOutputPolicyFormats, params: Dict[str, Any]
    ):
        raise NotImplemented()

    @staticmethod
    @abstractmethod
    def conversion_scheme() -> List[Tuple[InputOutputPolicyFormats, InputOutputPolicyFormats]]:
        pass
