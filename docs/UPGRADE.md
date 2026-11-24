<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Upgrade an existing controller

This procedure preserves the existing schedule helper behavior and cron entries.
The installer does not install or replace SSH keys.

1. Save a copy of the current scripts and crontab.
2. Extract the new package on the controller.
3. Create the configuration directory:

```bash
install -d -m 700 "$HOME/.config/dakboard-powersaver"
```

4. If no device file exists, copy the generic example:

```bash
cp -n occupants.example.json "$HOME/.config/dakboard-powersaver/occupants.json"
```

5. Edit the device file with the actual people and addresses.
6. Compare the destination and key path in both SSH scripts with the installed values.
7. Keep any required local destination or schedule-identifier changes.
8. Run the installer:

```bash
bash install.sh
```

The installer keeps the device configuration and existing cron entries.
It saves a backup of the installed scripts, device configuration, and any schedule cache.
It uses the existing locks to prevent overlap with active jobs.
If a job holds a lock, run the installer again later.

Read the schedule and inspect the proposed monitor state:

```bash
python3 "$HOME/bin/dakboard-schedule-sync.py"
python3 "$HOME/bin/dakboard-presence.py" --check-config
"$HOME/bin/dakboard-powersaver.sh" --check
```

The existing two cron entries still apply.
Do not add duplicate entries.
The presence helper does not need its own cron entry.

The archive does not contain a personal device list or a live-system backup.
See [license scope](../LICENSING.md).
