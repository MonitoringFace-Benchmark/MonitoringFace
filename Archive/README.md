# Purpose
The archive hosts Tools (Monitors, Enforcers) and all needed in the creation, execution and analysis of the Benchmark.
The first chapter introduces the available Categories followed by the implementation details and conventions that each Category entails.


## Categories
The archive should be well-structured and hence all Software should be assigned accordingly.

### Tools
Software that given policies and data either monitors or enforces properties.

### DataGenerators
Software that given some specifications creates traces/logs such as CSV-files or Logs in MonPoly-format.

### DataConverters
Software that transforms existing traces/logs into a different representation but retain the meaning. For example from CSV to MonPoly-format or vice-versa.

### PolicyGenerators
Software that given some specifications creates policies such as MFOTL formulas. 

### PolicyConverters
Software that transforms policies from one format to another.

### CaseStudies
Software creating predefined structures and instructions.

### Utilities
All software that is needed with in the other categories but doesn't fit in the other categories.

## Conventions
Guidelines and conventions to add software to the archive.
### Tools
1. Dockerfile:
    1. Uses the appropriate base image (supporting the correct version of the tech stack etc). 
    2. Imports all needed build tools (git, cargo, gcc, opam etc.) 
    3. Clones the repository, the git clone command should use a "ARG GIT_BRANCH" variable that allows the framework to download and run different branches and releases. 
    4. Build the tool and move into the final image.
    5. The final image needs to provide "/usr/bin/time"
    6. Entrypoint should be the name of the binary in lower case.
2. tool.properties:
   1. name= ... (original name of the tool, including lower and upper characters) 
   2. git= ... (the version control that the repository is hosted on) 
   3. owner= ... (the name of the user or organisation owning the repo) 
   4. repo= ... (name of the repo)

### DataGenerators

