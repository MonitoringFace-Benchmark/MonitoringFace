import subprocess
import urllib.request

try:
    urllib.request.urlopen('http://www.google.com', timeout=3).getcode()
except urllib.request.HTTPError as e:
    print("Internet connection is missing")

docker_ok = subprocess.call(['docker', 'info'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0

if not docker_ok:
    print("Docker is not running")

if docker_ok:
    print("OK")
    pass # call logic

if __name__ == "__main__":
    pass
