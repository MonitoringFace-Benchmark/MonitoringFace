import os.path


class ExperimentsHandler:
    def __init__(self, path_to_experiments, name):
        self.dir = f"{path_to_experiments}/{name}"

        if os.path.exists(self.dir):
            print("exists")
        else:
            os.mkdir(self.dir)
            print("not exists")


if __name__ == "__main__":
    ExperimentsHandler("//Infrastructure/experiments", "test1")
