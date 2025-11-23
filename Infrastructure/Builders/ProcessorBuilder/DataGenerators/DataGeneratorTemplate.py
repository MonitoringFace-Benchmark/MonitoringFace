from abc import ABC, abstractmethod


class DataGeneratorTemplate(ABC):
    @abstractmethod
    def run_generator(self, contract_inner, time_on=None, time_out=None):
        pass

    @abstractmethod
    def check_policy(self, path_inner, signature, formula) -> bool:
        pass
