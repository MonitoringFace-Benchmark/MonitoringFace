from abc import ABC, abstractmethod


class CaseStudyTemplate(ABC):
    @abstractmethod
    def run_generator(self, generic_contract, time_on=None, time_out=None):
        pass
