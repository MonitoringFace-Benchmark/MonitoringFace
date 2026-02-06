from enum import Enum


class InputOutputTraceFormats(Enum):
    CSV = "csv"
    OOO_CSV = "ooo-csv"
    CSV_LINEAR = "csv-linear"
    MONPOLY_LINEAR = "monpoly-linear"
    MONPOLY = "monpoly"
    DEJAVU = "dejavu"
    DEJAVU_ENCODED = "dejavu-encoded"
    DEJAVU_LINEAR = "dejavu-linear"


def str_to_inout_format(format_str: str) -> InputOutputTraceFormats:
    format_str = format_str.lower()
    if format_str == "csv":
        return InputOutputTraceFormats.CSV
    elif format_str == "csv-linear":
        return InputOutputTraceFormats.CSV_LINEAR
    elif format_str == "monpoly-linear":
        return InputOutputTraceFormats.MONPOLY_LINEAR
    elif format_str == "monpoly":
        return InputOutputTraceFormats.MONPOLY
    elif format_str == "dejavu":
        return InputOutputTraceFormats.DEJAVU
    elif format_str == "dejavu_encoded":
        return InputOutputTraceFormats.DEJAVU_ENCODED
    elif format_str == "dejavu-linear":
        return InputOutputTraceFormats.DEJAVU_LINEAR
    else:
        raise ValueError(f"Unknown input/output format: {format_str}")


def inout_format_to_str(format_enum: InputOutputTraceFormats) -> str:
    if format_enum == InputOutputTraceFormats.CSV:
        return "csv"
    elif format_enum == InputOutputTraceFormats.CSV_LINEAR:
        return "csv-linear"
    elif format_enum == InputOutputTraceFormats.MONPOLY_LINEAR:
        return "monpoly-linear"
    elif format_enum == InputOutputTraceFormats.MONPOLY:
        return "monpoly"
    elif format_enum == InputOutputTraceFormats.DEJAVU:
        return "dejavu"
    elif format_enum == InputOutputTraceFormats.DEJAVU_ENCODED:
        return "dejavu_encoded"
    elif format_enum == InputOutputTraceFormats.DEJAVU_LINEAR:
        return "dejavu-linear"
    else:
        raise ValueError(f"Unknown input/output format enum: {format_enum}")