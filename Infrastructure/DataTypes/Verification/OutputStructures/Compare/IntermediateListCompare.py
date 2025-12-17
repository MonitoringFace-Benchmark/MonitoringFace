from Infrastructure.DataTypes.Verification.OutputStructures.IntermediateList import IntermediateList, ValueType
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.Assignment import Assignment


class IntermediateListCompareError(Exception):
    pass


class DifferentLength(Exception):
    pass


def compare_intermediate_lists(tool_list: IntermediateList, oracle_list: IntermediateList):
    t_val = tool_list.value_type
    o_val = oracle_list.value_type

    if t_val == ValueType.ASSIGNMENTS and o_val == ValueType.ASSIGNMENTS:
        return assignment_list_equality(tool_list=tool_list, oracle_list=oracle_list)
    elif t_val == ValueType.PROP and o_val == ValueType.ASSIGNMENTS:
        return prop_list_assignment_equality(tool_list=tool_list, oracle_list=oracle_list)
    elif t_val == ValueType.PROP and o_val == ValueType.PROP:
        return prop_list_equality(tool_list=tool_list, oracle_list=oracle_list)
    else:
        return assignment_prop_list_equality(tool_list=tool_list, oracle_list=oracle_list)


def prop_list_assignment_equality(tool_list: IntermediateList, oracle_list: IntermediateList):
    length_equality(tool_list, oracle_list)

    for ((t_tp, t_values), (o_tp, o_values)) in zip(tool_list.values, oracle_list.values):
        if t_values.value:
            if o_values is None:
                raise IntermediateListCompareError(f"@{o_tp} Tool {t_values.value} !=  Oracle False")
        elif not t_values.value:
            if o_values:
                raise IntermediateListCompareError(f"@{o_tp} Tool {t_values.value} !=  Oracle True")

    return True


def assignment_prop_list_equality(tool_list: IntermediateList, oracle_list: IntermediateList):
    length_equality(tool_list, oracle_list)

    for ((t_tp, t_values), (o_tp, o_values)) in zip(tool_list.values, oracle_list.values):
        if o_values.value:
            if t_values is None:
                raise IntermediateListCompareError(f"@{o_tp} Tool False !=  Oracle {o_values.value}")
        elif not o_values.value:
            if t_values:
                raise IntermediateListCompareError(f"@{o_tp} Tool True !=  Oracle {o_values.value}")

    return True


def prop_list_equality(tool_list: IntermediateList, oracle_list: IntermediateList) -> bool:
    length_equality(tool_list, oracle_list)

    for ((t_tp, t_values), (o_tp, o_values)) in zip(tool_list.values, oracle_list.values):
        if t_values.value != o_values.value:
            raise IntermediateListCompareError(f"@{o_tp} Tool {t_values.value} !=  Oracle {o_values.value}")

    return True


def assignment_list_equality(tool_list: IntermediateList, oracle_list: IntermediateList) -> bool:
    def _reorder(vals: list[Assignment], new_variable_order):
        return list(map(lambda v: v.retrieve_order(new_variable_order), vals))

    length_equality(tool_list, oracle_list)

    for ((_, t_values), (_, o_values)) in zip(tool_list.values, oracle_list.values):
        t_values_reorder = _reorder(t_values, oracle_list.variable_ordering)
        x = set(t_values_reorder).difference(set(o_values))
        y = set(o_values).difference(set(t_values_reorder))

        if x != y:
            msg = []
            if x:
                msg.append(f"Elements in oracle but not in tool: {x - y}")
            if y:
                msg.append(f"Elements in tool but not in oracle: {y - x}")
            raise IntermediateListCompareError("\n".join(msg))

    return True


def length_equality(tool_list: IntermediateList, oracle_list: IntermediateList):
    t_len = len(tool_list.values)
    o_len = len(oracle_list.values)
    if t_len != o_len:
        t_tps = map(lambda t: t[0], tool_list.values)
        o_tps = map(lambda t: t[0], oracle_list.values)
        if t_len < o_len:
            missing = set(o_tps).difference(set(t_tps))
            raise DifferentLength(f"Tool is missing time-points: {missing}")
        else:
            too_much = set(t_tps).difference(set(o_tps))
            raise DifferentLength(f"Tools has additional time-points: {too_much}")
