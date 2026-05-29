# melee-macros

One-button competitive **Fox** tech for Super Smash Bros. Melee on
Slippi/Dolphin. Reads your physical controller (GameCube adapter, Switch Pro,
Xbox, DualShock, generic USB — anything SDL sees), passes inputs through to the
game, and when you press a trigger button/combo, injects a **frame-timed macro**
so you can land wavedashes, waveshines, multishines, SHFFLs, ledgedashes, etc.
without the execution.

The frame data behind every macro is in [docs/fox-techniques.md](docs/fox-techniques.md).

## How it works

```
physical pad ──SDL──▶ melee-macros ──pipe commands──▶ Dolphin (GCN port = pipe device)
                          │
                          └─ trigger pressed? play macro frames instead of passthrough
```

This program is the **sole** input source Dolphin sees. Dolphin's controller
port is set to a *pipe input* device; your real pad is read here and forwarded.
When a trigger fires, the macro's per-frame controller states override
passthrough until it finishes.

Two timing backends:
- **`pipe`** (default): writes to Dolphin's named pipe, paced by a wall-clock
  60 Hz loop. No extra setup; timing is open-loop (good for most movement tech).
- **`libmelee`**: steps the game one frame at a time via libmelee for
  frame-accurate timing (best for L-cancel/landing-relative macros). Requires
  `uv sync --extra libmelee` and a running Slippi Dolphin + ISO.

## Install (uv)

This project uses [uv](https://docs.astral.sh/uv/). It pins Python 3.13 (pygame
has no 3.14 wheels yet) and manages the virtualenv for you:

```bash
uv sync                       # creates .venv, installs pygame + PyYAML
uv sync --extra libmelee      # also install the frame-accurate backend (libmelee)
```

Then prefix commands with `uv run` (it uses the project venv automatically), e.g.
`uv run python run.py check`. A `requirements.txt` is also provided if you
prefer pip in your own venv.

## Set up Dolphin pipe input

1. In Dolphin/Slippi: **Controllers → Port 1 → Standard Controller → Configure**.
2. In the **Device** dropdown, pick `Pipe/0/slippibot` (create it if needed; see below).
3. Map the GCN inputs to the pipe device's inputs (the pipe exposes A, B, X, Y,
   Z, Start, L, R, D-Pad, Main Stick, C-Stick, analog L/R).

On this machine the pipe file lives at
`~/Library/Application Support/com.project-slippi.dolphin/netplay/User/Pipes/slippibot`
(the Slippi Launcher's netplay Dolphin user dir). This tool auto-detects and
creates it; `config.yaml` is already pre-filled with this path.

> **Note:** the GCPadNew.ini for Port 1 has already been written to point at
> `Pipe/0/slippibot`, with your original keyboard mapping backed up and saved as
> the "Keyboard" profile. So you can skip the manual in-app mapping below — just
> confirm Port 1 shows the pipe device.

## Configure your controller

Button/axis indices differ per pad, so they live in
[config.yaml](config.yaml) under `controller`. The defaults target a typical
Xbox-style SDL2 layout. Map your physical buttons to logical names:

- Game buttons `A B X Y Z L R START D_UP/DOWN/LEFT/RIGHT` pass through to Melee.
- `MOD` is a **macro-only modifier** (never sent to the game) for combo triggers.

## Bind triggers

In `config.yaml`, each `triggers` entry fires a macro on the rising edge of all
listed buttons; longer combos win. The default scheme keeps gameplay buttons
free by using the (unused-in-Melee) D-pad and a `MOD` modifier:

```yaml
triggers:
  - { buttons: [D_RIGHT], macro: wavedash_forward }
  - { buttons: [D_DOWN],  macro: shine }
  - { buttons: [MOD, B],  macro: multishine }
```

## Use it

```bash
uv run python run.py list                 # all 44 macros + frame lengths
uv run python run.py dump wavedash_forward   # per-frame input table for a macro
uv run python run.py check                # compile + validate every macro (no game)
uv run python run.py probe                # print live button/axis indices for config.yaml
uv run python run.py run                  # start the live engine (Ctrl-C to stop)
```

### Finding your controller's indices

Button/axis numbers differ per pad. Run `uv run python run.py probe`, then press each
button and move each stick — it prints the index that changed:

```
$ uv run python run.py probe
Detected 1 controller(s):
  index 0: Xbox One S Controller
Probing index 0: Xbox One S Controller (6 axes, 15 buttons, 0 hats).
button down: index [0]      # <- pressed A
axis 0: +0.98               # <- moved left stick right
button down: index [11]     # <- D-pad up (this pad has 0 hats, so D-pad = buttons)
```

Copy those numbers into the `controller:` section of `config.yaml`
(`--index N` if you have more than one pad). Note: if your pad reports **0 hats**
(like the Xbox One S here), the D-pad arrives as buttons — map those indices to
`D_UP`/`D_DOWN`/`D_LEFT`/`D_RIGHT` in the `buttons:` block.

## Important: legitimacy & accuracy

- **Macros automate inputs.** Most tournaments/ranked ladders ban input
  automation. Use this for practice, local play, and learning execution.
- **State-dependent macros** (L-cancel, teching, ledgedash, multishine drift,
  throw follow-ups) can't be perfectly fixed-frame in open-loop `pipe` mode —
  they're flagged `STATE-DEPENDENT` in `uv run python run.py list`. Use `libmelee`
  mode for landing-relative reliability.
- A few research frame values are **contested** (see the bottom of
  [docs/fox-techniques.md](docs/fox-techniques.md)); validate against a
  Slippi/20XX frame counter before relying on them.

## Layout

```
run.py                       CLI (list / dump / check / probe / run)
pyproject.toml               uv project (pins Python 3.13, deps)
config.yaml                  pipe path, controller map, trigger bindings
requirements.txt             pip alternative to uv
docs/
  fox-techniques.md          master frame-data reference + technique→macro map
  research/                  detailed source research (movement, shine, aerials)
src/melee_macros/
  inputs.py                  ControllerState + coordinate convention
  macro.py                   MacroBuilder timeline → per-frame states
  macros/fox.py              all 44 Fox macros
  library.py                 macro registry
  controller.py              SDL physical-pad reader
  pipe.py                    Dolphin named-pipe writer (diffed commands)
  backends.py                PipeBackend (wall-clock) + LibmeleeBackend (frame-stepped)
  engine.py                  read → trigger detect → passthrough/macro → send
  config.py                  config.yaml loader
tests/test_engine.py         engine wiring smoke tests (no hardware)
```
```bash
uv run python tests/test_engine.py        # run the smoke tests
```
