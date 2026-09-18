"""Live-lane executor for one stream processor stage, spawned by the online
driver as `--processor "PYTHONPATH=<root> python3 -u .../LiveRunner.py --spec
pipeline.json --index k"`. Reads lines from stdin, writes released lines to
stdout, and reports the control counters the driver's quiescence rule runs on
(`#mfctl consumed= released= dropped= [origins=]`) plus a final `#mfstats`
line on stderr. Self-contained: stdlib plus StreamProcessorTemplate only, so
the baked container tree needs nothing else."""

import argparse
import importlib
import json
import sys


def load(identifier):
    module = importlib.import_module(
        f"Archive.Implementations.Builders.ProcessorBuilder.StreamProcessors.{identifier}.{identifier}")
    return getattr(module, identifier)


def emit(outs, tee):
    for line in outs:
        sys.stdout.write(line + "\n")
        if tee is not None:
            tee.write(line + "\n")
    sys.stdout.flush()
    if tee is not None:
        tee.flush()


def ctl(consumed, released, processor, outs):
    dropped = getattr(processor, "dropped", 0) or 0
    message = f"#mfctl consumed={consumed} released={released} dropped={dropped}"
    if outs:
        origins = processor.released_origins()
        if origins:
            message += " origins=" + ",".join(str(i) for i in origins)
    print(message, file=sys.stderr, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--tee")
    args = parser.parse_args()

    with open(args.spec) as f:
        spec = json.load(f)
    entry = spec[args.index]
    processor = load(entry["identifier"])(entry["identifier"])
    processor.setup(entry.get("params") or {})

    tee = open(args.tee, "w") if args.tee else None
    consumed = 0
    released = 0
    for raw in sys.stdin:
        outs = processor.feed(raw.rstrip("\n"))
        consumed += 1
        released += len(outs)
        emit(outs, tee)
        ctl(consumed, released, processor, outs)

    outs = processor.flush()
    released += len(outs)
    emit(outs, tee)
    ctl(consumed, released, processor, outs)
    print("#mfstats " + json.dumps(processor.stats()), file=sys.stderr, flush=True)
    if tee is not None:
        tee.close()


if __name__ == "__main__":
    main()
