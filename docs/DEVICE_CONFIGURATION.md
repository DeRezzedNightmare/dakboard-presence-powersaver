<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# People and devices

The controller reads `~/.config/dakboard-powersaver/occupants.json`.

Use one named group for each person. Add a named entry for each device.

```json
{
  "Person 1": {
    "Phone": "192.0.2.101",
    "Watch": "192.0.2.102"
  },
  "Person 2": {
    "Phone": "192.0.2.103"
  }
}
```

Replace the example names and addresses before operation.
Use devices that leave home with their owners.
An always-on home computer can keep the monitor on throughout the schedule window.

Any reply counts as presence.
All unique addresses must give no reply before the absence timer can continue.
A successful reply has priority over an error from another device.
Without a successful reply, any check error gives an unknown result.

An unknown result resets the absence timer without a monitor command.
The `--check` mode leaves the timer unchanged.
The schedule can still require monitor off outside the allowed window.

The helper uses at most eight parallel workers.
Its result budget is 20 seconds.
Active ping processes can add up to six seconds after that budget.
A very large list can therefore give an unknown result.

Use IPv4 addresses. Keep at least one person and one device.
The helper checks duplicate addresses only once.
Use commas between JSON entries. Do not add a comma after the final entry.

Check the configuration:

```bash
python3 "$HOME/bin/dakboard-presence.py" --check-config
```

Do not commit the personal device file.
Commit only the generic example.
See [license scope](../LICENSING.md).
