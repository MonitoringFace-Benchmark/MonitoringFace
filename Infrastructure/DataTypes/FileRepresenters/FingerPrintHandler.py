from Infrastructure.DataTypes.FingerPrint.FingerPrint import data_class_to_finger_print


class FingerPrintHandler:
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

    def get_attr(self, name):
        return self.in_dict.get(name)

    def set_attr(self, k, v):
        self.in_dict[k] = data_class_to_finger_print(v)

    def to_file(self, file):
        with open(file, "w") as f:
            for k, v in self.in_dict.items():
                f.write(f"{k}={v}\n")
