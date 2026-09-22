#!/usr/bin/env bash
# Run on the Pi: pulls latest, restarts robotd, tails the log.
set -e

cd "$(dirname "$0")/.."

# Pin ALSA's default device to the USB speaker by name — card numbering isn't
# stable across reboots, and "default" otherwise falls back to HDMI (see AGENTS.md).
if [ ! -f "$HOME/.asoundrc" ]; then
    cat > "$HOME/.asoundrc" <<'EOF'
pcm.!default {
    type plug
    slave.pcm "hw:CARD=Device"
}
ctl.!default {
    type hw
    card "Device"
}
EOF
fi

git pull
sudo systemctl restart robotd
journalctl -fu robotd
