from typing import Tuple, AnyStr

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.IntermediateList import IntermediateList
from Infrastructure.DataTypes.Verification.OutputStructures.PDTHelper import equality_between_pdts, data_golf_pdt_equality
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.DatagolfVerdicts import DatagolfVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PropositionTree
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.OooVerdicts import OooVerdicts


# todo handle proposition tree reordering variable order
def intermediate_list_from_structure(structure: AbstractOutputStructure, variable_order) -> IntermediateList:
    if isinstance(structure, OooVerdicts):
        return IntermediateList.from_OOOVerdicts(structure).to_proposition_tree(new_order=variable_order)
    elif isinstance(structure, Verdicts):
        return IntermediateList.from_Verdicts(structure).to_proposition_tree(new_order=variable_order)
    elif isinstance(structure, PropositionList):
        return IntermediateList.from_PropositionList(structure).to_proposition_tree(new_order=variable_order)
    else:
        raise Exception("Cannot convert to IntermediateList")


def comparing(oracle_structure: AbstractOutputStructure, tool_structure: AbstractOutputStructure) -> Tuple[bool, AnyStr]:
    if isinstance(oracle_structure, DatagolfVerdicts):
        tool_pdt = tool_structure if isinstance(tool_structure, PropositionTree) else intermediate_list_from_structure(tool_structure, oracle_structure.variable_order)
        try:
            data_golf_pdt_equality(oracle_structure, tool_pdt)
            return True, "Verified: Structures are equivalent"
        except Exception as e:
            return False, str(e)
    else:
        oracle_pdt = oracle_structure if isinstance(oracle_structure, PropositionTree) else intermediate_list_from_structure(oracle_structure, oracle_structure.variable_order)
        tool_pdt = tool_structure if isinstance(tool_structure, PropositionTree) else intermediate_list_from_structure(tool_structure, oracle_structure.variable_order)
        try:
            equality_between_pdts(oracle_pdt, tool_pdt)
            return True, "Verified: Structures are equivalent"
        except Exception as e:
            return False, str(e)
