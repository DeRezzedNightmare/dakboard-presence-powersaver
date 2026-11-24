#!/bin/bash
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 damongatenby
set -u
export PATH=/usr/bin:/bin
export LC_ALL=C

# Version 2: people and devices are in occupants.json.
offtimeout=120
state_dir="$HOME/.local/state/dakboard-powersaver"
traxfile="$state_dir/absent-since"
check=0

case "${1:-}" in
    --check) check=1 ;;
    "") ;;
    *) echo "Usage: $0 [--check]" >&2; exit 2 ;;
esac

log() { printf '%s %s\n' "$(date -Is)" "$*"; }
fail() { log "ERROR: $*" >&2; exit 1; }

for command in ssh timeout ping flock date python3 awk; do
    command -v "$command" >/dev/null || fail "Missing command: $command"
done

mkdir -p "$state_dir" || exit 1
chmod 700 "$state_dir" || exit 1
exec 9>"$state_dir/lock"
flock -n 9 || exit 0

remote() {
    env -u SSH_AUTH_SOCK timeout 20s ssh -T \
        -i "$HOME/.ssh/dakboard_ed25519" \
        -o IdentitiesOnly=yes \
        -o BatchMode=yes \
        -o StrictHostKeyChecking=yes \
        -o ConnectTimeout=5 \
        -o ServerAliveInterval=5 \
        -o ServerAliveCountMax=2 \
        dakboard@192.0.2.10 "$1"
}

query=$(remote 'DISPLAY=:0 LC_ALL=C xset q') ||
    fail "Cannot query display; no control command sent."

monitor=$(printf '%s\n' "$query" |
    awk '/Monitor is/ {print $3; exit}')

case "$monitor" in
    On|Off|Standby|Suspend) ;;
    *) fail "Unknown display state; no control command sent." ;;
esac

# Explicit decimal conversion handles hours such as 08 and 09.

schedule=$(python3 "$HOME/bin/dakboard-schedule-sync.py" --read) ||
    fail "Cannot read cached schedule; leaving display unchanged."
read -r start_minutes end_minutes <<< "$schedule"
printf -v start_label "%02d:%02d" "$((start_minutes / 60))" "$((start_minutes % 60))"
printf -v end_label "%02d:%02d" "$((end_minutes / 60))" "$((end_minutes % 60))"
log "Cached DAKboard schedule=$start_label-$end_label."

hour=$(date +%H)
minute=$(date +%M)
now_minutes=$((10#$hour * 60 + 10#$minute))
desired="Off"
reason="outside cached DAKboard schedule $start_label-$end_label"

within=0
if ((start_minutes < end_minutes)); then
    if ((now_minutes >= start_minutes && now_minutes < end_minutes)); then
        within=1
    fi
else
    # Handle a schedule that crosses midnight.
    if ((now_minutes >= start_minutes || now_minutes < end_minutes)); then
        within=1
    fi
fi

if ((within)); then
    presence=$(python3 "$HOME/bin/dakboard-presence.py")
    result=$?

    case "$result" in
        0)
            desired="On"
            reason="$presence"
            if (( ! check )); then
                rm -f -- "$traxfile" || fail "Cannot reset absence timer."
            fi
            ;;
        1)
            now=$(date +%s)
            if [[ -f "$traxfile" ]]; then
                read -r since < "$traxfile" ||
                    fail "Cannot read absence timer."
                [[ "$since" =~ ^[0-9]{1,11}$ ]] ||
                    fail "Invalid absence timer."
                since=$((10#$since))
            else
                since=$now
                if (( ! check )); then
                    printf '%s\n' "$since" > "$traxfile" ||
                        fail "Cannot start absence timer."
                fi
            fi

            if ((since > now)); then
                since=$now
                if (( ! check )); then
                    printf '%s\n' "$since" > "$traxfile" ||
                        fail "Cannot reset absence timer."
                fi
            fi

            elapsed=$((now - since))
            if ((elapsed < offtimeout)); then
                log "Monitor=$monitor; all devices unreachable; absence ${elapsed}/${offtimeout}s; leaving display unchanged."
                exit 0
            fi
            reason="all devices unreachable for ${elapsed}s"
            ;;
        *)
            if (( ! check )); then
                rm -f -- "$traxfile" || fail "Cannot reset absence timer."
            fi
            fail "Presence is unknown; leaving display unchanged."
            ;;
    esac
elif (( ! check )); then
    rm -f -- "$traxfile" || fail "Cannot reset absence timer."
fi

log "Monitor=$monitor; target=$desired; $reason."
if ((check)); then
    log "CHECK ONLY: no monitor or absence-timer changes."
    exit 0
fi

[[ "$monitor" == "$desired" ]] && exit 0

case "$desired" in
    On) remote 'DISPLAY=:0 xset dpms force on' ;;
    Off) remote 'DISPLAY=:0 xset dpms force off' ;;
esac
[[ $? -eq 0 ]] || fail "Display command failed."

verified=$(remote 'DISPLAY=:0 LC_ALL=C xset q') ||
    fail "Display command sent, but verification failed."
actual=$(printf '%s\n' "$verified" |
    awk '/Monitor is/ {print $3; exit}')
[[ "$actual" == "$desired" ]] ||
    fail "Requested $desired but display reports ${actual:-unknown}."
log "Verified monitor $actual."
