from Infrastructure.Oracles.DataGolfOracle.DataGolfOracle import DataGolfOracle
from Infrastructure.Oracles.VeriMonOracle.VeriMonOracle import VeriMonOracle
from Infrastructure.printing import print_headline, print_footline


def identifier_to_oracle(monitoring_manager, identifier, monitor_name, params):
    if identifier == "VeriMonOracle":
        return VeriMonOracle(monitoring_manager.get_monitor(monitor_name), params)
    elif identifier == "DataGolfOracle":
        return DataGolfOracle()
    else:
        raise NotImplemented()


class OracleManager:
    def __init__(self, monitor_manager, oracles_to_build):
        print_headline("(Starting) Building OracleManager")
        self.oracles = {}
        failed_builds = []
        for (oracle_name, identifier, monitor_name, params) in oracles_to_build:
            try:
                print(f"-> Attempting to construct Oracle {identifier}")
                self.oracles[oracle_name] = identifier_to_oracle(monitor_manager, identifier, monitor_name, params)
                print(f"    -> (Success)")
            except Exception:
                print(f"-> (Failure)")
                failed_builds += [f"{identifier}"]

        if failed_builds:
            print(f"\nFailed to Construct:")
            for fail in failed_builds:
                print(f" - {fail}")

        print_footline("(Finished) Building OracleManager")

    def get_oracle(self, name):
        return self.oracles.get(name)
