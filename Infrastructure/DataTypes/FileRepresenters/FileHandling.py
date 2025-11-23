

def to_file(path, content, name, ending):
    file_name = path + "/" + f"{name}.{ending}"
    with open(file_name, mode="w") as f:
        f.write(content)
