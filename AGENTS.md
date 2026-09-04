# AGENTS.md

Operating notes for anyone (human or agent) working in this repo. The full milestone plan
lives outside this repo; this file only covers what's needed to work on the code correctly.

## What this is

A Raspberry Pi 5 desk companion robot, built one milestone at a time. Actors (Pykka)
communicate by message, own one device each, and are never imported by each other. See
"Recipe: adding a device" below before writing any new hardware code.

Current status: **M0 done** — package skeleton, config loader, one LED. **M1 done** — Pykka
actors, `StatusActor` owns the LED, and a `POST /command` HTTP endpoint drives it via
`CommandActor`. **M2 is implemented pending its USB-speaker Pi check** — `VoiceActor` streams
Piper TTS to the system-default audio device. Motors and the dead-man's switch move to the end
of the plan (M14) — see `docs/plan.md`.

## Repo map

```
robotd/
  __main__.py     entrypoint; python -m robotd
  config.py       loads config/robot.toml; RobotConfig.pin(name) -> gpio number
  messages.py     the message contract — frozen dataclasses actors send each other
  web.py          HTTP boundary only (transport) — POST /command -> CommandActor.ask()
  hal/            hardware seam — one Protocol + one real implementation per device
    leds.py       Led protocol + GpioLed
    audio.py      Speaker protocol + PyAudioSpeaker (system-default output)
  actors/
    status.py     StatusActor — owns the LED, handles SetLed (on/off only)
    command.py    CommandActor — routes external Command requests to device actors
    voice.py      VoiceActor — streams Speak text through TTS and the speaker
    supervisor.py Supervisor — starts/stops the actor tree
  models/
    tts.py        TextToSpeech protocol + PiperTts
scripts/          hardware bring-up bench — plain, blocking, run over SSH
tests/            pytest — logic only, no hardware required
  doubles.py      test doubles implementing hal/ protocols — never in robotd/
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
3. If the brain should be able to use it, register it in `tools.py` — `add_action` or
   `add_sensor`. This is the only place `BrainActor` learns about a device.
4. If it should be reachable over `POST /command`, add a `command(action) -> Message | None`
   translator next to the actor's own module (see `robotd/actors/status.py`) and one line
   in `Supervisor`'s route table. `CommandActor` never learns a device's message types
   directly.
5. Add a bring-up script in `scripts/` that talks to the device directly (not through the
   HAL) — this is how you debug the wiring by hand.

No actor should need to change just because a device was added.

## HTTP command endpoint

```
curl -X POST -d '{"device":"led","action":"on"}'  http://<pi-host>:8080/command
curl -X POST -d '{"device":"led","action":"off"}' http://<pi-host>:8080/command
```

`robotd/web.py` is transport only — it decodes JSON and calls `CommandActor.ask()`; it
knows nothing about device names or message types. Binds `0.0.0.0:8080` with no auth —
fine on a home LAN, worth remembering once anything with motors is exposed this way (M14).

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

## Testing without hardware

```
pytest
```
All tests run without a Pi, a GPIO backend, or any physical device attached.

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
