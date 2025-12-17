from Infrastructure.DataTypes.Verification.OutputStructures.Structures.PropositionTree import PDTLeave, PDTComplementSet


class PDTCompareError(Exception):
    pass


def equality_between_pdts(left, right) -> bool:
    def _inner(left_pdt, right_pdt) -> bool:
        if isinstance(left_pdt, PDTLeave) and isinstance(right_pdt, PDTLeave):
            return left_pdt.value == right_pdt.value
        elif isinstance(left_pdt, PDTLeave) or isinstance(right_pdt, PDTLeave):
            raise PDTCompareError(f"left is leave {isinstance(left_pdt, PDTLeave)}; right is leave {isinstance(right_pdt, PDTLeave)}")

        for (guard, sub_tree) in left_pdt.values:
            if isinstance(guard, PDTComplementSet):
                pass
            else:
                for value in guard:
                    pass
            pass

    return _inner(left, right)
