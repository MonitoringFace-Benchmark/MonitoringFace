from abc import ABC, abstractmethod
from typing import AnyStr


class PolicyGeneratorTemplate(ABC):
    @abstractmethod
    def generate_policy(self, policy_contract, time_on=None, time_out=None) -> (int, AnyStr, AnyStr):
        pass
