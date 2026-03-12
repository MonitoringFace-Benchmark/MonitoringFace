from typing import Tuple

from Infrastructure.DataTypes.Verification.OutputStructures.AbstractComparator import AbstractComparator
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.OooVerdicts import OooVerdicts


class OooVerdicsComparator(AbstractComparator):
    def __init__(self, ooov: OooVerdicts):
        self.ooov = ooov

    def as_oracle(self, other: AbstractOutputStructure) -> Tuple[bool, str]:
        pass
