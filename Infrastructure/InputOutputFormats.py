from enum import Enum


class InputOutputFormats(Enum):
    CSV = "csv"
    OOO_CSV = "ooo-csv"
    CSV_LINEAR = "csv-linear"
    MONPOLY_LINEAR = "monpoly-linear"
    MONPOLY = "monpoly"
    DEJAVU = "dejavu"
    DEJAVU_ENCODED = "dejavu_encoded"
    DEJAVU_LINEAR = "dejavu-linear"


def str_to_inout_format(format_str: str) -> InputOutputFormats:
    format_str = format_str.lower()
    if format_str == "csv":
        return InputOutputFormats.CSV
    elif format_str == "csv-linear":
        return InputOutputFormats.CSV_LINEAR
    elif format_str == "monpoly-linear":
        return InputOutputFormats.MONPOLY_LINEAR
    elif format_str == "monpoly":
        return InputOutputFormats.MONPOLY
    elif format_str == "dejavu":
        return InputOutputFormats.DEJAVU
    elif format_str == "dejavu_encoded":
        return InputOutputFormats.DEJAVU_ENCODED
    elif format_str == "dejavu-linear":
        return InputOutputFormats.DEJAVU_LINEAR
    else:
        raise ValueError(f"Unknown input/output format: {format_str}")


def inout_format_to_str(format_enum: InputOutputFormats) -> str:
    if format_enum == InputOutputFormats.CSV:
        return "csv"
    elif format_enum == InputOutputFormats.CSV_LINEAR:
        return "csv-linear"
    elif format_enum == InputOutputFormats.MONPOLY_LINEAR:
        return "monpoly-linear"
    elif format_enum == InputOutputFormats.MONPOLY:
        return "monpoly"
    elif format_enum == InputOutputFormats.DEJAVU:
        return "dejavu"
    elif format_enum == InputOutputFormats.DEJAVU_ENCODED:
        return "dejavu_encoded"
    elif format_enum == InputOutputFormats.DEJAVU_LINEAR:
        return "dejavu-linear"
    else:
        raise ValueError(f"Unknown input/output format enum: {format_enum}")