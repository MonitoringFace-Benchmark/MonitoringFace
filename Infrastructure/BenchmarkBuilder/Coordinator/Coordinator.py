from abc import abstractmethod, ABC
from enum import Enum
from typing import List, Tuple, Optional, Dict

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.Oracles.AbstractOracleTemplate import AbstractOracleTemplate


class SeedType(Enum):
    RANDOM = 1
    FIXED = 2
    DETERMINISTIC = 3


class Coordinator(ABC):
    def __init__(self, path_manager: PathManager, oracle: Optional[AbstractOracleTemplate] = None):
        self.path_manager = path_manager
        self.oracle = oracle

    @abstractmethod
    def build(self):
        pass

    @abstractmethod
    def finger_print(self) -> Dict[str, str]:
        pass

    @abstractmethod
    def short_cutting(self):
        pass

    @abstractmethod
    def time_out(self) -> Optional[int]:
        pass

    @abstractmethod
    def iterate_settings(self) -> List[Tuple[int, str, str, InputOutputTraceFormats, str, InputOutputPolicyFormats, Optional[str], Optional[str]]]:
        pass

    def add_path(self, path_id: str, path: str):
        self.path_manager.add_path(path_id, path)

    def get_path(self, path_id: str) -> Optional[str]:
        return self.path_manager.get_path(path_id)

    def get_path_manager(self) -> PathManager:
        return self.path_manager

    def get_oracle(self) -> Optional[AbstractOracleTemplate]:
        return self.oracle

