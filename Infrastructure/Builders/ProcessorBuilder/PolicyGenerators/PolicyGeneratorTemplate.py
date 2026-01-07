from abc import ABC, abstractmethod
from typing import AnyStr, Tuple


class PolicyGeneratorTemplate(ABC):
    @abstractmethod
    def generate_policy(self, policy_contract, time_on=None, time_out=None) -> Tuple[Tuple[int, AnyStr, AnyStr], int]:
        pass
