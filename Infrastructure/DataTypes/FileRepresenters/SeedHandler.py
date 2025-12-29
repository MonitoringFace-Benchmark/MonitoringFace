import os.path


class SeedHandler:
    def __init__(self, path_to_data):
        self.seeds_folder = f"{path_to_data}/Seeds"
        os.makedirs(self.seeds_folder, exist_ok=True)

    def add_seed_generator(self, seed):
        with open(f"{self.seeds_folder}/generator.seed", "w") as f:
            f.write(str(seed))

    def add_seed_policy(self, seed):
        with open(f"{self.seeds_folder}/policy.seed", "w") as f:
            f.write(str(seed))
