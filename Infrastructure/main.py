"""
Main entry point for MonitoringFace benchmark framework
Provides CLI for running experiments from YAML configuration files
"""
import subprocess
import urllib.request
import sys

from Infrastructure.cli import main as cli_main


def check_prerequisites():
    """Check if prerequisites (internet, Docker) are available"""
    # Check internet connection
    try:
        urllib.request.urlopen('http://www.google.com', timeout=3).getcode()
    except (urllib.request.HTTPError, urllib.request.URLError) as e:
        print("Warning: Internet connection may be unavailable")
        print(f"  {e}")
    
    # Check Docker
    docker_ok = subprocess.call(['docker', 'info'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) == 0
    
    if not docker_ok:
        print("Error: Docker is not running", file=sys.stderr)
        print("Please start Docker before running experiments", file=sys.stderr)
        sys.exit(1)
    
    return docker_ok


if __name__ == "__main__":
    # Check prerequisites
    check_prerequisites()
    
    # Run CLI
    cli_main()
