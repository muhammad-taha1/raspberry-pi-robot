# AGENTS.md

Operating notes for anyone (human or agent) working in this repo. The full milestone plan
lives outside this repo; this file only covers what's needed to work on the code correctly.

## What this is

A Raspberry Pi 5 desk companion robot, built one milestone at a time. Actors (Pykka)
communicate by message, own one device each, and are never imported by each other. See
"Recipe: adding a device" below before writing any new hardware code.

Current status: **M0 done** — package skeleton, config loader, one LED. **M1 done** — Pykka
actors, `StatusActor` owns the LED, and a `POST /command` HTTP endpoint drives it via
`CommandActor`. **M2 done** — `VoiceActor` streams Piper TTS to the system-default audio
device, verified on the Pi's USB speaker; the LED's GPIO claim degrades to a warning
(`robotd/hal/leds.py`'s `open_led`) instead of crashing the daemon when its circuit is
disconnected. **M3 done (reduced scope)** — `GET /` serves a page (`robotd/static/index.html`)
with a text box that speaks through `POST /say`; `GET /state` deferred to M4. **M5 done, moved
ahead of M4** — `BrainActor` runs Needle 3 (`cactus-needle`) fully on-device: a `POST /chat`
utterance becomes tool calls (`say`, `set_led`) dispatched through `tools.py`'s `ToolRegistry`,
with `confidence` logged on every completion. Moved ahead of M4 because it needed no new
hardware — the existing status page grew a chat box — while M4's ears just add a second way to
produce the same `Transcript` message this milestone already introduced. **Next: M4** — ears
(push-to-talk), and `GET /state` picking up real content (transcripts). Motors and the
dead-man's switch move to the end of the plan (M14) — see `docs/plan.md`.

## Repo map

```
robotd/
  __main__.py     entrypoint; python -m robotd
  config.py       loads config/robot.toml; RobotConfig.pin(name) -> gpio number
  messages.py     the message contract — frozen dataclasses actors send each other
  tools.py        ToolRegistry + build_registry(voice, status) — how a device becomes a tool
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
    brain.py      BrainActor — Transcript -> LlmProvider.complete() -> ToolRegistry.dispatch()
    supervisor.py Supervisor — starts/stops the actor tree
  models/
    tts.py        TextToSpeech protocol + PiperTts
    llm.py        LlmProvider protocol + NeedleLlm (Needle 3, on-device, owns its own history)
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
   `say`/`set_led` there). The function's name and docstring *are* the schema Needle reads, so
   there's no separate description string to keep in sync. This is the only place `BrainActor`
   learns about a device.
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
wired to `POST /say`, and below it a chat box wired to `POST /chat` showing the model's
`reasoning`/`confidence` under each reply, viewable from a phone on the same LAN.

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
  only by being registered as a tool in `tools.py` (`NeedleLlm` owns the conversation window
  itself); the moment `BrainActor` needs to `tell()` a device directly, that device belongs in
  the registry instead.

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

For M2 on Raspberry Pi OS, install PortAudio build prerequisites before refreshing the virtual
environment after pulling the dependency change:

```
sudo apt install portaudio19-dev python3-dev
.venv/bin/pip install -r requirements.txt
```

Install `en_GB-alan-medium.onnx` and its matching `.onnx.json` sidecar manually at the path in
`config/robot.toml`. Run `python scripts/speaker_test.py` to confirm the system-default output
is the USB speaker, then `python scripts/voice_test.py` to prove Piper streams through it before
starting `python -m robotd`.

**If `speaker_test.py`/`voice_test.py` produce no sound (or `robotd`'s log shows
`paInvalidSampleRate`):** ALSA's `"default"` device has no config pinning it, so it falls back
to card 0 — on this hardware that's `vc4hdmi0` (the Pi's HDMI output, no monitor attached, and
it doesn't support Piper's 22050Hz rate anyway), not the USB speaker. `aplay -l` shows each
card's index and name; USB card numbering isn't stable across reboots/hotplugs, so pin
`~/.asoundrc` **by name**, not index:
```
pcm.!default {
    type plug
    slave.pcm "hw:CARD=Device"
}
ctl.!default {
    type hw
    card "Device"
}
```
(`Device` here is the USB card's name from `aplay -l`'s `card 2: Device [USB Composite
Device]` — substitute whatever your `aplay -l` actually shows.) `type plug` also makes ALSA
resample if a future device doesn't natively support Piper's rate, instead of PortAudio
hard-failing. Re-run `speaker_test.py` to confirm before trusting `robotd`.

For M5, `cactus-needle` is a pure-Python wheel — no ARM64 build step, no extra apt packages.
Its weights are fetched from Hugging Face and cached on first run; pre-fetch them once on the
Pi so `python -m robotd` doesn't hit the network at boot:

```
.venv/bin/pip install -r requirements.txt
.venv/bin/needle download needle3
python scripts/brain_test.py --text "turn the light on and say good evening"
```

`brain_test.py` is the bring-up bench for the model itself — confirms install, weight cache,
and a plausible `confidence`/decode speed on the Pi 5 before trusting `python -m robotd`'s
`POST /chat`. Pull the network cable and repeat a `/chat` request to confirm the model still
answers fully offline — that's the entire point of running it on-device.

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
