from abc import ABC, abstractmethod
from typing import AnyStr


class DataConverterTemplate(ABC):
    @abstractmethod
    def convert(self, path_to_folder: AnyStr, data_file: AnyStr, tool: AnyStr, name: AnyStr, dest: AnyStr, params):
        pass
