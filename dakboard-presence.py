#!/usr/bin/python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 damongatenby
"""Check a set of people and devices. Exit: 0 present, 1 absent, 2 unknown."""
import argparse
import concurrent.futures
import ipaddress
import json
from pathlib import Path
import subprocess
import sys

DEFAULT_CONFIG = Path.home() / ".config/dakboard-powersaver/occupants.json"
MAX_WORKERS = 8
CHECK_BUDGET = 20
PING_TIMEOUT = 6


def load_devices(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise ValueError("The people list must not be empty.")
    devices = {}
    for person, entries in data.items():
        valid_name(person)
        if not isinstance(entries, dict) or not entries:
            raise ValueError(f"No devices for {person}.")
        for label, address in entries.items():
            valid_name(label)
            if not isinstance(address, str):
                raise ValueError(f"Invalid address for {person}/{label}.")
            address = str(ipaddress.IPv4Address(address))
            devices.setdefault(address, []).append(f"{person}/{label}")
    return devices


def valid_name(value):
    if (not isinstance(value, str) or not value.strip() or len(value) > 80
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError("Use a nonempty name without control characters.")


def ping_device(address):
    try:
        result = subprocess.run(
            ["ping", "-n", "-c", "2", "-W", "2", address],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            timeout=PING_TIMEOUT, check=False)
        return result.returncode if result.returncode in (0, 1) else 2
    except (OSError, subprocess.TimeoutExpired):
        return 2


def check_presence(devices, probe=ping_device, budget=CHECK_BUDGET):
    if not devices:
        return 2, "ERROR: No devices configured."
    executor = concurrent.futures.ThreadPoolExecutor(
        max_workers=min(MAX_WORKERS, len(devices)))
    futures = {}
    unknown = False
    try:
        futures = {executor.submit(probe, address): address
                   for address in devices}
        try:
            for future in concurrent.futures.as_completed(futures, timeout=budget):
                address = futures[future]
                try:
                    result = future.result()
                except Exception:
                    result = 2
                if result == 0:
                    labels = ", ".join(sorted(devices[address]))
                    return 0, f"Reachable device: {labels} ({address})."
                if result != 1:
                    unknown = True
        except concurrent.futures.TimeoutError:
            unknown = True
        if unknown:
            return 2, "ERROR: One or more device checks did not complete normally."
        return 1, f"No reply from all {len(devices)} configured addresses."
    finally:
        for future in futures:
            future.cancel()
        executor.shutdown(wait=True, cancel_futures=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--check-config", action="store_true")
    args = parser.parse_args()
    try:
        devices = load_devices(args.config)
        if args.check_config:
            print(f"Valid configuration: {len(devices)} unique device addresses.")
            return 0
        status, message = check_presence(devices)
        print(message)
        return status
    except Exception as error:
        print(f"ERROR: Presence check failed: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
