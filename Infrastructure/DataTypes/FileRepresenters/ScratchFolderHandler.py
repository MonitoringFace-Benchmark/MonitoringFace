import os.path
import shutil


class ScratchFolderHandler:
    def __init__(self, path_to_folder):
        self.path = path_to_folder
        self.folder = f"{self.path}/scratch"

        if not os.path.exists(self.folder):
            os.makedirs(self.folder, exist_ok=True)

    def remove_folder(self):
        self.clean_up_folder()
        os.rmdir(self.folder)

    def clean_up_folder(self):
        [os.remove(os.path.join(self.folder, f)) for f in os.listdir(self.folder)]

    def copy_to_debug(self, debug_base_path: str, setting_id: str, tool_name: str) -> str:
        # Sanitize setting_id for use as folder name
        safe_setting_id = setting_id.replace("/", "_").replace(" ", "_").replace(":", "_").replace(">", "")
        safe_tool_name = tool_name.replace("/", "_").replace(" ", "_")

        debug_folder = os.path.join(debug_base_path, safe_setting_id, safe_tool_name)
        os.makedirs(debug_folder, exist_ok=True)

        # Copy all files from scratch to debug folder
        for f in os.listdir(self.folder):
            src = os.path.join(self.folder, f)
            dst = os.path.join(debug_folder, f)
            if os.path.isfile(src):
                shutil.copy2(src, dst)
            elif os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)

        return debug_folder

