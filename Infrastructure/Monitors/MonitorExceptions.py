

class ReplayerException(Exception):
    pass


class GeneratorException(Exception):
    pass


class TimedOut(Exception):
    pass


class InstructionMissing(Exception):
    pass


class ToolException(Exception):
    pass


class BuildException(Exception):
    pass


class ResultErrorException(Exception):
    def __init__(self, msg):
        self.msg = msg

    def error(self):
        print(self.msg)
