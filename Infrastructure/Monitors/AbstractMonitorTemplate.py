import time
from abc import ABC, abstractmethod
from typing import Dict, AnyStr, Any, Tuple

from Infrastructure.Builders.ToolBuilder.ToolImageManager import ToolImageManager
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrdering
from Infrastructure.Monitors.MonitorExceptions import ToolException, ResultErrorException, TimedOut
from Infrastructure.printing import print_headline, print_footline


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
    def run_offline(self, time_on=None, time_out=None) -> Tuple[AnyStr, int]:
        # run tool and store results either as the value or file
        pass

    """
        retrieve the variable order for a given specification
    """
    @abstractmethod
    def variable_order(self) -> VariableOrdering:
        pass

    """
        preprocess the output format for double checking
    """
    @abstractmethod
    def post_processing(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        # process the string or file
        pass


def run_monitor(mon: AbstractMonitorTemplate, guarded,
                path_to_folder: AnyStr, data_file: AnyStr,
                signature_file: AnyStr, formula_file: AnyStr, oracle=None):
    print_headline(f"Run {mon.name}")
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
            raise TimedOut(f"Timed out: {mon.name}")
        else:
            raise ToolException(out)

    start = time.perf_counter()
    res = mon.post_processing(out)
    end = time.perf_counter()
    postprocessing_elapsed = end - start

    if oracle is not None and False:
        verified, msg = oracle.verify(path_to_folder + "/results", data_file, res)
        if not verified:
            raise ResultErrorException((postprocessing_elapsed, run_offline_elapsed, postprocessing_elapsed), msg)

    print_footline()
    return preprocessing_elapsed, run_offline_elapsed, postprocessing_elapsed
