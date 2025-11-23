from Infrastructure.DataLoader.Downloader import MonitoringFaceDownloader


class ToolLoader:
    def __init__(self):
        self.down_loader = MonitoringFaceDownloader()

    def get_all_tool_names(self):
        return self.down_loader.get_all_names()

    def get_tool(self, name):
        return self.down_loader.get_content(name)
