from abc import ABC, abstractmethod
from typing import AnyStr, Tuple, Dict, Any, List

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats


class PolicyGeneratorTemplate(ABC):
    @abstractmethod
    def generate_policy(self, policy_contract: Dict[AnyStr, Any], time_on=None, time_out=None) -> Tuple[int, AnyStr, AnyStr]:
        pass

    @staticmethod
    @abstractmethod
    def output_format() -> InputOutputPolicyFormats:
        pass
