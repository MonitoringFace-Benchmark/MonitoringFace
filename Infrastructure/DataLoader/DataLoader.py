from Infrastructure.DataLoader.Downloader import (
    DataGeneratorDownloader, DataConverterDownloader,
    PolicyGeneratorDownloader, PolicyConverterDownloader,
    GeneralUtilitiesDownloader, CaseStudiesDownloader, BenchmarkDownloader
)
from Infrastructure.DataTypes.Types.custome_type import Processor


class DataLoader:
    def __init__(self, p, path_to_infra):
        if p == Processor.DataGenerators:
            self.downloader = DataGeneratorDownloader(path_to_infra)
        elif p == Processor.DataConverters:
            self.downloader = DataConverterDownloader(path_to_infra)
        elif p == Processor.PolicyGenerators:
            self.downloader = PolicyGeneratorDownloader(path_to_infra)
        elif p == Processor.PolicyConverters:
            self.downloader = PolicyConverterDownloader(path_to_infra)
        elif p == Processor.CaseStudies:
            self.downloader = CaseStudiesDownloader(path_to_infra)
        elif p == Processor.Benchmark:
            self.downloader = BenchmarkDownloader(path_to_infra)
        elif p == Processor.GeneralUtilities:
            self.downloader = GeneralUtilitiesDownloader(path_to_infra)
        else:
            raise NotImplementedError(f"Not implemented {p}")

    def get_all_names(self):
        return self.downloader.get_all_names()

    def get_content(self, name):
        return self.downloader.get_content(name)
