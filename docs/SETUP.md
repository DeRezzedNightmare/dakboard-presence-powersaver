<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# DAKboard Presence Powersaver

Automatically turn your display off when nobody’s home.

## 1. Purpose

During the configured display schedule, turn the monitor off when everyone is away. Turn it on when a configured device returns.

Run display control on an always-on Linux computer. Use SSH to send monitor commands to a separate DAKboard computer.

The controller checks devices for multiple people. Any device reply counts as presence. The controller reads the on/off times from DAKboard.

## 2. Technical terms

- Controller: the Linux computer that runs the scripts.

- Display host: the DAKboard computer that receives SSH commands.

- Monitor: the screen connected to the display host.

- Schedule cache: a local file that contains the last valid on/off times.

- Host key: the SSH identity key on the display host.

- Client key: the SSH key on the controller.

- Fingerprint: a short value that identifies a public key.

- Cron: the Linux service that starts commands at specified times.

## 3. Requirements

All addresses in this guide are documentation examples. Replace them with the actual addresses for the intended network.

Use Bash and Python 3.9 or later on the controller. Install SSH, ping, flock, timeout, and awk. The installer also uses standard Linux file utilities.

The display host needs SSH, Python 3, and xset. The SSH account must have access to the graphical session. The example commands use DISPLAY=:0.

A Wayland-only system can require another display-control method. Confirm display access before you enable automatic control.

Configure the controller for the required local time zone. Cron and the powersaver use the controller time. Neither script sets a time zone.

## 4. Files

- dakboard-powersaver.sh reads the monitor state, schedule cache, and presence result. It applies monitor changes and maintains the absence timer.

- dakboard-presence.py reads the people and device list. It checks the configured IPv4 addresses.

- dakboard-schedule-sync.py reads the DAKboard schedule. Its --read mode reads the local cache without SSH.

- install.sh installs the scripts and makes backups. It preserves the device configuration and existing cron entries.

- occupants.example.json contains generic names and addresses. Replace its values before operation.

- cron-reference.txt contains example cron entries. Replace YOUR_USER with the controller user.

The scripts use these controller paths:

```
$HOME/bin/dakboard-powersaver.sh
$HOME/bin/dakboard-presence.py
$HOME/bin/dakboard-schedule-sync.py
$HOME/.config/dakboard-powersaver/occupants.json
$HOME/.local/state/dakboard-powersaver/
```

## 5. Configure people and devices

1. Create the configuration directory.

```
install -d -m 700 "$HOME/.config/dakboard-powersaver"
```

1. Copy the example without replacement of an existing configuration.

```
cp -n occupants.example.json "$HOME/.config/dakboard-powersaver/occupants.json"
```

1. Edit the file with the actual people, devices, and LAN addresses.

The following example contains two people and three devices. Do not use the example addresses without replacement.

```
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

Use one named group for each person. Add a named entry for each device. Use a comma between entries. Do not add a comma after the final entry. JSON does not accept comments.

Keep at least one person and one device. Use IPv4 addresses. The helper checks duplicate addresses only once.

Use devices that leave home with their owners. An always-on home computer can keep the monitor on throughout the schedule window.

1. Check the configuration.

```
python3 dakboard-presence.py --check-config
```

## 6. Configure SSH access

The source files use example destination dakboard@192.0.2.10. They use client key ~/.ssh/dakboard_ed25519. Set the required account, destination, and key path in both SSH scripts.

1. On the controller, check for an existing client key.

```
ls -l "$HOME/.ssh/dakboard_ed25519" "$HOME/.ssh/dakboard_ed25519.pub"
```

Do not overwrite an unknown key. If the required key exists, use it after you confirm its purpose.

1. If no key exists, create a dedicated key.

```
install -d -m 700 "$HOME/.ssh"
ssh-keygen -t ed25519 -f "$HOME/.ssh/dakboard_ed25519" -N '' -C dakboard-powersaver
```

The example creates a key without a passphrase for unattended operation. Keep its private file readable only by its owner.

1. On the display host, read the host fingerprint through a trusted connection.

```
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

1. From the controller, connect to the display host.

```
ssh -o StrictHostKeyChecking=ask \
  -o HostKeyAlgorithms=ssh-ed25519 dakboard@192.0.2.10
```

1. Compare the displayed fingerprint with the fingerprint from the display host.

1. If the fingerprints differ, stop.

1. If the fingerprints agree, accept the host key.

1. Enter the account password yourself.

1. After login, return to the controller.

```
exit
```

1. Install the client public key.

```
ssh-copy-id -i "$HOME/.ssh/dakboard_ed25519.pub" \
  -o StrictHostKeyChecking=yes dakboard@192.0.2.10
```

Enter the display account password when requested. ssh-copy-id adds the public key and keeps other accepted keys. The private key stays on the controller.

1. Check unattended display access without an SSH agent.

```
env -u SSH_AUTH_SOCK ssh -T \
  -i "$HOME/.ssh/dakboard_ed25519" \
  -o IdentitiesOnly=yes -o BatchMode=yes \
  -o StrictHostKeyChecking=yes -o ConnectTimeout=5 \
  dakboard@192.0.2.10 'DISPLAY=:0 xset q'
```

