# Implementation Guidelines


### PolicyGenerators
Provide a Dockerfile and tool.properties for your tool. Find the guidelines 
and requirements in the PolicyGenerators section in the Archive.

Navigate to ``YOUR_PATH_TO/MonitoringFace/Infrastructure/Builders/ProcessorBuilder``, 
in case the category of your tool is not available yet create a new folder with 
the name of your category in camel-case. 

In the folder create a subfolder with a unique name in camel-case ending with the type of your tool, 
e.g., ``PolicyGeneratorContract`` or ``CSVtoTSVConverter``.

Add an ``__init__.py`` file to the folder. Add two files the contract defining all parameters and option for
the tool, the file is named ``<YourToolName>Contract.py``. The second file is the implementation of the builder
named ``<YourToolName><Type>.py``.

In the contract file define a dataclass named ``<YourToolName>Contract`` that inherits from 
``AbstractContract`` located in ``MonitoringFace.DataTypes.Contracts.AbstractContract.py``.
The inheriting class requires the implementation of two methods:
1. ``default_contract()``: populates all the fields of the contract with reasonable default values.
2. ``instantiate_contract(params: Dict[str, Any])``: populates all the fields of the contract with the values
   provided in the params dictionary, or if the params are empty calls ``default_contract()``.
Otherwise, the dataclass implements one field a parameter or option for the tool.


In the builder file implement a class named ``<YourToolName>Generator`` that inherits from 
``PolicyGeneratorTemplate`` located in ``MonitoringFace.Infrastructure.Builders.PolicyGenerator.PolicyGeneratorTemplatepy``.
Implement the required methods:
1. ``init(self, name, path_to_build)``: are used to link the class to the underlying Dockerfile.
2. ``generate_policy(self, policy_contract, time_on=None, time_out=None)``: returns the name of the tool as a string.
The parameter ``policy_contract`` is a raw dict and need to be parsed to create the command. The time_on and time_out are provided
by the framework and need to be passed to the call to the image, to control execution time.
The main logic of this method is to create the command to call the Docker image with the parameters and options, process
the output and return the seed, signature and policy the tool produced. 

Implement the Tag in YamlParser located in ``MonitoringFace.Infrastructure.Parsers.YamlParser``.
add a new field in the ``PolicyGeneratorsTags`` dataclass with the name of your tool in upper-case.

Also implement your variant in init_policy_generator located in ``MonitoringFace.Infrastructur.BenchmarkBuilder.BenchmarkBuilder.init_policy_generator``.

