from abc import ABC, abstractmethod


class AbstractContract(ABC):
    @abstractmethod
    def default_contract(self):
        pass

    @abstractmethod
    def instantiate_contract(self, params):
        pass
