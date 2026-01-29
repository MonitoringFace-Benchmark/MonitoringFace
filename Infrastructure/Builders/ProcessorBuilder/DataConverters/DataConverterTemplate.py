from abc import ABC, abstractmethod
from typing import AnyStr, List, Tuple

from Infrastructure.InputOutputFormats import InputOutputFormats


class DataConverterTemplate(ABC):
    @abstractmethod
    def convert(self, path_to_folder: AnyStr, data_file: AnyStr, tool: AnyStr, name: AnyStr, dest: AnyStr, params):
        pass

    @staticmethod
    @abstractmethod
    def conversion_scheme() -> List[Tuple[InputOutputFormats, InputOutputFormats]]:
        pass
