from typing import AnyStr

from Infrastructure.constants import LENGTH


def print_headline(text):
    print(f"\n{orient_header_text(text, LENGTH)}")
    
    
def print_footline(init=None):
    if init is None:
        print(("=" * LENGTH) + "\n")
    else:
        print(f"{orient_header_text(init, LENGTH)}\n")
    

def orient_header_text(text: AnyStr, row_length) -> AnyStr:
    text_with_spaces = f" {text} "
    padding_needed = row_length - len(text_with_spaces)
    left_equals = padding_needed // 2
    right_equals = padding_needed - left_equals

    return '=' * left_equals + text_with_spaces + '=' * right_equals


if __name__ == "__main__":
    print(orient_header_text("test", 21))