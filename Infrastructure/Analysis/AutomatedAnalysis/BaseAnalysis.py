from abc import ABC, abstractmethod
from typing import Dict

import pandas as pd

from Infrastructure.Analysis.Aggregators.AbstractAggregator import AbstractAggregator


class AbstractAnalysis(ABC):
    @abstractmethod
    def run(self, aggregator: AbstractAggregator) -> Dict[str, pd.DataFrame]:
        pass
