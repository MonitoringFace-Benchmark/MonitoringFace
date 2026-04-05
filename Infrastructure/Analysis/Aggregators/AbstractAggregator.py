from abc import ABC, abstractmethod

from Infrastructure.DataTypes.Types.custome_type import OnlineOffline


class AbstractAggregator(ABC):
    @abstractmethod
    def to_csv(self, path: str, name: str) -> None:
        pass


def dispatch_aggregator(mode: OnlineOffline) -> AbstractAggregator:
    if mode == OnlineOffline.Online:
        from Infrastructure.Analysis.Aggregators.ResultAggregatorOnline import ResultAggregatorOnline
        return ResultAggregatorOnline()
    else:
        from Infrastructure.Analysis.Aggregators.ResultAggregatorOffline import ResultAggregatorOffline
        return ResultAggregatorOffline()
