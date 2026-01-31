from abc import ABC, abstractmethod
from typing import AnyStr, List, Tuple, Dict, Any

from Infrastructure.InputOutputFormats import InputOutputFormats


class DataConverterTemplate(ABC):
    @abstractmethod
    def convert(self, path_to_folder: AnyStr, data_file: AnyStr, tool: AnyStr, name: AnyStr, dest: AnyStr, params):
        pass

    @abstractmethod
    def auto_convert(
            self, path_to_folder: str, input_file: str, path_to_output_folder: str, output_file: str,
            source: InputOutputFormats, target: InputOutputFormats, cmd_params: List[str], general_params: Dict[str, Any]
    ):
        raise NotImplemented()

    @staticmethod
    @abstractmethod
    def conversion_scheme() -> List[Tuple[InputOutputFormats, InputOutputFormats]]:
        pass
