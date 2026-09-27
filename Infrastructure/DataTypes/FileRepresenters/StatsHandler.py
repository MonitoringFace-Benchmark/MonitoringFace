import os.path
import time


class StatsHandler:
    def __init__(self, path_to_folder_inner):
        self.path = path_to_folder_inner

    def get_stats(self, wait: bool = True):
        """Read the GNU `time -v` stats the container copied to
        scratch/stats.txt just before exit.

        The copy lands on a bind mount whose host-side visibility can lag the
        container's exit by a moment (macOS Docker), which used to lose the
        wall-time/memory/cpu of ~4% of perfectly good runs. With `wait` we
        retry for up to ~2s; pass wait=False when measurement was disabled so
        an absent file returns immediately. A partially flushed or malformed
        file returns None instead of raising: a stats hiccup must never turn
        a successful run into a tool error.
        """
        file_path = f"{self.path}/scratch/stats.txt"
        attempts = 20 if wait else 1
        for attempt in range(attempts):
            if os.path.exists(file_path):
                try:
                    with open(file_path, "r") as f:
                        fields = dict(
                            line.strip().split(": ", 1)
                            for line in f if ": " in line
                        )
                    return (
                        fields["Elapsed (wall clock) time (h:mm:ss or m:ss)"],
                        fields["Maximum resident set size (kbytes)"],
                        fields["Percent of CPU this job got"],
                    )
                except (KeyError, ValueError, OSError):
                    pass  # partially flushed file: retry until the budget ends
            if attempt + 1 < attempts:
                time.sleep(0.1)
        return None
