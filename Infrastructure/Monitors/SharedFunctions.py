import re


def parse_variable_order_monpoly(text):
    match = re.search(r"The sequence of free variables is:\s*\((.*?)\)", text)
    result = match.group(1).split(",") if match and match.group(1) else []
    return [v.strip() for v in result]


def parse_pattern(pattern_str: str):
    match = re.match(r'@(\d+)\s*\(time point (\d+)\):\s*(.*)', pattern_str)
    tuples_list = [[num for num in tup.split(',') if num] for tup in re.findall(r'\(([^)]*)\)', match.group(3))]
    return int(match.group(1)), int(match.group(2)), tuples_list


def parse_variable_order_timely(text):
    match = re.search(r"Order of free variables:\s*\((.*?)\)", text)
    result = match.group(1).split(", ") if match and match.group(1) else []
    return [v.strip() for v in result]
