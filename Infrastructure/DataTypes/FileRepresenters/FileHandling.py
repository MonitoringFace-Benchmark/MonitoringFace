import os.path
from typing import AnyStr, Optional


def to_file(path, content, name, ending=None):
    file_name = path + "/" + (f"{name}.{ending}" if ending else name)
    with open(file_name, mode="w") as f:
        f.write(content)


def from_file(path: AnyStr):
    if os.path.exists(path):
        with open(path, mode="r") as f:
            return f.read()
    return None


def get_auth_token(path_to_infra: AnyStr) -> Optional[AnyStr]:
    environment_path = f"{path_to_infra}/environment"
    if not os.path.exists(environment_path):
        os.mkdir(environment_path)
        return None
    auth_token_path = f"{environment_path}/auth_token"
    return from_file(auth_token_path)
