import os

from Infrastructure.Builders.BuilderUtilities import ImageBuildException
from Infrastructure.Builders.ToolBuilder.ToolImageManager import DirectToolImageManager, remote_content_handler, IndirectToolImageManager
from Infrastructure.DataLoader.Resolver import ToolResolver, Location
from Infrastructure.printing import print_headline, print_footline


class ToolManager:
    def __init__(self, tools_to_build, path_to_project):
        print_headline("(Starting) Building ToolManager")
        path_to_build = path_to_project + f"/Infrastructure/build"
        path_to_infra = path_to_project + "/Infrastructure"
        path_to_archive = path_to_project + f"/Archive"

        path_to_monitor = f"{path_to_build}/Monitor"
        os.makedirs(path_to_monitor, exist_ok=True)

        self.images = {}
        failed_builds = []
        for (tool, branch, commit, release) in tools_to_build:
            if commit is None:
                commit = ""
            try:
                if commit:
                    print(f"-> Attempting to build Image {tool} - {branch} @ {commit}")
                else:
                    print(f"-> Attempting to build Image {tool} - {branch}")
                path_to_named_archive = f"{path_to_archive}/Tools/{tool}"
                tl = ToolResolver(tool, path_to_archive, path_to_named_archive, path_to_infra)
                location = tl.resolve()

                # only direct linking, no transitive linking, there is no reason for further indirection
                if location == Location.Unavailable:
                    raise ImageBuildException(f"{tool} does not exists either Local or Remote")
                elif location == Location.Remote:
                    remote_content_handler(path_to_named_archive, path_to_infra, tool)

                linked = tl.symbolic_linked()
                if linked:
                    new_path_to_named_archive = f"{path_to_archive}/Tools/{linked}"
                    new_tl = ToolResolver(linked, path_to_archive, new_path_to_named_archive, path_to_infra)
                    new_location = new_tl.resolve()
                    if location == Location.Unavailable:
                        raise ImageBuildException(f"Linked {linked} does not exists either Local or Remote")
                    elif new_location == Location.Remote:  # local need no further treatment
                        remote_content_handler(new_path_to_named_archive, path_to_infra, new_tl)
                    self.images[(tool, branch, commit)] = IndirectToolImageManager(tool, linked, branch, commit, release,
                                                                           path_to_build, path_to_archive,
                                                                           path_to_infra, new_location)
                else:
                    self.images[(tool, branch, commit)] = DirectToolImageManager(tool, branch, release, commit, path_to_build,
                                                                         path_to_archive, path_to_infra, location)
                print(f"    -> (Success)")
            except ImageBuildException:
                print(f"-> (Failure)")
                failed_builds += [f"{tool} - {branch}"]

        if failed_builds:
            print(f"\nFailed to build:")
            for fail in failed_builds:
                print(f" - {fail}")

        print_footline("(Finished) Building ToolManager")

    def get_image(self, tool, branch, commit):
        if commit is None:
            commit = ""
        return self.images.get((tool, branch, commit))
