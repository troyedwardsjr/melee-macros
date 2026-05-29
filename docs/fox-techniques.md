# Fox Competitive Techniques — Master Reference

This is the consolidated frame-data reference behind the macros in
`src/melee_macros/macros/fox.py`. It links to three detailed research files and
maps every technique to the macro that performs it.

- [Movement tech](research/movement.md) — wavedash, dash dance, foxtrot, pivots, moonwalk, JC/boost grab, crouch cancel
- [Shine / defense / recovery](research/shine_defense.md) — shine, waveshine, multishine, shine OOS, teching, powershield, Firefox, Illusion, ledgedash
- [Aerials / L-cancel / combos](research/aerials_combos.md) — L-cancel, SHFFL, aerial frame data, drillshine, pillar, upthrow uair

> Target: SSBM NTSC 1.02 on Slippi/Dolphin, 60 fps. Character: **Fox**.

## Frame conventions

The research docs are **1-indexed** (frame 1 = first frame of an action; Fox
"airborne on frame 4" after a 3-frame jumpsquat). The macro builder is
**0-indexed** (frame 0 = first applied frame). So research "frame N" == builder
"frame N-1". The CLI (`python run.py dump <macro>`) prints builder frames.

## Load-bearing Fox constants

| Constant | Value | Used by |
|---|---|---|
| Jumpsquat | **3 frames** (airborne on builder f3) | every jump-based macro |
| Short-hop window | release jump within builder f0–1 | `short_hop`, SHFFL |
| Initial dash / dash-dance window | **11 frames** | `dash_dance_*`, `foxtrot_*` |
| Shine jump-cancellable | builder **f3** (research f4) | `jc_shine`, `waveshine_*`, `multishine` |
| Multishine reshine | builder **f6** (period 6) | `multishine` |
| Wavedash airdodge | first airborne frame | `wavedash_*`, `waveshine_*` |
| Wavedash landing lag | 10 frames | (informational) |
| Pivot window | **1 frame** | `pivot_*` |
| L-cancel window | 7 frames before landing | SHFFL, `drillshine` |
| Firefox aim lock | builder **f41** (research f42), launches f42 | `firefox_*` |
| Illusion forward-travel | 5 frames (= 5 shorten lengths) | `illusion_forward_short` |
| Ledge intangibility | 37 frames; Fox GALINT 15 | `ledgedash_*` |
| Tech window / lockout | 20f window / 40f lockout (never double-tap) | `tech_*` |

## Analog coordinates

Macros are authored in **unit** convention (−1..+1, +y = up, 0 = neutral) and
compiled to **pipe** convention (0..1, 0.5 = neutral, y up) for Dolphin.
`pipe = 0.5 + unit/2`. Key values:

| Input | Unit (x, y) | Pipe (x, y) |
|---|---|---|
| Full down (shine/crouch) | (0, −1) | (0.5, 0.0) |
| Wavedash down-forward (~17°) | (+0.85, −0.50) | (0.925, 0.250) |
| Ledgedash airdodge (~45° into stage) | (±0.70, −0.70) | (0.85/0.15, 0.15) |
| Firefox up-forward 45° | (+0.70, +0.70) | (0.85, 0.85) |

## Technique → macro map

### Movement
| Technique | Macro(s) |
|---|---|
| Short hop / full hop | `short_hop`, `full_hop` |
| Wavedash | `wavedash_forward`, `wavedash_back` |
| Wavedance / wavesurf | chain `wavedash_*` then dash (see research §4) |
| Dash dance | `dash_dance_right`, `dash_dance_left` |
| Foxtrot / extended dash dance | `foxtrot_right`, `foxtrot_left` |
| Moonwalk | `moonwalk_right`, `moonwalk_left` |
| Pivot / empty pivot | `pivot_right`, `pivot_left` |
| JC grab | `jc_grab` |
| Boost grab | `boost_grab` |

### Shine
| Technique | Macro(s) |
|---|---|
| Shine | `shine` |
| JC shine | `jc_shine` |
| Waveshine | `waveshine_forward`, `waveshine_back` |
| Multishine | `multishine` |
| Shine OOS | `shine_oos` |
| Drillshine | `drillshine` |

### Aerials / combos
| Technique | Macro(s) |
|---|---|
| SHFFL aerials | `shffl_nair`, `shffl_fair`, `shffl_bair`, `shffl_uair`, `shffl_dair` |
| Upthrow upair | `upthrow_uair` |
| Pillar | `drillshine` + `waveshine_*` chained |

### Defense / tech
| Technique | Macro(s) |
|---|---|
| Tech in place / roll | `tech_in_place`, `tech_roll_left`, `tech_roll_right` |
| Spotdodge | `spotdodge` |
| Roll | `roll_left`, `roll_right` |
| Powershield | `powershield` |

### Recovery
| Technique | Macro(s) |
|---|---|
| Firefox (up-B) angles | `firefox_up`, `firefox_up_forward`, `firefox_up_back`, `firefox_side_forward`, `firefox_side_back` |
| Illusion (side-B) | `illusion_forward`, `illusion_back`, `illusion_forward_short` |
| Ledgedash | `ledgedash_stage_right`, `ledgedash_stage_left` |

## State-dependent macros (read before trusting them)

Some techniques are not pure fixed-frame sequences in real play — their timing
depends on game state the open-loop pipe backend can't see:

- **L-cancel / SHFFL / drillshine**: the landing frame depends on fast-fall
  timing and aerial choice. The macros press L across a predicted landing
  window. Use **libmelee mode** (frame-stepped) for reliable landing-relative timing.
- **Teching / powershield**: only valid on the contact frame. The macro fires a
  single press *when you trigger it* — you must trigger it on the hit.
- **Multishine**: drift and exact reshine frame can desync over many reps; the
  period is a tunable constant (`MULTISHINE_PERIOD`).
- **Ledgedash**: Fox's ECB changes with the pre-ledge animation, shifting the
  jump→airdodge delay. The #1 consistency variable; tune per situation.
- **upthrow_uair**: requires an active grab; the follow-up gap is %/character
  dependent.

These are flagged `STATE-DEPENDENT` in each macro's description (`python run.py list`).

## Contested frame numbers flagged by research

- Nair landing lag / L-cancel lag (Liquipedia 10→7 vs floor(10/2)=5) — verify in-engine.
- Bair total (~33) inferred, not directly sourced.
- Foxtrot "frame 16" is Smash 4/Ultimate, **not** Melee — Melee uses the 11f dash window.
- Deadzone 0.2750 (physics) vs 0.2875 (ruleset).
- Firefox ~352 travel angles (the "8 directions" is a simplification).

Validate the contested values against a Slippi/20XX frame counter before
locking timings for tournament-critical use.
