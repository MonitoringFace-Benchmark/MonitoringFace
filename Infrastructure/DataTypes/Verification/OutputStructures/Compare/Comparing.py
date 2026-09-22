from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Strength import Comparison


def comparing(oracle_structure: AbstractOutputStructure, tool_structure: AbstractOutputStructure) -> Comparison:
    return oracle_structure.as_oracle(tool_structure)
