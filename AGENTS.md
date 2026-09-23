# AGENTS.md

A Raspberry Pi 5 desk companion robot. Actors (Pykka) communicate by message, own one
device each, and are never imported by each other.

## Documentation

`docs/` is gitignored — local-only, never reaches the Pi. It holds the working memory:
`plan.md` (milestones, status, decisions), `architecture.md` (actor tree + `/chat` behaviour
matrix — regenerate it whenever a milestone rewires an actor), `open-questions.md` (deferred
decisions — check before starting a milestone), `pinout.md` (full board reference).

`articles/` and `.claude/` are also gitignored.

## Repo map

```
robotd/
  __main__.py     entrypoint; python -m robotd
  config.py       loads config/robot.toml; RobotConfig.pin(name) -> gpio number
  messages.py     the message contract — frozen dataclasses actors send each other
  tools.py        ToolRegistry + build_registry(light) — how a device becomes a tool
  phrases.py      generic ACK/FAILED/UNSURE phrase sets
  web.py          HTTP transport only — GET /, GET /state, POST /say, POST /chat
  static/         the status page GET / serves, read from disk per request
  hal/            hardware seam — one Protocol + one real implementation per device
    leds.py       Led protocol; open_led() falls back to a no-op if the pin can't be claimed
    audio.py      Speaker/Microphone protocols + PyAudioSpeaker / PyAudioMicrophone
    buttons.py    Button protocol; open_button() falls back to a no-op, same as open_led()
  actors/
    light.py      LightActor — owns the LED, handles SetLed
    voice.py      VoiceActor — streams Speak text through TTS and the speaker
    hearing.py    HearingActor — owns the mic, STT and push-to-talk button; tells Transcript
    brain.py      BrainActor — Transcript -> LlmProvider -> ToolRegistry.dispatch(), else ChatProvider; also answers GetState
    supervisor.py Supervisor — starts/stops the actor tree
  models/
    tts.py        TextToSpeech protocol + PiperTts
    stt.py        SpeechToText protocol + WhisperStt (faster-whisper, weights self-managed)
    llm.py        LlmProvider protocol + NeedleLlm (Needle 3, on-device, owns its history)
    chat.py       ChatProvider protocol + LlamaCppChat / NullChat — prose Needle can't produce
scripts/          hardware bring-up bench — plain, blocking, run over SSH
tests/            pytest — logic only, no hardware required
  doubles.py      test doubles implementing hal/ and models/ protocols — never in robotd/
config/robot.toml the authoritative pin map
deploy/robotd.service
```

## Pin map

`config/robot.toml` is the only authoritative source. Never hardcode a GPIO number — read it
via `RobotConfig.pin(name)`.

