import time
from abc import ABC, abstractmethod
from typing import Dict, AnyStr, Any

from Infrastructure.Builders.ToolBuilder import ToolImageManager
from Infrastructure.Monitors.MonitorExceptions import ToolException, ResultErrorException, TimedOut


class AbstractMonitorTemplate(ABC):
    def __init__(self, image: ToolImageManager, name, params: Dict[AnyStr, Any]):
        self.image = image
        self.params = params
        self.name = name

    """
        transform csv into the tool format, e.g. sorted
        @param path_to_data:      path to the initial data in the standard csv format 
        @param path_to_signature: path to the signature 
        @param path_to_formula:   path to the formula 
    """
    @abstractmethod
    def pre_processing(self, path_to_folder: AnyStr, data_file: AnyStr, signature_file: AnyStr, formula_file: AnyStr):
        # each tool will be initialized with a working directory in which the user can create files for
        # processing or passing around
        pass

    """
        run the monitor
    """
    @abstractmethod
    def run_offline(self, time_on=None, time_out=None) -> (AnyStr, int):
        # run tool and store results either as the value or file
        pass

    """
        preprocess the output format for double checking
    """
    @abstractmethod
    def post_processing(self, stdout_input: AnyStr) -> list[AnyStr]:
        # process the string or file
        pass


def run_monitor(mon: AbstractMonitorTemplate, guarded,
                path_to_folder: AnyStr, data_file: AnyStr,
                signature_file: AnyStr, formula_file: AnyStr, oracle=None):
    print("\n" + "="*75)
    print(mon.name)
    start = time.perf_counter()
    mon.pre_processing(path_to_folder, data_file, signature_file, formula_file)
    end = time.perf_counter()
    preprocessing_elapsed = end - start

    start = time.perf_counter()
    out, code = mon.run_offline(time_on=None, time_out=guarded.upper_bound)
    end = time.perf_counter()
    run_offline_elapsed = end - start

    if code != 0:
        if code == 124:
            raise TimedOut
        else:
            print(out)
            raise ToolException

    start = time.perf_counter()
    res = mon.post_processing(out)
    end = time.perf_counter()
    postprocessing_elapsed = end - start

    if oracle is not None and False:
        verified, msg = verify(res, oracle)
        if not verified:
            raise ResultErrorException(msg)

    print(postprocessing_elapsed, run_offline_elapsed, postprocessing_elapsed)
    print("="*75 + "\n")
    return preprocessing_elapsed, run_offline_elapsed, postprocessing_elapsed


# match tool to oracle
def check(tool_res: list[AnyStr], oracle_res: list[AnyStr]):
    oracle_len = len(oracle_res)
    tool_len = len(tool_res)

    emptiness = True if oracle_len == 0 and tool_len == 0 else False
    same_length = tool_len == oracle_len

    # check if tool_res is a subset of oracle_res
    pass


def verify(tool_res: list[AnyStr], oracle_res: list[AnyStr]) -> (bool, AnyStr):
    # todo verify and check
    pass
