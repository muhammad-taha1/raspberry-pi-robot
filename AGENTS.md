# AGENTS.md

Operating notes for anyone (human or agent) working in this repo. The full milestone plan
lives outside this repo; this file only covers what's needed to work on the code correctly.

## What this is

A Raspberry Pi 5 desk companion robot, built one milestone at a time. Actors (Pykka)
communicate by message, own one device each, and are never imported by each other. See
"Recipe: adding a device" below before writing any new hardware code.

Current status: **M0** — package skeleton, config loader, one LED. No actors yet.

## Repo map

```
robotd/
  __main__.py     entrypoint; python -m robotd [--check]
  config.py       loads config/robot.toml; RobotConfig.pin(name) -> gpio number
  hal/            hardware seam — one Protocol + one real implementation per device
    leds.py       Led protocol + GpioLed
scripts/          hardware bring-up bench — plain, blocking, run over SSH
tests/            pytest — logic only, no hardware required
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

## Recipe: adding a device

1. Add a `Protocol` + one real implementation in `robotd/hal/` (or `robotd/models/` for an
   inference engine). No `Fake*` class — those live only in `tests/doubles.py`.
2. Add its pin(s)/address to `config/robot.toml`.
3. If the brain should be able to use it, register it in `tools.py` — `add_action` or
   `add_sensor`. This is the only place `BrainActor` learns about a device.
4. Add a bring-up script in `scripts/` that talks to the device directly (not through the
   HAL) — this is how you debug the wiring by hand.

No actor should need to change just because a device was added.

## Invariants

- Motors stop on exit, on exception, and on command timeout (dead-man's switch, from M1).
- No actor blocks its mailbox — slow work (LLM calls, TTS, frame capture) belongs to the
  actor whose only job is that thing.
- `robotd/` ships real implementations only. Test doubles live in `tests/doubles.py`.
- `scripts/` stays plain, blocking, and actor-free — it exists to test wiring, not logic.

## Testing without hardware

```
pytest
```
All tests run without a Pi, a GPIO backend, or any physical device attached.

## Deploy loop (on the Pi)

```
./deploy/deploy.sh
```

Pulls latest, restarts the `robotd` service, and tails its log (`git pull`,
`sudo systemctl restart robotd`, `journalctl -fu robotd`).

`python -m robotd --check` exercises every registered real device once and prints a
pass/fail line per device — run it after any wiring change, before trusting the service.
