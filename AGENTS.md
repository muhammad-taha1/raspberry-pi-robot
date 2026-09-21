# AGENTS.md

Operating notes for anyone (human or agent) working in this repo. The full milestone plan
lives outside this repo; this file only covers what's needed to work on the code correctly.

## What this is

A Raspberry Pi 5 desk companion robot, built one milestone at a time. Actors (Pykka)
communicate by message, own one device each, and are never imported by each other. See
"Recipe: adding a device" below before writing any new hardware code.

Current milestone status, decisions, and rationale live in `docs/plan.md` (gitignored,
local-only — see "Documentation" below).

## Documentation

`docs/` is gitignored — local-only, never committed, never reaches the Pi via `git pull` (see
"Repo hygiene" in `docs/plan.md`'s M0 entry). It holds the project's working memory:

- `docs/plan.md` — the milestone plan, current status, and the decisions behind it
- `docs/architecture.md` — current actor tree, message flow, and a behaviour matrix for `/chat`
- `docs/open-questions.md` — deferred decisions; check before starting a new milestone
- `docs/pinout.md` — full board capability reference (J8 header, ports, SoC)

Regenerate `docs/architecture.md` whenever a milestone adds or rewires an actor — it says so
at its own top, and it's the fastest way to answer "why does X reach device Y two ways?"

## Repo map

```
robotd/
  __main__.py     entrypoint; python -m robotd
  config.py       loads config/robot.toml; RobotConfig.pin(name) -> gpio number
  messages.py     the message contract — frozen dataclasses actors send each other
  tools.py        ToolRegistry + build_registry(status) — how a device becomes a tool
  phrases.py      generic ACK/FAILED/UNSURE phrase sets — used by BrainActor and NullChat
  web.py          HTTP boundary only (transport) — GET /, POST /command, POST /say, POST /chat
  static/
    index.html    the status page GET / serves — read from disk per request
  hal/            hardware seam — one Protocol + one real implementation per device
    leds.py       Led protocol + GpioLed, open_led() falls back to a no-op if the pin can't be claimed
    audio.py      Speaker protocol + PyAudioSpeaker (system-default output)
  actors/
    status.py     StatusActor — owns the LED, handles SetLed (on/off only)
    command.py    CommandActor — routes external Command requests to device actors
    voice.py      VoiceActor — streams Speak text through TTS and the speaker; command() translates any action string to Speak
    brain.py      BrainActor — Transcript -> LlmProvider.complete() -> ToolRegistry.dispatch(), or ChatProvider.reply() if nothing to dispatch
    supervisor.py Supervisor — starts/stops the actor tree
  models/
    tts.py        TextToSpeech protocol + PiperTts
    llm.py        LlmProvider protocol + NeedleLlm (Needle 3, on-device, owns its own history)
    chat.py       ChatProvider protocol + LlamaCppChat / NullChat — prose Needle can't produce
scripts/          hardware bring-up bench — plain, blocking, run over SSH
tests/            pytest — logic only, no hardware required
  doubles.py      test doubles implementing hal/ and models/ protocols — never in robotd/
config/robot.toml the authoritative pin map
deploy/robotd.service
```

`articles/` and `.claude/` are gitignored — local only, never pulled to the Pi.

## Pin map

The **only** authoritative source is `config/robot.toml`. Never hardcode a GPIO number
anywhere else — read it via `RobotConfig.pin(name)`.

| Name | GPIO | Device |
|---|---|---|
| `led` | 24 | Status LED |
| `motor_in1` | 17 | L298N |
| `motor_in2` | 27 | L298N |
| `motor_in3` | 22 | L298N |
| `motor_in4` | 23 | L298N |

(I²C and SPI addresses will be added here as those devices arrive, from M8 onward.)

Board capability reference (full J8 header, ports, SoC): `docs/pinout.md`
(local-only, see below) or run `pinout` directly on the Pi.

## Recipe: adding a device

1. Add a `Protocol` + one real implementation in `robotd/hal/` (or `robotd/models/` for an
   inference engine). No `Fake*` class — those live only in `tests/doubles.py`.
2. Add its pin(s)/address to `config/robot.toml`.
3. If the brain should be able to use it, register it in `tools.py`'s `build_registry()` — a
   small function taking the actor and `tell()`ing it, passed to `registry.add_action()` (see
   `set_led` there). The function's name and docstring *are* the schema Needle reads, so
   there's no separate description string to keep in sync. This is the only place `BrainActor`
   learns about a device. Do not add a `say`-style tool for prose — that's the chat model's
   job now (`robotd/models/chat.py`), consulted only when Needle dispatches nothing.
4. If it should be reachable over `POST /command`, add a `command(action) -> Message | None`
   translator next to the actor's own module (see `robotd/actors/status.py`) and one line
   in `Supervisor`'s route table. `CommandActor` never learns a device's message types
   directly.
5. Add a bring-up script in `scripts/` that talks to the device directly (not through the
   HAL) — this is how you debug the wiring by hand.

No actor should need to change just because a device was added.

## HTTP endpoints

```
curl -X POST -d '{"device":"led","action":"on"}'  http://<pi-host>:8080/command
curl -X POST -d '{"device":"led","action":"off"}' http://<pi-host>:8080/command
curl -X POST -d '{"text":"Good evening."}'        http://<pi-host>:8080/say
curl -X POST -d '{"text":"turn on the light"}'    http://<pi-host>:8080/chat
```
`GET http://<pi-host>:8080/` opens the status page (`robotd/static/index.html`) — a text box
wired to `POST /say`, and below it a chat box wired to `POST /chat` showing the spoken reply
plus `reasoning`/`confidence`/tool calls as debug under each turn, viewable from a phone on
the same LAN. Full request/response flow and every `/chat` outcome (tool ack, chat reply,
unsure fallback): `docs/architecture.md`.

`robotd/web.py` is transport only — it decodes JSON and calls `CommandActor.ask()` or
`BrainActor.ask()`; it knows nothing about device names or message types, with two deliberate
exceptions: `POST /say` hardcodes the `"voice"` device, since an utterance is a `{text}` body,
not a `{device, action}` one; and `POST /chat` talks to `BrainActor` directly rather than
through `CommandActor`'s route table, since a reply is the entire point of `/chat` and
`CommandActor` only `tell()`s (fire-and-forget) so it structurally cannot carry one back.
`/chat` gets a longer `ask()` timeout than `/command`/`/say` (inference takes longer than a
`tell()`). Binds `0.0.0.0:8080` with no auth — fine on a home LAN, worth remembering once
anything with motors is exposed this way (M14).

## Invariants

- A device-owning actor stays dumb: it exposes primitives (`SetLed(on/off)`, later
  `Drive`/`Stop`), never a pattern or policy (blink timing, a drive sequence). Behaviour
  that plays those primitives over time belongs in whichever actor actually needs it — e.g.
  M8's attention/face logic will drive `StatusActor` via `SetLed`, `StatusActor` itself
  never grows a `Blink` message. This is the actual point of decomposing into actors: logic
  splits across collaborating pieces instead of accreting in the device owner.
- A device is turned off and closed when its actor stops, on clean stop and on failure
  alike (`StatusActor.on_stop`/`on_failure`, from M1). Motors get the same treatment plus a
  dead-man's switch when they arrive in M14.
- No actor blocks its mailbox — slow work (LLM calls, TTS, frame capture) belongs to the
  actor whose only job is that thing. Timed/repeating behaviour (the future dead-man's
  switch, or any future periodic pattern) is a self-rearming `threading.Timer` that
  `tell()`s the actor a private message, never a `sleep()` inside `on_receive`.
- `robotd/` ships real implementations only. Test doubles live in `tests/doubles.py`.
- `scripts/` stays plain, blocking, and actor-free — it exists to test wiring, not logic.
- `BrainActor` holds no device references and no conversation history. A device reaches it
  only by being registered as a tool in `tools.py` (`NeedleLlm` and `ChatProvider` each own
  their own conversation window); the moment `BrainActor` needs to `tell()` a device directly,
  that device belongs in the registry instead.
- Prose is the chat model's job, never a Needle tool: Needle owns GPIO calls, `ChatProvider`
  (`robotd/models/chat.py`) owns spoken sentences, and `BrainActor` consults the latter only
  when Needle dispatches nothing.

## Raspberry Pi setup (first boot to running service)

1. **Flash Raspberry Pi OS** (64-bit, Bookworm or later — required for `rpi-lgpio`/Pi 5
   support) with Raspberry Pi Imager. In the Imager's settings (gear icon / Ctrl+Shift+X)
   before writing: set hostname, enable SSH (password or your public key), set the
   username/password, and join Wi-Fi if not using Ethernet. This avoids a monitor/keyboard
   entirely.
2. **Boot it, then SSH in**: `ssh <user>@<hostname>.local` (mDNS; use the DHCP-assigned IP if
   `.local` doesn't resolve on your network).
3. **Update and install system prerequisites**:
   ```
   sudo apt update && sudo apt full-upgrade -y
   sudo apt install -y git python3-venv portaudio19-dev python3-dev build-essential cmake
   ```
4. **Clone the repo and create the venv**:
   ```
   git clone <this-repo-url> ~/robot
   cd ~/robot
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   .venv/bin/pip install -e .
   ```
5. **Install the models manually** (never committed — see `.gitignore`): the Piper voice at
   `config/robot.toml`'s `[voice] model_path`, and the chat GGUF at `[chat] model_path`; then
   `.venv/bin/needle download needle3` to pre-fetch Needle's weights. See "Testing without
   hardware" below for the per-subsystem bring-up scripts that confirm each one before
   trusting `python -m robotd`.
6. **Wire the hardware** per `config/robot.toml`'s pin map (below) and confirm with the
   matching `scripts/*_test.py` bring-up script.
7. **Install the systemd service** so the robot survives a reboot:
   ```
   sudo cp deploy/robotd.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now robotd
   journalctl -fu robotd
   ```
   Edit `deploy/robotd.service`'s `WorkingDirectory`/`ExecStart`/`User` first if the repo
   isn't cloned to `/home/taha/robot` or the user isn't `taha`.
8. From then on, `./deploy/deploy.sh` (`git pull`, restart, tail the log) is the update loop —
   see "Deploy loop" below.

## Testing without hardware

```
pytest
```
All tests run without a Pi, a GPIO backend, or any physical device attached.

`robotd` is installed editable into the venv so `python scripts/whatever.py` and
`python -m robotd` both resolve it regardless of invocation style or working directory:

```
.venv/bin/pip install -e .
```
Re-run this after pulling a change to `pyproject.toml` (e.g. a new package-data entry); plain
edits inside `robotd/` take effect immediately without it.

**Voice (Piper).** Needs PortAudio's headers to build `PyAudio`:
```
sudo apt install portaudio19-dev python3-dev
.venv/bin/pip install -r requirements.txt
```
Install `en_GB-alan-medium.onnx` + its `.onnx.json` sidecar manually at the path in
`config/robot.toml`. `python scripts/speaker_test.py` confirms the system-default output is
the USB speaker, then `python scripts/voice_test.py` proves Piper streams through it.

If there's no sound (or `robotd` logs `paInvalidSampleRate`): ALSA's `"default"` falls back to
card 0 (`vc4hdmi0`, the Pi's HDMI out, no monitor attached and wrong sample rate), not the USB
speaker. `aplay -l` lists card names; pin `~/.asoundrc` **by name** (USB card numbering isn't
stable across reboots):
```
pcm.!default { type plug; slave.pcm "hw:CARD=Device" }
ctl.!default { type hw; card "Device" }
```
(substitute the USB card's name from `aplay -l`). Re-run `speaker_test.py` to confirm.

**Brain (Needle 3).** Pure-Python wheel, no ARM64 build step. Pre-fetch weights once so
`python -m robotd` doesn't hit the network at boot:
```
.venv/bin/pip install -r requirements.txt
.venv/bin/needle download needle3
python scripts/brain_test.py --text "turn the light on and say good evening"
```
`brain_test.py` confirms install, weight cache, and a plausible `confidence`/decode speed
before trusting `POST /chat`.

**Chat model (llama.cpp).** May compile `llama.cpp` from source unless a prebuilt ARM64 wheel
exists:
```
sudo apt install build-essential cmake
.venv/bin/pip install -r requirements.txt
```
Install a chat GGUF manually at the path in `config/robot.toml`'s `[chat]` section, out of Git
like the Piper voice. `python scripts/chat_test.py --model <path>` prints reply text, tok/s,
latency, and peak RSS for canned prompts before trusting `POST /chat`'s chat replies. A missing
or failed-to-load GGUF degrades `robotd` to a logged warning and a spoken fallback
(`robotd/models/chat.py`'s `NullChat`) instead of crashing — same pattern as the LED's
`open_led()`.

**Offline check.** Pull the network cable and repeat a few `/chat` prompts (a joke, "turn on
the light") — both Needle and the chat model must keep answering; that's the point of running
both on-device.

## Deploy loop (on the Pi)

```
./deploy/deploy.sh
```

Pulls latest, restarts the `robotd` service, and tails its log (`git pull`,
`sudo systemctl restart robotd`, `journalctl -fu robotd`).

There's no automated device check — the pin/device set changes too often for a
hand-maintained one to be worth it. Verify a wiring change by watching `python -m robotd`
start cleanly and exercising the device over `POST /command` (or watching its actor's
behaviour directly once it has one).
