
### Common Structure to add new Policy and Data Generators
Navigate to ``YOUR_PATH_TO/MonitoringFace/Infrastructure/Builders/ProcessorBuilder/PolicyGenerators``.

In the folder create a subfolder with a unique name in camel-case ending with the type with ``<YourToolName>Generator``,
e.g., ``ComplexPolicyGenerator`` or ``ComplexDataGenerator``.

Add an ``__init__.py`` file to the folder. Add two files the contract defining all parameters and option for
the tool, the file is named ``<YourToolName>Contract.py``. The second file is the implementation of the builder
named ``<YourToolName>Generator.py``.

In the contract file define a dataclass named ``<YourToolName>Contract`` that inherits from 
``AbstractContract`` located in ``MonitoringFace.DataTypes.Contracts.AbstractContract.py``.
The inheriting class requires the implementation of two methods:
1. ``default_contract()``: populates all the fields of the contract with reasonable default values.
2. ``instantiate_contract(params: Dict[str, Any])``: populates all the fields of the contract with the values 
provided in the params dictionary, or if the params are empty calls ``default_contract()``.
Otherwise, the dataclass implements one field a parameter or option for the tool.

### PolicyGenerators
In the builder file implement a class named ``<YourToolName>Generator`` that inherits from 
``PolicyGeneratorTemplate`` located in ``MonitoringFace.Infrastructure.Builders.PolicyGenerator.PolicyGeneratorTemplate``.
Implement the required methods:
1. ``init(self, name, path_to_build)``: are used to link the class to the underlying Dockerfile.
2. ``generate_policy(self, policy_contract, time_on=None, time_out=None)``: returns the name of the tool as a string.
The parameter ``policy_contract`` is a raw dict and need to be parsed to create the command. The time_on and time_out are provided
by the framework and need to be passed to the call to the image, to control execution time.
The main logic of this method is to create the command to call the Docker image with the parameters and options, process
the output and return the seed, signature and policy the tool produced.


### DataGenerators
In the builder file implement a class named ``<YourToolName>Generator`` that inherits from 
``DataGeneratorTemplate`` located in ``MonitoringFace.Infrastructure.Builders.DataGenerator.DataGeneratorTemplate``.
Implement the required methods:
1. ``run_generator(self, contract_inner: Dict[AnyStr, Any], time_on=None, time_out=None) -> Tuple[int, AnyStr, int]``: 
Executes the data generator with the provided contract. The ``contract_inner`` parameter is a raw dictionary that needs to be parsed to create the command. 
The ``time_on`` and ``time_out`` parameters are provided by the framework and should be passed to the image call to control execution time. 
Returns a tuple containing the seed, the generated data as a string, and the return code of the dockerfile.
2. ``check_policy(self, path_inner, signature, formula) -> bool``: 
Validates that the policy (signature and formula) is compatible with the data generator. 
Returns ``True`` if the policy is valid for the generator, ``False`` otherwise.