The result must include a valid monitor state. If display authorization fails, examine the graphical session and Xauthority configuration.

The key receives the normal permissions of the display account. This setup does not restrict the key to selected commands.

## 7. Configure the schedule and install

1. In DAKboard, create or select the required display schedule.

1. In dakboard-schedule-sync.py, replace YOUR_SCHEDULE_ID with that schedule identifier.

If the selected identifier is absent, the helper accepts exactly one remaining schedule. Several remaining schedules cause an error.

1. Confirm the account, destination, and key path in both SSH scripts.

1. From the extracted package directory, run the installer.

```
bash install.sh
```

The installer checks syntax and device configuration. It saves backups of existing scripts, the device list, and any schedule cache. It preserves the device configuration and cron entries.

The installer uses the existing locks. If a scheduled job holds a lock, run the installer again later.

1. Read the DAKboard schedule.

```
python3 "$HOME/bin/dakboard-schedule-sync.py"
```

1. Read the local cache.

```
python3 "$HOME/bin/dakboard-schedule-sync.py" --read
```

1. Inspect the proposed monitor state without a control action.

```
"$HOME/bin/dakboard-powersaver.sh" --check
```

The --check mode leaves the monitor and absence timer unchanged. It can create the state directory and acquire the lock.

## 8. Configure cron

1. Confirm manual operation before you add automatic control.

1. As the controller user, save the current cron entries.

```
crontab -l
```

Keep a backup of the entries before an edit. If no user crontab exists, crontab can report that condition.

1. Open the crontab editor.

```
crontab -e
```

1. Add the following entries with the actual absolute home directory.

```
* * * * * "/home/YOUR_USER/bin/dakboard-powersaver.sh" >> "/home/YOUR_USER/.local/state/dakboard-powersaver/run.log" 2>&1
*/15 * * * * /usr/bin/python3 "/home/YOUR_USER/bin/dakboard-schedule-sync.py" >> "/home/YOUR_USER/.local/state/dakboard-powersaver/schedule-sync.log" 2>&1
```

Do not add duplicate jobs. Keep all unrelated entries. No additional cron entry is necessary for the presence helper. No cron entry is necessary on the display host.

The powersaver runs each minute. The schedule helper runs at minutes 00, 15, 30, and 45. The jobs continue after you close the terminal.

1. Check cron and the controller time zone.

```
systemctl is-active cron
date
timedatectl show -p Timezone
```

## 9. Operating behavior

Inside the schedule window, any configured device reply counts as presence. The powersaver requests On and clears the absence timer.

If all configured addresses give no reply, the powersaver starts or continues the absence timer. Before 120 seconds, it leaves the monitor unchanged. After the threshold, it requests Off.

The timer starts at the first all-absent result. It does not start at the exact time of departure. Minute intervals and command duration can increase the delay.

Outside the schedule window, the powersaver requests Off and clears the absence timer. The start time is inclusive. The end time is exclusive.

The schedule can cross midnight. Equal on/off times cause an error. The software does not define equal times as a full-day window.

An error in a presence check gives an unknown result unless another device replies. An unknown result clears the absence timer without a monitor command. The --check mode leaves the timer unchanged.

The monitor query must succeed before a control action. The accepted states are On, Off, Standby, and Suspend. An SSH failure or an unknown state stops monitor control.

After a monitor command, the powersaver reads the state again. It records an error if the state does not agree with the request.

## 10. Change the hours

1. Change the on/off times only in DAKboard.

1. Wait for the next schedule-helper run.

Alternatively, run the helper manually for an immediate read.

```
python3 "$HOME/bin/dakboard-schedule-sync.py"
```

A change can take 15 minutes to reach the cache. The next powersaver run can add approximately one minute.

The helper reads only on_time and off_time. It does not apply weekday selections, holidays, or schedule enable controls. Do not use those controls to stop the controller jobs.

DAKboard can also apply its native schedule. After an edit, its actions can temporarily disagree with the cached schedule.

## 11. Validate operation

1. Keep one configured device connected and disconnect the other devices.

1. During the schedule window, confirm that the monitor remains on.

1. Repeat the check with a different person's device.

1. Disconnect all configured devices long enough for the absence threshold and subsequent scheduled check.

1. Confirm that the monitor turns off.

1. Reconnect one device and confirm that the monitor turns on.

1. Check the scheduled cutoff and the next allowed start.

1. Check phone detection while the phones sleep.

Use the following commands to inspect the results:

```
tail -n 20 "$HOME/.local/state/dakboard-powersaver/run.log"
tail -n 10 "$HOME/.local/state/dakboard-powersaver/schedule-sync.log"
cat "$HOME/.local/state/dakboard-powersaver/schedule.json"
```

## 12. Troubleshooting

### 12.1 A device does not reply

1. Keep the device awake on home Wi-Fi.

1. Use its actual address in the following commands.

