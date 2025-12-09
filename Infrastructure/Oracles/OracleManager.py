from Infrastructure.Oracles.DataGolfOracle.DataGolfOracle import DataGolfOracle
from Infrastructure.Oracles.VeriMonOracle.VeriMonOracle import VeriMonOracle


def identifier_to_oracle(monitoring_manager, identifier, monitor_name, params):
    if identifier == "VeriMonOracle":
        return VeriMonOracle(monitoring_manager.get_monitor(monitor_name), params)
    elif identifier == "DataGolfOracle":
        return DataGolfOracle()
    else:
        raise NotImplemented()


class OracleManager:
    def __init__(self, monitor_manager, oracles_to_build):
        self.oracles = {}
        for (oracle_name, identifier, monitor_name, params) in oracles_to_build:
            self.oracles[oracle_name] = identifier_to_oracle(monitor_manager, identifier, monitor_name, params)

    def get_oracle(self, name):
        return self.oracles.get(name)
