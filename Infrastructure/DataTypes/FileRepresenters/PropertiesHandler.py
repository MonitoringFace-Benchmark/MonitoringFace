

class PropertiesHandler:
    def __init__(self, in_dict):
        self.in_dict: dict = in_dict

    @classmethod
    def from_file(cls, file):
        tmp_dict = {}
        with open(file) as f:
            for line in f.readlines():
                name, val = line.strip().split("=", 1)
                tmp_dict[name.strip()] = val.strip()
        return cls(tmp_dict)

    @classmethod
    def from_dict(cls, in_dict):
        return cls(in_dict)

    def get_attr(self, name):
        return self.in_dict.get(name)

    def set_attr(self, k, v):
        self.in_dict[k] = v

    @staticmethod
    def to_file(file):
        with open(file) as f:
            for (k, v) in f:
                f.write(f"{k}={v}\n")
