#!/usr/bin/env python3
import random
import time


def main() -> None:
    ts = 0
    while True:
        pred = random.choice(["A", "B", "C"])
        x0 = random.randint(0, 100)
        x1 = random.randint(0, 100)
        print(f"@{ts} {pred}({x0},{x1});")
        time.sleep(0.00001)
        ts += 1


if __name__ == "__main__":
    main()
