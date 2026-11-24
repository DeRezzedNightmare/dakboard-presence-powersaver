# SPDX-License-Identifier: MIT
# Copyright (c) 2026 damongatenby
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest

TEMP_ROOT = (Path.cwd() / "work/test-temp").resolve()
TEMP_ROOT.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(TEMP_ROOT)

PACKAGE = Path(sys.argv.pop(1)).resolve()
SHELL = sys.argv.pop(1)
spec = importlib.util.spec_from_file_location("presence", PACKAGE / "dakboard-presence.py")
presence = importlib.util.module_from_spec(spec)
spec.loader.exec_module(presence)

class PresenceTests(unittest.TestCase):
    def config(self, value):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory, "occupants.json")
            path.write_text(json.dumps(value))
            return presence.load_devices(path)

    def test_people_devices_and_duplicate_addresses(self):
        value = self.config({"A": {"Phone": "192.0.2.2", "Watch": "192.0.2.3"},
                             "B": {"Phone": "192.0.2.2"}})
        self.assertEqual(len(value), 2)
        self.assertEqual(value["192.0.2.2"], ["A/Phone", "B/Phone"])

    def test_invalid_configs(self):
        for value in ({}, [], {"A": {}}, {"A": {"Phone": "bad"}},
                      {"A": {"Phone": "::1"}}, {"A\n": {"Phone": "192.0.2.2"}},
                      {"A": {"Phone": 1}}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.config(value)

    def test_any_person_is_home(self):
        devices = {"192.0.2.2": ["A/Phone"], "192.0.2.3": ["B/Phone"]}
        status, message = presence.check_presence(
            devices, probe=lambda ip: 0 if ip.endswith(".3") else 1)
        self.assertEqual(status, 0)
        self.assertIn("B/Phone", message)

    def test_success_overrides_another_error(self):
        devices = {"a": ["A"], "b": ["B"]}
        self.assertEqual(presence.check_presence(
            devices, probe=lambda ip: 0 if ip == "b" else 2)[0], 0)

    def test_all_absent(self):
        self.assertEqual(presence.check_presence(
            {"a": ["A"], "b": ["B"]}, probe=lambda ip: 1)[0], 1)

    def test_error_is_not_absence(self):
        self.assertEqual(presence.check_presence(
            {"a": ["A"], "b": ["B"]},
            probe=lambda ip: 2 if ip == "b" else 1)[0], 2)

    def test_budget_expiry_is_not_absence(self):
        def slow(ip):
            time.sleep(0.04)
            return 1
        self.assertEqual(presence.check_presence(
            {"a": ["A"], "b": ["B"]}, probe=slow, budget=0.001)[0], 2)

    def test_many_devices_bound_concurrency(self):
        lock = threading.Lock()
        active = 0
        maximum = 0
        def probe(ip):
            nonlocal active, maximum
            with lock:
                active += 1
                maximum = max(maximum, active)
            time.sleep(0.01)
            with lock:
                active -= 1
            return 1
        status, _ = presence.check_presence(
            {str(i): [str(i)] for i in range(80)}, probe=probe)
        self.assertEqual(status, 1)
        self.assertLessEqual(maximum, 8)
        self.assertGreater(maximum, 1)

    def test_ping_error_codes(self):
        from unittest.mock import patch
        for returncode, expected in ((0, 0), (1, 1), (2, 2), (127, 2)):
            with patch.object(presence.subprocess, "run",
                              return_value=subprocess.CompletedProcess([], returncode)):
                self.assertEqual(presence.ping_device("192.0.2.2"), expected)

HARNESS = r'''
date() {
    case "$1" in
        +%H) echo "$TEST_HOUR" ;;
        +%M) echo "$TEST_MINUTE" ;;
        +%s) echo 1000 ;;
        -Is) echo TEST ;;
        *) return 2 ;;
    esac
}
flock() { return 0; }
ping() { return 99; }
chmod() { return 0; }
env() {
    if [[ "$1" == "-u" ]]; then shift 2; fi
    "$@"
}
timeout() { shift; "$@"; }
ssh() {
    case "$*" in
        *"xset q"*) printf 'Monitor is %s\n' "$(cat "$HOME/monitor")" ;;
        *"force on"*) echo On > "$HOME/monitor" ;;
        *"force off"*) echo Off > "$HOME/monitor" ;;
        *) return 2 ;;
    esac
}
python3() {
    case "$1" in
        *dakboard-schedule-sync.py) echo "$TEST_START $TEST_END" ;;
        *dakboard-presence.py)
            echo queried > "$HOME/presence-called"
            echo "MOCK presence result"
            return "$TEST_PRESENCE"
            ;;
        *) return 2 ;;
    esac
}
'''

class PowersaverTests(unittest.TestCase):
    def run_case(self, presence_code=0, monitor="Off", since=None,
                 hour="08", minute="09", start=420, end=1260, check=False):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state = root / ".local/state/dakboard-powersaver"
            state.mkdir(parents=True)
            (root / "monitor").write_text(monitor)
            if since is not None:
                (state / "absent-since").write_bytes((str(since) + "\n").encode())
            harness = root / "harness.sh"
            harness.write_text(HARNESS)
            env = os.environ.copy()
            env.update(HOME=root.as_posix(), TEST_HOUR=hour,
                       TEST_MINUTE=minute, TEST_START=str(start),
                       TEST_END=str(end), TEST_PRESENCE=str(presence_code))
            result = subprocess.run(
                [SHELL, "-c", '. "$1"; . "$2" "$3"', "test",
                 harness.as_posix(), (PACKAGE / "dakboard-powersaver.sh").as_posix(),
                 "--check" if check else ""],
                env=env, capture_output=True, text=True, timeout=10)
            timer = state / "absent-since"
            return (result, (root / "monitor").read_text().strip(),
                    timer.read_text().strip() if timer.exists() else None,
                    (root / "presence-called").exists())

    def test_present_turns_on_and_clears_timer(self):
        result, monitor, timer, _ = self.run_case(since=800)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((monitor, timer), ("On", None))

    def test_first_absence_preserves_on(self):
        result, monitor, timer, _ = self.run_case(presence_code=1, monitor="On")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((monitor, timer), ("On", "1000"))

    def test_expired_absence_turns_off(self):
        result, monitor, _, _ = self.run_case(presence_code=1, monitor="On", since=800)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(monitor, "Off")

    def test_unknown_preserves_monitor_and_resets_timer(self):
        result, monitor, timer, _ = self.run_case(presence_code=2, monitor="On", since=800)
        self.assertEqual(result.returncode, 1)
        self.assertEqual((monitor, timer), ("On", None))

    def test_cutoff_does_not_check_devices(self):
        result, monitor, _, checked = self.run_case(monitor="On", hour="21", minute="00")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((monitor, checked), ("Off", False))

    def test_start_is_inclusive(self):
        result, monitor, _, _ = self.run_case(hour="07", minute="00")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(monitor, "On")

    def test_overnight_window(self):
        result, monitor, _, _ = self.run_case(hour="23", minute="00", start=1320, end=360)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(monitor, "On")

    def test_dry_run_does_not_change_state(self):
        result, monitor, timer, _ = self.run_case(
            presence_code=1, monitor="On", since=800, check=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((monitor, timer), ("On", "800"))

    def test_unknown_monitor_stops_before_presence(self):
        result, monitor, _, checked = self.run_case(monitor="Unknown")
        self.assertEqual(result.returncode, 1)
        self.assertEqual((monitor, checked), ("Unknown", False))

if __name__ == "__main__":
    unittest.main()
