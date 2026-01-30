

class CLIArgs:
    def __init__(
            self, debug: bool = False, verbose: bool = False,
            measure: bool = True, clean: bool = False,
            clean_all: bool = False):
        self.debug = debug
        self.verbose = verbose
        self.measure = measure
        self.clean = clean
        self.clean_all = clean_all
