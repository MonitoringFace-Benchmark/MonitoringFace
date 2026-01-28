from abc import ABC, abstractmethod
from typing import AnyStr, Tuple, Dict, Any


class PolicyGeneratorTemplate(ABC):
    @abstractmethod
    def generate_policy(self, policy_contract: Dict[AnyStr, Any], time_on=None, time_out=None) -> Tuple[Tuple[int, AnyStr, AnyStr], int]:
        pass
