from typing import Tuple, AnyStr
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure


def comparing(oracle_structure: AbstractOutputStructure, tool_structure: AbstractOutputStructure) -> Tuple[bool, AnyStr]:
    return oracle_structure.as_oracle(tool_structure)
