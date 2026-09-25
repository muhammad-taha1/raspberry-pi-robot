#!/usr/bin/env bash
# Run on the Pi: pulls latest, refreshes deps/models/unit, restarts robotd, tails the log.
set -e

# Braces make bash parse the whole script before running it, so the git pull
# below can't swap this file out from under the running shell.
{
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

# robotd.service runs with HF_HUB_OFFLINE=1, so fetch weights here while online.
# Both are no-ops once cached; the STT one follows [stt] model in robot.toml.
.venv/bin/needle download needle3
.venv/bin/python -c "from faster_whisper import WhisperModel; from robotd.config import load; WhisperModel(load().stt_model, compute_type='int8')"

# The voice and chat models are installed by hand, never committed. Missing
# chat weights only degrade to NullChat, so flag them here rather than in the log.
.venv/bin/python -c "
from robotd.config import load
c = load()
for p in (c.voice_model_path, c.chat_model_path):
    if not p.exists():
        print(f'WARNING: model file missing: {p}')
"

if ! cmp -s deploy/robotd.service /etc/systemd/system/robotd.service; then
    sudo cp deploy/robotd.service /etc/systemd/system/robotd.service
    sudo systemctl daemon-reload
fi

sudo systemctl restart robotd
journalctl -fu robotd
exit
}
