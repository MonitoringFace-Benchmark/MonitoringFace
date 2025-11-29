import os.path


class SeedHandler:
    def __init__(self, path_to_data):
        self.seeds_folder = f"{path_to_data}/Seeds"
        if os.path.exists(self.seeds_folder):
            os.mkdir(self.seeds_folder)

    def add_seed_generator(self, seed):
        with open(f"{self.seeds_folder}/generator.seed", "w") as f:
            f.write(seed)

    def add_seed_policy(self, seed):
        with open(f"{self.seeds_folder}/policy.seed", "w") as f:
            f.write(seed)
