from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.ValueType import ValueType


class Proposition(ValueType):
    def __init__(self, value: bool):
        self.value = value

    def __repr__(self):
        return f"Proposition({self.value})"

    def __eq__(self, other):
        if not isinstance(other, Proposition):
            return False
        return self.value == other.value

    def __hash__(self) -> int:
        return hash(self.value)

    def __lt__(self, other):
        if not isinstance(other, Proposition):
            return NotImplemented
        return self.value < other.value

    def __le__(self, other):
        if not isinstance(other, Proposition):
            return NotImplemented
        return self.value <= other.value

    def __gt__(self, other):
        if not isinstance(other, Proposition):
            return NotImplemented
        return self.value > other.value

    def __ge__(self, other):
        if not isinstance(other, Proposition):
            return NotImplemented
        return self.value >= other.value
