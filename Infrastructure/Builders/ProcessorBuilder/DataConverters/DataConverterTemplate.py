from abc import ABC, abstractmethod
from typing import AnyStr, List, Tuple, Dict, Any

from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats


class DataConverterTemplate(ABC):
    @abstractmethod
    def convert(self, path_to_folder: AnyStr, data_file: AnyStr, tool: AnyStr, name: AnyStr, dest: AnyStr, params):
        pass

    @abstractmethod
    def auto_convert(
            self, path_to_folder: str, input_file: str, path_to_output_folder: str, output_file: str,
            source: InputOutputTraceFormats, target: InputOutputTraceFormats, params: Dict[str, Any]
    ):
        raise NotImplemented()

    @staticmethod
    @abstractmethod
    def conversion_scheme() -> List[Tuple[InputOutputTraceFormats, InputOutputTraceFormats]]:
        pass
