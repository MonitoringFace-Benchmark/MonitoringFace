#!/usr/bin/env python3
import json
import sys
import urllib.error
import urllib.request
from typing import Iterable, Iterator, Optional


STREAM_URL = "https://stream.wikimedia.org/v2/stream/recentchange"
USER_AGENT = "Mozilla/5.0 (compatible; ExperimentDriver/1.0)"


def extract_event(line: str) -> Optional[dict]:
    line = line.strip()
    if not line:
        return None
    try:
        data = json.loads(line)
    except json.JSONDecodeError:
        return None
    return {
        "ts": data.get("ts", data.get("timestamp")),
        "user": data.get("user"),
        "bot": data.get("bot"),
        "type": data.get("type"),
    }


def format_record(event: dict) -> str:
    e = event.get("type")
    ts = event.get("ts")
    u = event.get("user")
    b = event.get("bot")
    return f"{e}, tp={ts}, ts={ts}, user=\"{u}\", bot={b}"


def iter_live_stream_lines() -> Iterator[str]:
    request = urllib.request.Request(STREAM_URL, headers={"User-Agent": USER_AGENT, "Accept": "text/event-stream"})
    try:
        with urllib.request.urlopen(request) as response:
            for raw in response:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line.startswith("data: "):
                    continue
                payload = line.removeprefix("data: ")
                event = extract_event(payload)
                if event is None:
                    continue
                yield json.dumps(event, separators=(",", ":"))
    except urllib.error.HTTPError as exc:
        print(f"Fatal: live stream request failed: {exc}", file=sys.stderr)
        return
    except urllib.error.URLError as exc:
        print(f"Fatal: live stream request failed: {exc}", file=sys.stderr)
        return


def process_lines(lines: Iterable[str]) -> int:
    for raw in lines:
        event = extract_event(raw)
        if event is None:
            continue

        ts = event.get("ts")
        if ts is None: continue
        res = format_record(event)
        print(res)
    return 0


def main() -> int:
    return process_lines(iter_live_stream_lines())


if __name__ == "__main__":
    raise SystemExit(main())

