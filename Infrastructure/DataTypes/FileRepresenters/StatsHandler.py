import os.path


class StatsHandler:
    def __init__(self, path_to_folder_inner):
        self.path = path_to_folder_inner

    def get_stats(self):
        file_path = f"{self.path}/scratch/stats.txt"
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                fields = dict(map(lambda x: x.strip().split(": "), f.readlines()))
                cpu_percentage = fields["Percent of CPU this job got"]
                max_memory = fields["Maximum resident set size (kbytes)"]
                wall_time = fields["Elapsed (wall clock) time (h:mm:ss or m:ss)"]
                return wall_time, max_memory, cpu_percentage
        else:
            return None


if __name__ == "__main__":
    sh = StatsHandler("//Infrastructure/experiments/test123456/operators_5/num_0")
    sh.get_stats()
