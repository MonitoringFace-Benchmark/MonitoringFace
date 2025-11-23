from Infrastructure.DataLoader.Downloader import (
    DataGeneratorDownloader, DataConverterDownloader,
    PolicyGeneratorDownloader, PolicyConverterDownloader,
    GeneralUtilitiesDownloader, CaseStudiesDownloader
)
from Infrastructure.DataTypes.Types.custome_type import Processor


class DataLoader:
    def __init__(self, p):
        if p == Processor.DataGenerators:
            self.downloader = DataGeneratorDownloader()
        elif p == Processor.DataConverters:
            self.downloader = DataConverterDownloader()
        elif p == Processor.PolicyGenerators:
            self.downloader = PolicyGeneratorDownloader()
        elif p == Processor.PolicyConverters:
            self.downloader = PolicyConverterDownloader()
        elif p == Processor.CaseStudies:
            self.downloader = CaseStudiesDownloader()
        else:
            self.downloader = GeneralUtilitiesDownloader()

    def get_all_names(self):
        return self.downloader.get_all_names()

    def get_content(self, name):
        return self.downloader.get_content(name)
