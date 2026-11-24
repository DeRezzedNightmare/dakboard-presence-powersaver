<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Recovery after a DAKboard reimage

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

See [license scope](../LICENSING.md).
