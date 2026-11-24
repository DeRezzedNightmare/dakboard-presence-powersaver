#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 damongatenby
# Install files only. This script does not add or replace cron jobs.
set -euo pipefail
umask 077
package_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
config="$HOME/.config/dakboard-powersaver/occupants.json"
state="$HOME/.local/state/dakboard-powersaver"
mkdir -p "$HOME/bin" "$state"
chmod 700 "$state"

for command in python3 bash flock ssh ping timeout; do
    command -v "$command" >/dev/null || {
        echo "Missing command: $command" >&2
        exit 1
    }
done
if [[ ! -f "$config" ]]; then
    echo "Create and edit $config first. See README.txt." >&2
    exit 1
fi

bash -n "$package_dir/dakboard-powersaver.sh"
python3 "$package_dir/dakboard-presence.py" --config "$config" --check-config
python3 - "$package_dir" <<'PY'
import ast
from pathlib import Path
import sys
for name in ("dakboard-presence.py", "dakboard-schedule-sync.py"):
    source = Path(sys.argv[1], name).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=name)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            if any(isinstance(t, ast.Name) and t.id == "remote_code"
                   for t in node.targets):
                ast.parse(node.value.value, filename="remote_schedule_code")
PY

exec 9>"$state/lock"
flock -n 9 || { echo "Powersaver is active. Try the installer again."; exit 1; }
exec 8>"$state/schedule-sync.lock"
flock -n 8 || { echo "Schedule helper is active. Try the installer again."; exit 1; }

backup=$(mktemp -d "$state/update-backup.XXXXXXXX")
for name in dakboard-powersaver.sh dakboard-presence.py dakboard-schedule-sync.py; do
    if [[ -e "$HOME/bin/$name" ]]; then
        cp -p -- "$HOME/bin/$name" "$backup/"
    fi
done
cp -p -- "$config" "$backup/occupants.json"
if [[ -f "$state/schedule.json" ]]; then
    cp -p -- "$state/schedule.json" "$backup/schedule.json"
fi

# Put dependencies in place before the new powersaver can run.
for name in dakboard-presence.py dakboard-schedule-sync.py dakboard-powersaver.sh; do
    temporary=$(mktemp "$HOME/bin/.dakboard-update.XXXXXXXX")
    if ! cp -- "$package_dir/$name" "$temporary"; then
        rm -f -- "$temporary"
        exit 1
    fi
    chmod 700 "$temporary"
    mv -f -- "$temporary" "$HOME/bin/$name"
done
echo "Installed version 2. Device configuration and cron entries are unchanged."
echo "Backup: $backup"
echo 'Next: run the schedule helper, then powersaver --check.'
