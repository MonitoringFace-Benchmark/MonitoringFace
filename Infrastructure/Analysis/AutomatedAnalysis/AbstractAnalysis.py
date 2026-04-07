from typing import Dict

import pandas as pd

from Infrastructure.Analysis.Aggregators.AbstractAggregator import AbstractAggregator
from Infrastructure.Analysis.Aggregators.ResultAggregatorOffline import ResultAggregatorOffline
from Infrastructure.Analysis.Aggregators.ResultAggregatorOnline import ResultAggregatorOnline
from Infrastructure.Analysis.AutomatedAnalysis.BaseAnalysis import AbstractAnalysis


def dispatch_analysis(aggregator: AbstractAggregator) -> AbstractAnalysis:
    if isinstance(aggregator, ResultAggregatorOffline):
        from Infrastructure.Analysis.AutomatedAnalysis.AnalysisOffline import AnalysisOffline
        return AnalysisOffline()
    if isinstance(aggregator, ResultAggregatorOnline):
        from Infrastructure.Analysis.AutomatedAnalysis.AnalysisOnline import AnalysisOnline
        return AnalysisOnline()
    raise TypeError(f"Unsupported aggregator type for analysis: {type(aggregator)}")


def run_analysis(aggregator: AbstractAggregator) -> Dict[str, pd.DataFrame]:
    return dispatch_analysis(aggregator).run(aggregator)
