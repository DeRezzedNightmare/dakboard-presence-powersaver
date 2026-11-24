#!/usr/bin/python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 DeRezzedNightmare
import datetime
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

state = Path.home() / ".local/state/dakboard-powersaver"
cache = state / "schedule.json"

def validate(data):
    start = data["start_minutes"]
    end = data["end_minutes"]
    if (type(start) is not int or type(end) is not int
            or not 0 <= start < 1440 or not 0 <= end <= 1440
            or start == end):
        raise ValueError("Invalid or ambiguous schedule")
    return start, end

def main():
    mode = sys.argv[1:]
    if mode == ["--read"]:
        data = json.loads(cache.read_text())
        print(*validate(data))
        return
    if mode:
        raise ValueError("Usage: dakboard-schedule-sync.py [--read]")

    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    with open(state / "schedule-sync.lock", "a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return

        remote_code = """
import json
import re
with open("/var/www/config.json") as f:
    schedules = json.load(f).get("schedules")
if not isinstance(schedules, dict):
    raise ValueError("Cannot read DAKboard schedules")
schedule = schedules.get("YOUR_SCHEDULE_ID")
if schedule is None and len(schedules) == 1:
    schedule = next(iter(schedules.values()))
if not isinstance(schedule, dict):
    raise ValueError("Cannot identify intended schedule")
def minutes(value, end=False):
    if not isinstance(value, str):
        raise ValueError("Missing time")
    m = re.fullmatch(r"([0-9]{1,2}):([0-9]{2})", value)
    if not m:
        raise ValueError("Invalid time")
    h, minute = map(int, m.groups())
    if end and h == 24 and minute == 0:
        return 1440
    if not (0 <= h < 24 and 0 <= minute < 60):
        raise ValueError("Time out of range")
    return h * 60 + minute
print(json.dumps({
    "start_minutes": minutes(schedule.get("on_time")),
    "end_minutes": minutes(schedule.get("off_time"), True)
}))
"""
        import shlex
        env = os.environ.copy()
        env.pop("SSH_AUTH_SOCK", None)
        result = subprocess.run(
            ["ssh", "-T", "-i",
             str(Path.home() / ".ssh/dakboard_ed25519"),
             "-o", "IdentitiesOnly=yes", "-o", "BatchMode=yes",
             "-o", "StrictHostKeyChecking=yes",
             "-o", "ConnectTimeout=5",
             "-o", "ServerAliveInterval=5",
             "-o", "ServerAliveCountMax=2",
             "dakboard@192.0.2.10",
             "python3 -c " + shlex.quote(remote_code)],
            capture_output=True, text=True, timeout=25,
            check=True, env=env)
        data = json.loads(result.stdout)
        start, end = validate(data)
        data["updated_at"] = datetime.datetime.now().astimezone().isoformat()

        fd, name = tempfile.mkstemp(prefix=".schedule-", dir=state)
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f)
                f.write("\n")
            os.replace(name, cache)
        finally:
            if os.path.exists(name):
                os.unlink(name)

        print(f"Saved DAKboard schedule: "
              f"{start // 60:02d}:{start % 60:02d}-"
              f"{end // 60:02d}:{end % 60:02d}")

try:
    main()
except Exception as error:
    print(f"Schedule sync/read failed: {error}. "
          "Existing cache left unchanged.", file=sys.stderr)
    sys.exit(1)
