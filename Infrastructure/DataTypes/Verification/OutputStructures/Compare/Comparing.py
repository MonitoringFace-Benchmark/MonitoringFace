from typing import Tuple, AnyStr

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.DatagolfVerdicts import DatagolfVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PropositionTree
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts


def comparing(oracle_structure: AbstractOutputStructure, tool_structure: AbstractOutputStructure) -> Tuple[bool, AnyStr]:
    if isinstance(oracle_structure, Verdicts):
        pass
    elif isinstance(oracle_structure, DatagolfVerdicts):
        pass
    elif isinstance(oracle_structure, PropositionTree):
        pass

    return False, ""
