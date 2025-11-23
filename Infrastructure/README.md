# MonitoringFaceBootloader


## Prerequisites

Docker must be installed and running on your system. You can download Docker from
[here](https://www.docker.com/get-started).

    - RAM: 6GB
    - 4 CPU cores
    - Swap memory: 1GB
    - Disk space: 64GB
    - Allow Docker to access the folder where MonitoringFaceBootloader is located under Settings> Resources > File Sharing.

Python 3.9 or higher must be installed. You can download Python from
[here](https://www.python.org/downloads/).


## Running the Evaluator

Create a virtual environment and install the required packages, use the command:

````
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Congifure the Evaluator.py script, use the command from the folder containing the MonitoringFaceBootloader:

```
python3 -m MonitoringFaceBootloader.Evaluator.Evaluator 
```
