from Infrastructure.DataTypes.Contracts.AbstractContract import AbstractContract


class ScriptSetupContract(AbstractContract):
    def __init__(self, name: str, script_name: str, fixed: bool):
        self.name = name
        self.fixed = fixed
        self.script_name = script_name

    def default_contract(self):
        pass

    def instantiate_contract(self, params):
        pass
