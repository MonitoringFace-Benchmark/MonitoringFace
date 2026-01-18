# Implementation Guidelines

### Authentication Token
To avoid running into rate-limiting issues when pulling images from Github, it is
recommended to set up a personal authentication token. You can add a personal access token by creating
the folder environment in ``Infrastructure/environment`` and adding a file named ``auth_token`` containing your token.

### Implementing a Monitoring Tool
Provide a Dockerfile and tool.properties for your tool. Find the guidelines 
and requirements in the Monitors section in the Archive. 
Implement the runnable Monitoring tool as described in [Monitors/README.md](Monitors/README.md)


### Implement Data and Policy Generators
The implementation guide: [README.md](Builders/ProcessorBuilder/README.md).

### Utilities and Converters
There are no additional guidelines for implementing utilities and converters.