```
ip route get 192.0.2.101
ip neigh show 192.0.2.101
ping -c 3 -W 3 192.0.2.101
```

A FAILED neighbor entry indicates an address discovery failure. It does not prove that the person left home. A DELAY entry alone does not indicate a fault.

Phone sleep, Wi-Fi faults, and address changes can look like absence. A reply proves device reachability, not a person's physical presence.

Use stable private MAC addresses and DHCP reservations where applicable. Confirm the device and router settings separately.

### 12.2 A schedule change does not appear

1. Run the schedule helper manually.

1. Examine its error, the selected identifier, and the cache timestamp.

A failed schedule read keeps the last valid cache indefinitely. There is no cache age limit or automatic stale-cache alert. A missing or invalid cache stops monitor control.

### 12.3 Device checks give an unknown result

The helper uses at most eight parallel workers. Each ping process has a six-second limit. The result budget is 20 seconds.

After that budget, the helper cancels queued checks and waits for active checks. Active checks can add up to six seconds. An incomplete list gives an unknown result.

A very large list can exceed the budget. Locks prevent overlapping powersaver runs. A long run can cause the next scheduled run to skip.

### 12.4 SSH or display access fails

1. Repeat the unattended display query in section 6.

Permission denied indicates an account or key problem. A host-key warning requires an identity check. An X authorization error requires a graphical-session check.

Do not disable host-key checks. Do not publish passwords, private keys, or the complete DAKboard configuration.

## 13. Recovery after a DAKboard reimage

A reimage can remove the accepted client public key. It can also replace the display host key. Usually, reuse the existing controller client key.

1. On the controller, run crontab -e.

1. Put # at the start of only the two DAKboard job lines.

1. Save the crontab and keep unrelated entries unchanged.

1. Confirm the display account, address, SSH service, and graphical session.

1. On the display host, read the new host fingerprint through a trusted connection.

```
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

1. On the controller, inspect the stored entry for the display address.

```
ssh-keygen -F 192.0.2.10
```

If the key did not change, keep its entry. If a verified reimage changed it, back up known_hosts before removal.

```
(
  umask 077
  if [ -f "$HOME/.ssh/known_hosts" ]; then
    backup=$(mktemp "$HOME/.ssh/known_hosts.before-dakboard.XXXXXXXX") || exit 1
    cp -p "$HOME/.ssh/known_hosts" "$backup" || exit 1
    echo "Backup: $backup"
  fi
)
```

1. Remove only the obsolete entry for the verified address.

```
ssh-keygen -R 192.0.2.10
```

1. Connect again and compare the fingerprints.

```
ssh -o StrictHostKeyChecking=ask \
  -o HostKeyAlgorithms=ssh-ed25519 dakboard@192.0.2.10
```

1. If the fingerprints differ, stop.

1. If they agree, accept the host key and enter the account password.

1. Return to the controller.

```
exit
```

1. Install the existing client public key again.

```
ssh-copy-id -i "$HOME/.ssh/dakboard_ed25519.pub" \
  -o StrictHostKeyChecking=yes dakboard@192.0.2.10
```

1. Repeat the unattended display query.

1. Confirm the required DAKboard schedule and its identifier.

1. Read the schedule and inspect the proposed monitor state.

```
python3 "$HOME/bin/dakboard-schedule-sync.py"
"$HOME/bin/dakboard-powersaver.sh" --check
```

1. Remove the leading # from the two DAKboard cron lines.

1. Check absence, return, and schedule behavior.

If the client key is lost, create a replacement at a new file name. Do not overwrite an unknown key.

Install the replacement public key. Change the key path in both SSH scripts. Confirm access before you remove an obsolete accepted key.

The people and device file remains on the controller during a display-host reimage. Preserve it during controller maintenance.

## 14. Maintenance and upgrades

1. Before an upgrade, save copies of the scripts, device file, schedule cache, and crontab.

1. Compare local account, address, key, and schedule-identifier settings with the new package.

1. Preserve required local settings.

1. Run the installer from the new package directory.

```
bash install.sh
```

1. Read the schedule and inspect the proposed monitor state.

```
python3 "$HOME/bin/dakboard-schedule-sync.py"
python3 "$HOME/bin/dakboard-presence.py" --check-config
"$HOME/bin/dakboard-powersaver.sh" --check
```

Keep existing cron entries unless the required commands change. Do not add duplicate jobs. Do not restore an old full crontab without a comparison.

To pause operation, comment only the two DAKboard job lines. The monitor keeps its state unless another control changes it. DAKboard can still apply its native schedule.

The software does not include automatic log rotation. Apply a local log-retention policy if required.

## 15. Source and licenses

The repository contains the scripts, installer, generic device example, cron reference, and reusable guides. It excludes personal device lists, private keys, logs, and backups.

Code and configuration examples use MIT. Original guide prose uses Creative Commons Attribution 4.0 International. Code examples inside guides remain under MIT.

Credit the original author as damongatenby. Refer to LICENSING.md, LICENSE, and LICENSES/CC-BY-4.0.txt for the full terms.
