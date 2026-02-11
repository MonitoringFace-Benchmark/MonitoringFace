from abc import abstractmethod, ABC
from enum import Enum
from typing import List, Tuple, Optional, Dict

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats


class SeedType(Enum):
    RANDOM = 1
    FIXED = 2
    DETERMINISTIC = 3


class Coordinator(ABC):
    @abstractmethod
    def build(self):
        pass

    @abstractmethod
    def finger_print(self) -> Dict[str, str]:
        pass

    @abstractmethod
    def time_out(self) -> Optional[int]:
        pass

    @abstractmethod
    def iterate_settings(self) -> List[Tuple[int, str, str, InputOutputTraceFormats, str, InputOutputPolicyFormats, Optional[str], Optional[str]]]:
        pass
