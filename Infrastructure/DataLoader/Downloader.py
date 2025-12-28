from abc import ABC, abstractmethod
from typing import Optional, Any, AnyStr
import requests

from Infrastructure.DataTypes.FileRepresenters.FileHandling import get_auth_token
from Infrastructure.constants import DOWNLOADER_ERR_MSG


class Downloader(ABC):
    err = DOWNLOADER_ERR_MSG
    url = "https://api.github.com/repos/MonitoringFace-Benchmark/MonitoringFace/contents/Archive"

    def __init__(self, path_to_infra):
        self.path_to_infra = path_to_infra

    @abstractmethod
    def get_all_names(self):
        pass

    @abstractmethod
    def get_content(self, name):
        pass


class DataGeneratorDownloader(Downloader):
    def __init__(self, path_to_infra):
        super().__init__(path_to_infra)

    def get_all_names(self):
        return url_dir_getter(self.url, "/DataGenerators", self.err)

    def get_content(self, name):
        i = url_getter(self.url, f"/DataGenerators/{name}", f"Data generator {name} is not reachable", self.path_to_infra)[0]
        return requests.get(i["download_url"]).content.decode()


class DataConverterDownloader(Downloader):
    def __init__(self, path_to_infra):
        super().__init__(path_to_infra)

    def get_all_names(self):
        return url_dir_getter(self.url, "/DataConverters", self.err)

    def get_content(self, name):
        i = url_getter(self.url, f"/DataConverters/{name}", f"Data converter {name} is not reachable", self.path_to_infra)[0]
        return requests.get(i["download_url"]).content.decode()


class PolicyGeneratorDownloader(Downloader):
    def __init__(self, path_to_infra):
        super().__init__(path_to_infra)

    def get_all_names(self):
        return url_dir_getter(self.url, "/PolicyGenerators", self.err)

    def get_content(self, name):
        i = url_getter(self.url, f"/PolicyGenerators/{name}", f"Policy generator {name} is not reachable", self.path_to_infra)[0]
        return requests.get(i["download_url"]).content.decode()


class PolicyConverterDownloader(Downloader):
    def __init__(self, path_to_infra):
        super().__init__(path_to_infra)

    def get_all_names(self):
        return url_dir_getter(self.url, "/PolicyConverters", self.err)

    def get_content(self, name):
        i = url_getter(self.url, f"/PolicyConverters/{name}", f"Policy converter {name} is not reachable", self.path_to_infra)[0]
        return requests.get(i["download_url"]).content.decode()


class GeneralUtilitiesDownloader(Downloader):
    def __init__(self, path_to_infra):
        super().__init__(path_to_infra)

    def get_all_names(self):
        return url_dir_getter(self.url, "/GeneralUtilities", self.err)

    def get_content(self, name):
        i = url_getter(self.url, f"/GeneralUtilities/{name}", f"General Utility {name} is not reachable", self.path_to_infra)[0]
        return requests.get(i["download_url"]).content.decode()


class CaseStudiesDownloader(Downloader):
    def __init__(self, path_to_infra):
        super().__init__(path_to_infra)

    def get_all_names(self):
        return url_dir_getter(self.url, "/CaseStudies", self.err)

    def get_content(self, name):
        i = url_getter(self.url, f"/CaseStudies/{name}", f"Case Study {name} is not reachable", self.path_to_infra)[0]
        return requests.get(i["download_url"]).content.decode()


class BenchmarkDownloader(Downloader):
    def __init__(self, path_to_infra):
        super().__init__(path_to_infra)

    def get_all_names(self):
        token = get_auth_token(self.path_to_infra)
        return url_dir_getter_files(self.url, "/Benchmarks", token, self.err)

    def get_content(self, name):
        i = url_getter(self.url, f"/Benchmarks/{name}", f"Benchmark {name} is not reachable", self.path_to_infra)
        return requests.get(i["download_url"]).content.decode()


class MonitoringFaceDownloader(Downloader):
    def __init__(self, path_to_infra):
        super().__init__(path_to_infra)

    def get_all_names(self):
        return url_dir_getter(self.url, "/Tools", self.err)

    def get_content(self, name):
        res = {}
        for i in url_getter(self.url, f"/Tools/{name}", self.err, self.path_to_infra):
            res[i["name"]] = requests.get(i["download_url"]).content.decode()
        return res


def url_getter(url, addon, err, path_to_infra: AnyStr) -> Optional[Any]:
    try:
        auth_token = get_auth_token(path_to_infra=path_to_infra)
        headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else None
        response = requests.get(url + addon, headers=headers)
        response.raise_for_status()
        contents = response.json()
        return contents
    except requests.exceptions.RequestException as e:
        print(f"{err}: {e}")
        return None


def url_dir_getter(url, addon, err) -> Optional[list]:
    try:
        response = requests.get(url + addon)
        response.raise_for_status()
        return [item["name"] for item in response.json() if item['type'] == "dir"]
    except requests.exceptions.RequestException as e:
        print(f"{err}: {e}")
        return None


def url_dir_getter_files(url, addon, token, err) -> Optional[list]:
    headers = {}
    if token:
        headers["Authorization"] = f"token {token}"
    init_path = "Archive/Benchmarks"
    url += addon

    def remove_relative_path(path: str):
        return path.removeprefix(init_path)

    def get(path):
        response = requests.get(url + path, headers=headers)
        response.raise_for_status()
        status_code = response.status_code
        if status_code == 403:
            raise print("Rate limit exceeded, supply github token in Infrastructure/environment/auth_token")
        elif status_code != 200:
            raise ValueError(f"Unable to retrieve content from Archive/Benchmarks; returned code {status_code}")

        inner_files = []
        for item in response.json():
            if item["type"] == "file":
                inner_files.append(item["path"])
            elif item["type"] == "dir":
                inner_files.extend(get(remove_relative_path(item["path"])))
        return inner_files

    try:
        return [s.removeprefix(init_path + "/") for s in get("")]
    except requests.exceptions.RequestException as e:
        print(f"{err}: {e}")
        return None
    except ValueError as e:
        print(f"{err}: {e}")
        return None
