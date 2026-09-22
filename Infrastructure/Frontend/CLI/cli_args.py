from typing import Optional

from Infrastructure.DataTypes.Verification.OutputStructures.Strength import Strength


class CLIArgs:
    def __init__(
            self, debug: bool = False, verbose: bool = False,
            measure: bool = True, clean: bool = False,
            clean_all: bool = False, short_cut: bool = False,
            analyze: bool = False, provenance: bool = True,
            min_verification_strength: Optional[Strength] = None):
        self.debug = debug
        self.verbose = verbose
        self.measure = measure
        self.clean = clean
        self.clean_all = clean_all
        self.short_cut = short_cut
        self.analyze = analyze
        self.provenance = provenance
        self.min_verification_strength = min_verification_strength
