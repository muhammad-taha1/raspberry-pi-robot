#!/usr/bin/env bash
# Run on the Pi: pulls latest, restarts robotd, tails the log.
set -e

cd "$(dirname "$0")/.."

# Pin ALSA's default card by name, system-wide — card numbering isn't stable
# across reboots and "default" otherwise falls back to HDMI (see AGENTS.md).
# /etc/asound.conf, not ~/.asoundrc: robotd runs as a systemd service, and this
# one USB device is both the speaker and the mic, so a per-user file the
# service can't see would break capture and playback together.
if [ ! -f /etc/asound.conf ]; then
    sudo tee /etc/asound.conf >/dev/null <<'EOF'
pcm.!default { type plug; slave.pcm "hw:CARD=Device" }
ctl.!default { type hw; card "Device" }
EOF
fi

git pull
.venv/bin/pip install -q -r requirements.txt
sudo systemctl restart robotd
journalctl -fu robotd
