from Infrastructure.Builders.ToolBuilder.ToolImageManager import ToolImageManager


class ToolManager:
    def __init__(self, tools_to_build, path_to_build, path_to_archive):
        print("\n" + "="*20 + " Build tools " + "="*20)
        self.images = {}
        for (tool, branch, release) in tools_to_build:
            self.images[(tool, branch)] = ToolImageManager(tool, branch, release, path_to_build, path_to_archive)
        print("="*53)

    def get_image(self, tool, branch):
        return self.images.get((tool, branch))
