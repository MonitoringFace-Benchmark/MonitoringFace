from abc import abstractmethod, ABC
from enum import Enum
from typing import List, Tuple, Optional

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
    def iterate_settings(self) -> List[Tuple[int, str, InputOutputTraceFormats, str, InputOutputPolicyFormats, Optional[str], Optional[str]]]:
        pass
