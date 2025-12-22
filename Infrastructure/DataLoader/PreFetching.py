import requests
from abc import ABC, abstractmethod

from Infrastructure.DataTypes.FileRepresenters.FileHandling import get_auth_token


class RepoFetcher(ABC):
    @abstractmethod
    def get_branches(self):
        pass

    @abstractmethod
    def get_releases(self):
        pass

    @abstractmethod
    def get_hash(self, identifier):
        pass


class BitBucketFetcher(RepoFetcher):
    def __init__(self, owner, repo):
        self.url = f"https://api.bitbucket.org/2.0/repositories/{owner}/{repo}"

    def get_branches(self):
        url = self.url + "/refs/branches"
        all_branches = []
        try:
            while url:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                branch_names = [branch['name'] for branch in data['values']]
                all_branches.extend(branch_names)
                url = data.get('next')
            return all_branches
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while fetching branches: {e}")
            return None

    def get_releases(self):
        url = self.url + "/refs/tags"
        all_tags = []
        try:
            while url:
                response = requests.get(url)
                response.raise_for_status()
                data = response.json()
                all_tags.extend(data['values'])
                url = data.get('next')
            return all_tags
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while fetching tags/releases: {e}")
            return None

    def get_hash(self, identifier):
        try:
            response = requests.get(self.url + f"/refs/branches/{identifier}")
            response.raise_for_status()
            branch_data = response.json()
            return branch_data['target']['hash']
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while fetching the branch hash: {e}")
            return None


class GitHubFetcher(RepoFetcher):
    def __init__(self, owner, repo, path_to_infra):
        self.url = f"https://api.github.com/repos/{owner}/{repo}"
        auth_token = get_auth_token(path_to_infra=path_to_infra)
        self.header = {"Authorization": f"Bearer {auth_token}"} if auth_token else None

    def get_branches(self):
        try:
            response = requests.get(self.url + "/branches", headers=self.header)
            response.raise_for_status()
            branches_data = response.json()
            branch_names = [branch['name'] for branch in branches_data]
            return branch_names
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while fetching branches: {e}")
            return None

    def get_releases(self):
        try:
            response = requests.get(self.url + "/releases", headers=self.header)
            response.raise_for_status()
            releases_data = response.json()
            return releases_data
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while fetching releases: {e}")
            return None

    def get_hash(self, identifier):
        try:
            response = requests.get(self.url + f"/branches/{identifier}", headers=self.header)
            response.raise_for_status()
            branch_data = response.json()
            return branch_data['commit']['sha']
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while fetching the branch hash: {e}")
            return None
        except KeyError:
            print("Unexpected response structure from GitHub API.")
            return None


class GitLabFetcher(RepoFetcher):
    def __init__(self, base, repo):
        self.url = f"https://{base}/api/v4/projects/{repo}"

    def get_branches(self):
        try:
            response = requests.get(self.url + "/repository/branches")
            response.raise_for_status()
            branches_data = response.json()
            branch_names = [branch['name'] for branch in branches_data]
            return branch_names
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while fetching branches: {e}")
            return None

    def get_releases(self):
        try:
            response = requests.get(self.url + "/releases")
            response.raise_for_status()
            releases_data = response.json()
            return releases_data
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while fetching releases: {e}")
            return None

    def get_hash(self, identifier):
        try:
            response = requests.get(self.url + f"/repository/branches/{identifier}")
            response.raise_for_status()
            branch_data = response.json()
            return branch_data['commit']['id']
        except requests.exceptions.RequestException as e:
            print(f"An error occurred while fetching the branch hash: {e}")
            return None


def init_repo_fetcher(platform, owner, repo, path_to_infra):
    if platform == "GitLab":
        return GitLabFetcher(owner, repo)
    elif platform == "GitHub":
        return GitHubFetcher(owner, repo, path_to_infra)
    else:
        return BitBucketFetcher(owner, repo)
