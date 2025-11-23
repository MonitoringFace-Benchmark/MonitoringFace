from abc import ABC, abstractmethod


class PolicyGeneratorTemplate(ABC):

    @abstractmethod
    def generate_policy(self, policy_contract, time_on=None, time_out=None):
        pass
