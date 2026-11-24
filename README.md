<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# DAKboard Presence Powersaver

Automatically turn your display off when nobody is home.

During the configured display schedule, turn it on when a configured device returns.
Run the scripts on an always-on controller. Use SSH to control the separate display host.

- Add multiple people and multiple devices per person.
- Keep the monitor on when any configured device replies.
- Request monitor off after all devices give no reply for 120 seconds.
- Read the on/off times from DAKboard every 15 minutes.
- Keep scripts on the controller when DAKboard receives a new system image.

The powersaver runs each minute. The absence threshold is not an exact shutoff time.

## Get the code

```bash
git clone https://github.com/DeRezzedNightmare/dakboard-presence-powersaver.git
cd dakboard-presence-powersaver
```

## Requirements

Use Bash and Python 3.9 or later on the controller. The controller also needs SSH, ping, flock, timeout, and awk.

DAKboard needs Python 3 and working `DISPLAY=:0 xset q` access. A Wayland-only system can require another control method.

## Install

All example addresses use the documentation-only network 192.0.2.0/24.
Replace them with actual LAN addresses before operation.

1. Set up SSH key access from the controller to DAKboard.
2. Compare the display host fingerprint before you accept its key.
3. Set the destination and client key path in both SSH scripts.
4. Set the DAKboard schedule identifier in `dakboard-schedule-sync.py`.
5. Create and edit the device configuration:

```bash
install -d -m 700 "$HOME/.config/dakboard-powersaver"
cp -n occupants.example.json "$HOME/.config/dakboard-powersaver/occupants.json"
nano "$HOME/.config/dakboard-powersaver/occupants.json"
```

Replace all example addresses before installation.

```bash
python3 dakboard-presence.py --check-config
bash install.sh
python3 "$HOME/bin/dakboard-schedule-sync.py"
"$HOME/bin/dakboard-powersaver.sh" --check
```

The installer makes backups. It preserves the device configuration and existing cron entries.

Use `crontab -e` to add the two entries in `cron-reference.txt`. Replace `YOUR_USER` with the actual user. Do not add duplicate jobs.

## Add people and devices

Edit `~/.config/dakboard-powersaver/occupants.json`:

```json
{
  "Person 1": {
    "Phone": "192.0.2.101"
  },
  "Person 2": {
    "Phone": "192.0.2.102",
    "Watch": "192.0.2.103"
  }
}
```

Any reply counts as presence. Duplicate addresses receive one check. Keep at least one configured device.

Use devices that leave home with their owners. Permanent home equipment can keep the monitor on throughout the schedule window.

## Change the hours

Change the on/off times in DAKboard. Do not edit fixed times in the powersaver.

The helper reads the times every 15 minutes. Run it manually for an immediate update:

```bash
python3 "$HOME/bin/dakboard-schedule-sync.py"
```

The helper applies on/off times only. It does not apply weekdays, holidays, or schedule enable controls.

## Restore access after a reimage

1. Pause only the two DAKboard cron entries.
2. Confirm the display account, address, and SSH service.
3. Read the new host fingerprint directly on DAKboard.
4. If the host key changed, back up the controller's `known_hosts` file.
5. Remove only the obsolete entry for the verified address.
6. Connect again and compare the fingerprints.
7. Install the existing client public key again with `ssh-copy-id`.
8. Confirm display access and read the new schedule.
9. Restore the two cron entries.

Usually, the controller private key does not need replacement. Do not put it in this repository.

See [the complete setup guide](docs/SETUP.md) for commands, logs, and recovery details.

## Limits

Sleeping devices and network faults can look like absence. Use stable device addresses where possible.

The helper uses at most eight parallel workers. A very large list can exceed its result budget.

Check errors give an unknown result. The powersaver then resets its absence timer without a monitor command.

A failed schedule read retains the last valid cache indefinitely. There is no automatic cache age limit.

DAKboard can also apply its native schedule. Its actions can temporarily differ from the cached times after a change.

## Guides

- [Complete setup guide](docs/SETUP.md)
- [People and devices](docs/DEVICE_CONFIGURATION.md)
- [Upgrade an existing controller](docs/UPGRADE.md)
- [Recovery after a DAKboard reimage](docs/REIMAGE_RECOVERY.md)

## Licenses

Code and configuration examples use the [MIT license](LICENSE).
Original guide prose uses [CC BY 4.0](LICENSES/CC-BY-4.0.txt).
Code examples inside guides remain under MIT.

Credit: DeRezzedNightmare.
See [license scope](LICENSING.md) for the exact file groups.
