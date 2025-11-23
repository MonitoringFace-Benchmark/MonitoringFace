import os.path


class ScratchFolderHandler:
    def __init__(self, path_to_folder):
        self.path = path_to_folder
        self.folder = f"{self.path}/scratch"

        if not os.path.exists(self.folder):
            os.mkdir(self.folder)

    def remove_folder(self):
        self.clean_up_folder()
        os.rmdir(self.folder)

    def clean_up_folder(self):
        [os.remove(os.path.join(self.folder, f)) for f in os.listdir(self.folder)]
