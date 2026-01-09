from typing import Tuple, AnyStr

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.IntermediateList import IntermediateList
from Infrastructure.DataTypes.Verification.OutputStructures.PDTHelper import equality_between_pdts, data_golf_pdt_equality
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.DatagolfVerdicts import DatagolfVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionList import PropositionList
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PropositionTree
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.Verdicts import Verdicts
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.OooVerdicts import OooVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.Proposition import Proposition


def to_raw_intermediate_list(structure: AbstractOutputStructure) -> IntermediateList:
    if isinstance(structure, OooVerdicts):
        return IntermediateList.from_OOOVerdicts(structure)
    elif isinstance(structure, Verdicts):
        return IntermediateList.from_Verdicts(structure)
    elif isinstance(structure, PropositionList):
        return IntermediateList.from_PropositionList(structure)
    else:
        raise Exception("Cannot convert to IntermediateList")


def intermediate_list_from_structure(structure: AbstractOutputStructure, variable_order) -> PropositionTree:
    if isinstance(structure, OooVerdicts):
        return IntermediateList.from_OOOVerdicts(structure).to_proposition_tree(new_order=variable_order)
    elif isinstance(structure, Verdicts):
        return IntermediateList.from_Verdicts(structure).to_proposition_tree(new_order=variable_order)
    elif isinstance(structure, PropositionList):
        return IntermediateList.from_PropositionList(structure).to_proposition_tree(new_order=variable_order)
    else:
        raise Exception("Cannot convert to IntermediateList")


def intermediate_compare(oracle_structure: AbstractOutputStructure, tool_structure: AbstractOutputStructure):
    return not isinstance(oracle_structure, PropositionTree) and not isinstance(tool_structure, PropositionTree)


def comparing(oracle_structure: AbstractOutputStructure, tool_structure: AbstractOutputStructure) -> Tuple[bool, AnyStr]:
    if isinstance(oracle_structure, DatagolfVerdicts):
        tool_pdt = tool_structure if isinstance(tool_structure, PropositionTree) else intermediate_list_from_structure(tool_structure, oracle_structure.variable_order)
        try:
            data_golf_pdt_equality(oracle_structure, tool_pdt)
            return True, "Verified: Structures are equivalent"
        except Exception as e:
            return False, str(e)
    elif intermediate_compare(oracle_structure, tool_structure):
        oracle_intermediate_list = to_raw_intermediate_list(oracle_structure)
        tool_intermediate_list = to_raw_intermediate_list(tool_structure)

        if set(oracle_structure.variable_order.variable_order) != set(tool_structure.variable_order.variable_order):
            return False, "Verified: Variable orders differ"

        for ((l_tp, l_ts, l_vals), (r_tp, r_ts, r_vals)) in zip(oracle_intermediate_list.values, tool_intermediate_list.values):
            if l_tp != r_tp or l_ts != r_ts:
                return False, "Verified: Structures are not equivalent"

            if isinstance(l_vals, Proposition) and isinstance(r_vals, Proposition):
                if l_vals.value != r_vals.value:
                    return False, f"Verified: Structures are not equivalent unequal propositions {l_tp}"
            elif not isinstance(l_vals, Proposition) and not isinstance(r_vals, Proposition):
                l_vals = [ass.retrieve_order(oracle_structure.variable_order) for ass in l_vals]
                if set(l_vals) != set(r_vals):
                    return False, "Verified: Structures are not equivalent"
            else:
                return False, "Miss matching type"
        return True, f"Verified: Structures are equivalent"
    else:
        oracle_pdt = oracle_structure if isinstance(oracle_structure, PropositionTree) else intermediate_list_from_structure(oracle_structure, oracle_structure.variable_order)
        tool_pdt = tool_structure if isinstance(tool_structure, PropositionTree) else intermediate_list_from_structure(tool_structure, oracle_structure.variable_order)
        try:
            oracle_dict = oracle_pdt.tp_to_ts
            tool_dict = tool_pdt.tp_to_ts

            if oracle_dict == tool_dict:
                for tp in oracle_dict.keys():
                    oracle_subtree = oracle_pdt.forest[tp]
                    tool_subtree = tool_pdt.forest[tp]
                    if not equality_between_pdts(oracle_structure.variable_order.variable_order, oracle_subtree, tool_subtree):
                        return False, "Verified: Structures are not equivalent"

                return True, "Verified: Structures are equivalent"
            else:
                tool_keys = set(tool_dict.keys())
                oracle_keys = set(oracle_dict.keys())

                if tool_keys.issubset(oracle_keys):
                    missing_keys = oracle_keys - tool_keys
                    missing_mappings = {k: oracle_dict[k] for k in missing_keys}
                    return False, f"Tool missing tp->ts mappings: {missing_mappings}"
                elif oracle_keys.issubset(tool_keys):
                    extra_keys = tool_keys - oracle_keys
                    extra_mappings = {k: tool_dict[k] for k in extra_keys}
                    return False, f"Tool has extra tp->ts mappings: {extra_mappings}"
                else:
                    return False, f"tp->ts dictionaries differ: Oracle has {oracle_dict}, Tool has {tool_dict}"
        except Exception as e:
            return False, str(e)