| Name | GPIO | Device |
|---|---|---|
| `led` | 24 | Status LED |
| `button` | 5 | Push-to-talk button (wired to GND, gpiozero's internal pull-up) |
| `motor_in1` | 17 | L298N |
| `motor_in2` | 27 | L298N |
| `motor_in3` | 22 | L298N |
| `motor_in4` | 23 | L298N |

I²C/SPI addresses get added here from M8 onward. Full board reference: `docs/pinout.md`, or
run `pinout` on the Pi.

## Recipe: adding a device

1. Add a `Protocol` + one real implementation in `robotd/hal/` (or `robotd/models/` for an
   inference engine). No `Fake*` class — those live in `tests/doubles.py`.
2. Add its pin(s)/address to `config/robot.toml`.
3. To let the brain use it, register it in `tools.py`'s `build_registry()` — a small function
   that `tell()`s the actor, passed to `registry.add_action()`. The function's name and
   docstring *are* the schema Needle reads; use a Google-style `Args:` block, which drives
   Needle's per-argument grounding. Pass `triggers=(...)` (case-insensitive regexes) to make
   those phrasings the tool's *only* way to fire — it then fires on a match regardless of
   confidence, and never without one (Needle has called `set_led` for "how are you?" at
   confidence 1.0). Every tool that actuates hardware should declare triggers — check
   `docs/open-questions.md`'s trigger-overlap entry first, since two tools matching the same
   utterance is undefined. Don't add a `say`-style tool; prose is the chat model's job. This
   registry entry is the only wire-in a device needs — there's no second, HTTP-facing route
   table to also update.
4. Add a bring-up script in `scripts/` that talks to the device directly, not through the HAL.

No actor should need to change just because a device was added.

## HTTP endpoints

```
curl -X POST -d '{"text":"Good evening."}'     http://<pi-host>:8080/say
curl -X POST -d '{"text":"turn on the light"}' http://<pi-host>:8080/chat
curl http://<pi-host>:8080/state
```

`GET /` serves the status page: a turn log, a say box, a chat box, and
`reasoning`/`confidence`/tool calls as debug under each chat turn. `GET /state` is the same
turn log as JSON — `BrainActor`'s own last-`STATE_TURNS` `(heard, spoken)` pairs, from `/chat`
*and* the mic both, polled by the status page every few seconds. Full flow and every `/chat`
outcome: `docs/architecture.md`.

`web.py` is transport only, with one deliberate exception: `/chat` and `/state` both `ask()`
`BrainActor` directly (a reply is the point of both). `/say` is a direct `tell()` into
`VoiceActor` — a human typing text to speak, never routed through Needle, and never shows up
in `/state`. Binds `0.0.0.0:8080` with no auth — fine on a home LAN, worth revisiting once
motors are exposed this way (M14).

## Invariants

- A device-owning actor exposes primitives (`SetLed`, later `Drive`/`Stop`), never a pattern
  or policy. Behaviour that plays primitives over time lives in the actor that needs it.
- A device is turned off and closed when its actor stops — clean stop and failure alike.
- No actor blocks its mailbox. Slow work belongs to the actor whose only job is that thing.
  Timed behaviour is a self-rearming `threading.Timer` that `tell()`s, never a `sleep()`.
- `robotd/` ships real implementations only; doubles live in `tests/doubles.py`.
- `scripts/` stays plain, blocking, and actor-free.
- `BrainActor` holds no device references and no conversation history. A device reaches it
  only via `tools.py`.
- Prose is the chat model's job, never a Needle tool.
- **A reflex acts directly; an intent goes through the brain; a proposal needs consent.** The
  brain is never in the loop for anything that must be fast (a sensor reflex, M9+) or must be
  safe (a motion interlock, M14) — those live in the actor that owns the device or the sensor,
  not routed through `BrainActor`. There is one interpretation actor (`BrainActor`); there is
  no central command/coordinator actor — arbitration is ownership (one actor per device, one
  mailbox), not a switchboard.

## Raspberry Pi setup

1. Flash Raspberry Pi OS 64-bit (Bookworm or later — needed for `rpi-lgpio`/Pi 5). Set
   hostname, SSH, user and Wi-Fi in the Imager's settings (Ctrl+Shift+X) before writing.
2. `ssh <user>@<hostname>.local`
3. ```
   sudo apt update && sudo apt full-upgrade -y
   sudo apt install -y git python3-venv portaudio19-dev python3-dev build-essential cmake
   ```
4. ```
   git clone <this-repo-url> ~/robot && cd ~/robot
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   .venv/bin/pip install -e .
   ```
5. Install the models manually (never committed): the Piper voice at `[voice] model_path`,
   the chat GGUF at `[chat] model_path`, then `.venv/bin/needle download needle3` and
   ```
   .venv/bin/python -c "from faster_whisper import WhisperModel; WhisperModel('base.en', compute_type='int8')"
   ```
   to pre-fetch the STT weights — same reasoning as Needle: first boot after a deploy
   shouldn't hit the network.
6. Wire the hardware per the pin map and confirm with the matching `scripts/*_test.py`.
7. ```
   sudo cp deploy/robotd.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now robotd
   journalctl -fu robotd
   ```
   Edit `WorkingDirectory`/`ExecStart`/`User` first if the repo isn't at `/home/taha/robot`.

## Testing without hardware

```
pytest
```

All tests run without a Pi or any device attached. `robotd` is installed editable so
`python scripts/whatever.py` and `python -m robotd` both resolve it:

```
.venv/bin/pip install -e .
```

Re-run that after changing `pyproject.toml`; edits inside `robotd/` take effect immediately.

**Voice (Piper).** `python scripts/speaker_test.py` confirms the default output is the USB
speaker, then `python scripts/voice_test.py` proves Piper streams through it.

No sound, or `robotd` logs `paInvalidSampleRate`? No input, or the mic records silence? ALSA's
`"default"` fell back to card 0 (HDMI). `aplay -l` and `arecord -l` list card names — on this
robot both are the one USB composite device, card name `Device`. Pin it system-wide **by
name** (USB numbering isn't stable across reboots):

```
sudo tee /etc/asound.conf >/dev/null <<'EOF'
pcm.!default { type plug; slave.pcm "hw:CARD=Device" }
ctl.!default { type hw; card "Device" }
EOF
```

Use `/etc/asound.conf`, not `~/.asoundrc`: `robotd` runs as a systemd service, and a per-user
file the service can't read would break the mic and the speaker together, since they're the
same device.

If a config seems to vanish at reboot, check in this order:
1. `mount | grep -E 'overlay|on / '` — the Overlay File System (`raspi-config` → Performance)
   makes `/` a RAM overlay, discarding every write at reboot.
2. `ls -la ~/.asoundrc /root/.asoundrc` — `sudo nano ~/.asoundrc` writes `/root/.asoundrc`, so
   it was never in your home to begin with.
3. `ls -la ~ | grep -i asound` — saved as `asoundrc` or `.asoundrc.txt`.

A leftover `~/.asoundrc` overrides `/etc/asound.conf`. Delete it once the system-wide file is
in place, or the old one still decides.

**Brain (Needle 3).** Pre-fetch weights so boot doesn't hit the network:

```
.venv/bin/needle download needle3
python scripts/brain_test.py --text "turn the light on and say good evening"
```

**Chat model (llama.cpp).** May compile from source. Install a GGUF at `[chat] model_path`,
then `python scripts/chat_test.py --model <path>` for reply text, tok/s, latency and peak RSS.
A missing or unloadable GGUF degrades to a logged warning and `NullChat`, same as `open_led()`.

**Hearing (mic + Whisper).** `python scripts/mic_test.py` records a few seconds and plays it
straight back through `arecord`/`aplay`, below the HAL — confirms the capture device is wired
before any Python audio library is involved. `python scripts/stt_test.py` then records one
clip through the real `PyAudioMicrophone` and transcribes it with `tiny.en` and `base.en`,
printing text/latency/peak RSS so `[stt] model` in `config/robot.toml` can be picked from real
numbers. `python scripts/button_test.py` prints press/release events straight off `gpiozero`
to prove the wiring and pull-up before `HearingActor` is trusted with it. Unlike the LED and
the chat model, a missing mic **fails startup** (see `Supervisor`) — it's the same USB device
the speaker already hard-depends on, so degrading one and not the other would be incoherent;
the button degrades like the LED (`open_button()`).

**Offline check.** Pull the network cable and repeat a few `/chat` prompts, then hold the
button and speak a couple more — all three models must keep answering.

## Deploy loop (on the Pi)

```
./deploy/deploy.sh
```

`git pull`, install any new dependencies, restart `robotd`, tail the log. Also (re)writes
`/etc/asound.conf` if it's missing. There's no automated device check — verify a wiring
change by watching `python -m robotd` start cleanly and exercising the device over
`POST /chat`.
