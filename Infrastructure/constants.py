DOWNLOADER_ERR_MSG = "An error occurred while fetching the directory tree"

DATAGOLF_POLICY_CHECK = "[Main] The inputs satisfy all constraints."

IMAGE_POSTFIX = "_mf_image"

BUILD_ARG_GIT_BRANCH = "GIT_BRANCH"

WORKDIR_KEY = "workdir"
WORKDIR_VAL = "/data"

SYMLINK_KEY = "symbolic_link"

DOCKERFILE_KEY = "Dockerfile"
DOCKERFILE_VALUE = "/Dockerfile"

PROP_FILES_KEY = "tool.properties"
PROP_FILES_VALUE = "/tool.properties"

META_FILE_VALUE = "/meta.properties"

ORACLE_KEY = "oracle"
ENTRYPOINT_KEY = "entrypoint"
VOLUMES_KEY = "volumes"
COMMAND_KEY = "command"

GIT_KEY = "git"
OWNER_KEY = "owner"
REPO_KEY = "repo"
VERSION_KEY = "version"
BRANCH_KEY = "branch"


FINGERPRINT_DATA = "fingerprint_data"
FINGERPRINT_EXPERIMENT = "fingerprint_experiment"

PLACEHOLDER_EVENT = "Placeholder()"

BENCHMARK_BUILDING_OFFSET = (" " * 8)

# Pretty Printing
LENGTH = 80
HEADER_ROW = "=" * LENGTH

LINE_BUFFER = 100


class Config:
    verbose = False

    @classmethod
    def set_verbose(cls, value: bool):
        cls.verbose = value

    @classmethod
    def is_verbose(cls) -> bool:
        return cls.verbose


class Measure:
    measure = True

    @classmethod
    def set_measure(cls, value: bool):
        cls.measure = value

    @classmethod
    def is_measure(cls) -> bool:
        return cls.measure
