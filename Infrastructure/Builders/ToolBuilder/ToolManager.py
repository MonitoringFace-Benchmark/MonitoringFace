from Infrastructure.Builders.BuilderUtilities import ImageBuildException
from Infrastructure.Builders.ToolBuilder.ToolImageManager import ToolImageManager
from Infrastructure.printing import print_headline, print_footline


class ToolManager:
    def __init__(self, tools_to_build, path_to_project):
        print_headline("(Starting) Building ToolManager")
        path_to_build = path_to_project + f"/Infrastructure/build"
        path_to_infra = path_to_project + "/Infrastructure"
        path_to_archive = path_to_project + f"/Archive"

        self.images = {}
        failed_builds = []
        for (tool, branch, release) in tools_to_build:
            try:
                print(f"-> Attempting to build Image {tool} - {branch}")
                self.images[(tool, branch)] = ToolImageManager(tool, branch, release, path_to_build, path_to_archive, path_to_infra)
                print(f"    -> (Success)")
            except ImageBuildException:
                print(f"-> (Failure)")
                failed_builds += [f"{tool} - {branch}"]

        if failed_builds:
            print(f"\nFailed to build:")
            for fail in failed_builds:
                print(f" - {fail}")

        print_footline("(Finished) Building ToolManager")

    def get_image(self, tool, branch):
        return self.images.get((tool, branch))
