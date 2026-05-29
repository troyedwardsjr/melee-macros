# Fox (SSBM) — Shine, Defensive & Recovery Frame Data

> Target game: **Super Smash Bros. Melee** (Slippi / Dolphin), **60 fps** (1 frame = 16.67 ms).
> Purpose: precise input + frame-timing reference for a one-button input-injection macro system.
> Convention: frame numbers are **1-indexed** (frame 1 = first frame of the action), matching SmashWiki/FightCore.
> "Actionable" = first frame a new input is accepted.

## Universal Fox constants (reference these everywhere)

| Constant | Value | Notes |
|---|---|---|
| Jumpsquat | **3 frames** | Press jump on frame 0; airborne on frame 4 (the "magic 4th frame"). |
| Shine jump-cancel earliest | **frame 4** | Shine becomes jump-cancellable frames 4–21 (see Shine). |
| Airdodge intangibility | frames **4–29** (26 active) | startup 3, then 26 intangible, 20 recovery (total 49). |
| Wavedash/waveland angle | analog **down-forward / down-back**, ~17–30° below horizontal | shallower angle = longer slide. |

**Analog coordinate note (Melee gate):** stick values are in [-1.0, +1.0] per axis (raw 0–255 → -80…+80 in melee units). Cardinal full = (±1.0, 0) / (0, ±1.0). Wavedash diagonals commonly use ~(±0.95, −0.30) for a low, long slide. libmelee uses `controller.tilt_analog(Button.BUTTON_MAIN, x, y)` with x,y in [0,1] where 0.5 = center.

---

# SHINE TECHNIQUES

## Shine (Down-B / Reflector) — base move

| Property | Frame(s) | Notes |
|---|---|---|
| Hitbox active | **frame 1 only** | Comes out frame 1, set knockback (5%, angle 0°), set hitstun. |
| Intangibility | frame 1 | 1 frame invuln on startup. |
| Jump-cancellable | **frames 4–21** (min) / 4 → (release+1) if held | This is the entire basis of waveshine/multishine. |
| Reflect window | frames 4–21 (min) / 4 → release+1 | Reflects projectiles in this window. |
| Total (tapped) | **39 frames** | If released ASAP. |
| Lag upon release | **19 frames** (reflection lag ~20) | The non-jump-cancelled ending. |
| Shieldstun on shield | 9 frames | Hitlag 4. |

**Input:** `Down` (analog full down, y ≈ −1.0) **+ `B`** simultaneously.
**Key macro fact:** you can jump out starting frame 4. If you do nothing, Fox is locked in shine for 39 frames total. *Always* jump-cancel out for combos.
**Caveats / contested:** after reflecting a projectile Fox cannot jump-cancel for ~⅓ second (~20 frames); turning around during shine disables jump-cancel for 3 frames. Sources agree on frames 4–21; "total 39" assumes immediate release.

## JC (Jump-Cancel) Shine

The atomic unit of waveshine/multishine. Cancel the jumpsquat with a special.

| Step | Frame | Input |
|---|---|---|
| 1. Shine | 0 | `Down` + `B` |
| 2. Jump | ≥4 (earliest) | `Y` (or `X`) — enters 3f jumpsquat |
| 3. Shine again | **+4 after jump press** | `Down` + `B` on the frame Fox would leave ground |

- **One frame too late → you shine in the air. One frame too soon → you just jump.** No margin: must hit the second shine on **frame 4 after pressing jump**.
- Prefer tap-jump (`Y`/`X`) for jump-cancels; analog-up jump complicates angled follow-ups.

## Waveshine (shine → jump → airdodge into ground)

Wavedash directly out of shine. Used to slide forward and re-shine / grab / smash.

| Step | Frame | Input |
|---|---|---|
| 1. Shine | 0 | `Down` + `B` |
| 2. Jump | ≥4 | `Y` (during shine's jump-cancel window) |
| 3. Airdodge into ground | during 3f jumpsquat | `L`/`R` (airdodge) + analog **down-forward** (~(0.95, −0.30)) or **down-back** |

- The airdodge into the ground produces the wavedash slide; Fox is grounded and **actionable immediately on landing** (wavedash land lag is minimal for Fox).
- Macro timing: jump on frame 4 of shine, airdodge on the next frame(s) within jumpsquat. The airdodge angle decides slide direction/distance.
- libmelee: `tilt_analog(MAIN, 0.95, 0.20)` (y<0.5 = down) + `press_button(BUTTON_L)`.

## Multishine (shine → JC → shine, looped)

Repeated JC shines. This is the metronomic loop.

| Cycle | Length | Note |
|---|---|---|
| First shine → second shine | **7 frames** | startup offset for first loop |
| Each subsequent shine → shine | **8 frames** | steady-state loop period |

**Per-cycle input (steady state, 8-frame period):**
1. `Down`+`B` (shine, frame 0 of cycle)
2. `Y` (jump, on frame 4 — the jump-cancel)
3. `Down`+`B` (re-shine on frame 4 after the jump = frame 8 = frame 0 of next cycle)

- **Must shine on the exact frame following the 3-frame jumpsquat (frame 4 after jump).** Zero margin for error — hardest standard Fox tech by hand; trivial for a macro injecting on exact frames.
- Falco's loop is easier for humans (2 extra jumpsquat frames) but Fox's numbers are the 7/8 above.
- Macro implementation: alternate `[Down+B]` and `[Y]` every 4 frames → produces the 8-frame shine period.

## Shine OOS (Out Of Shield)

Shield → shine. Shine can come out of shieldstun via jump-cancel; the fastest OOS option.

| Step | Frame (from shield) | Input |
|---|---|---|
| In shield | — | `L`/`R` held |
| Jump OOS | first actionable frame after shieldstun | `Y` (jumpsquat starts) |
| Shine | frame 4 after jump | `Down` + `B` |

- Because shine is jump-cancellable, you jump out of shield (jump is instant OOS in Melee, no shield-drop delay) then JC the jumpsquat into shine on frame 4. Effective shine-OOS startup ≈ **4 frames after the jump input** (plus any remaining shieldstun).
- Drop-shield (releasing shield without jumping) takes longer; jump-OOS is the standard path to shine.

## Drillshine / shine-grab timing

- **Drillshine** = land drill (dair) → shine. Dair must auto-cancel / land such that shine connects frame 1 on landing; then JC-shine loop as above. Standard follow-up after the shine: JC into **grab** or **another shine**.
- **JC grab off shine:** shine → jump (frame 4) → `Z` (grab) during jumpsquat. Same jump-cancel mechanic as shine; grab registers during the 3-frame jumpsquat → instant standing grab.
- **JC up-smash off shine:** shine → jump (frame 4) → `C-stick up` during jumpsquat → upsmash with no jumpsquat delay.
- All JC follow-ups share the rule: input the action **within the 3-frame jumpsquat** after the frame-4 jump.

---

# DEFENSIVE / TECH

## Teching (general mechanics)

| Property | Value | Notes |
|---|---|---|
| Tech window | **20 frames** | Opened by a digital L/R press. |
| Tech lockout | **40 frames** | Triggered if you press L/R again within 40 frames of a prior press (mashing locks you out). |
| Window if pressed mid-hitlag | **1 frame** only | Press on any but the **last** hitlag frame → only 1-frame window. |
| Window if pressed on last hitlag frame | **20 frames** | Optimal: press L/R on the final hitlag frame → full 20f window. |
| End-of-tech vulnerability | **6 frames** (most chars; Fox = 6) | Vulnerable at end of tech animation before actionable (Pikachu/Pichu = 2). |

**Input:** press **`L` or `R`** (digital/click, any press depth that registers digital) at/near the moment of ground contact.
**Macro strategy:** detect impending ground contact and press L/R timed to the **last hitlag frame** to get the 20-frame window; do **not** double-tap (40f lockout).

### Tech in place
- Input: **`L`/`R`** with **no directional input** (analog neutral).
- Character pops up and lands in place with intangibility during the animation; vulnerable 6f at the end.

### Tech roll (left / right)
| Property | Value |
|---|---|
| Input | `L`/`R` **+ analog left or right** (full, ±1.0 x) |
| Behavior | bounce into a sideways roll, **intangible during the roll movement**, vulnerable 6f at end |

- Direction = the way the stick is held when the tech registers.
- libmelee: `tilt_analog(MAIN, 0.0, 0.5)` (full left) or `(1.0, 0.5)` (full right) + `press_button(BUTTON_L)`.

### Amsah tech (DI'd / survival tech)
- Purpose: survive low-angle, low-knockback hits (e.g. Falco dsmash) by combining survival DI + ASDI-down + a tech.
- **Inputs (combined):** DI **down + away** (analog), **C-stick down** (ASDI down), press **`L`/`R`** *before hitlag ends*.
- Result: trajectory pulled toward the ground → character techs the ground at percents that would otherwise launch them. "Away" survives longer than "toward."
- Contested: timing is matchup-dependent; the defining inputs (DI down/away + C-down + shield) are consistent across sources.

### ASDI-down tech (standing tech vs weak knockdowns)
- **Inputs:** control stick **down** (or neutral), **C-stick down** (ASDI), press **`L`/`R`** before hitlag ends → standing tech. Useful vs e.g. Fox upsmash at low %.

## Shield drop / powershield

| Property | Value | Notes |
|---|---|---|
| Powershield window (physical attacks) | **4 frames** | First frames of shield activation; press L/R so shield turns on exactly as the attack connects. |
| Powershield vs projectiles | first **2 frames** of shield | Reflects projectile (deals ½ damage; keeps thrower's ownership on Poké Balls). |
| Light shield | analog L/R partial press | Wider, slower-shrinking shield; more shieldstun/pushback to user. Press depth = shield density. |
| Shield drop | release `L`/`R` | Shield-release lag before actionable (jump-OOS bypasses this — see Shine OOS). |

**Input (powershield):** tap **`L`/`R`** so the shield’s **first 1–4 frames** overlap the incoming hit. Macro must align shield-on frame with predicted hit frame.
**Light shield analog note:** intermediate trigger values (between digital threshold and full) set shield density; libmelee `press_shoulder(BUTTON_L, x)` with 0<x<1.

## Spotdodge

| Property | Frame(s) |
|---|---|
| Startup | 1 |
| Intangible | frames **2–15** (~14 active) |
| Recovery | 11 |
| Total | **26 frames** |

**Input:** analog **down** (full, y ≈ −1.0) **+ `L`/`R`** (shield), from standing/shield.

## Roll (forward / backward)

| Property | Forward | Backward |
|---|---|---|
| Startup | 3 | 3 |
| Intangible | frames 4–19 (~16 active) | 4–19 (~16) |
| Recovery | 11 | 11 |
| Total | **30 frames** | **30 frames** |

**Input:** `L`/`R` **+ analog forward** (toward facing dir) or **backward** (away). Held shield + stick direction.

---

# RECOVERY

## Firefox / Firebird (Up-B)

The 8-/multi-direction angled recovery. Charge, then launch in the stick-aimed direction.

| Phase | Frame(s) | Notes |
|---|---|---|
| Charge start | frame 1 | Fox engulfed in flames, stationary. |
| Charge looping hits | frames **20, 22, 24, 26, 28, 30, 32** | 2% each (7 hits). |
| **Aim/angle locked** | **frame 42** | Trajectory = the **control-stick direction held on frame 42**. |
| Launch / travel + strong hit | **frame 43** | Strong hit active **frames 43–72** (14% NTSC / 12% PAL). |
| Total | **92 frames** | |
| Earliest ledge grab (pre-move) | frame 16 | Can sweetspot ledge before traveling as early as frame 16. |
| Landing lag (onto ground) | 6 frames pre-freefall / 3 post | |

**Input sequence:**
1. `Up` + `B` (analog up + B) → starts 42-frame charge.
2. **Hold/set the control stick to the desired travel angle so it is correct on frame 42.** The stick position read on frame 42 determines the launch direction.
3. Fox launches frame 43 in that direction; travels ~ until frame 72.

**Angling notes:**
- Direction is taken from the **analog stick angle at frame 42** (you can rotate the stick during the charge; only the frame-42 read matters). Hold the angle from ~frame 38+ to be safe.
- Fox/Falco up-B supports a very large set of travel angles (commonly cited **~352 distinct angles**, far more than the "8 directions" simplification). For a macro, pick the exact `(x, y)` analog coordinate for the desired degree.
- Cannot re-angle after launch (frame 43); the path is fixed at frame 42.
- **Coordinate examples:** straight up = (0, +1.0); up-toward-stage 45° = (±0.70, +0.70); shallow toward stage = (±0.90, +0.40).

## Shorten Up-B

- Fox's up-B distance can be shortened, but the practical "shorten" is choosing the **frame-42 angle** + grabbing ledge early (frame 16+) or aiming to land sooner. There is **no separate B-press shorten** for Firefox like there is for Illusion. To minimize distance: aim more vertically/short or sweetspot the ledge ASAP (frame ≥16 before travel; or aim so the strong-hit travel ends near the ledge).
- Contested: "shorten up-B" in community usage usually refers to **Illusion** (below), not Firefox. For Firefox the levers are angle + early ledge grab.

## Fox Illusion (Side-B)

Horizontal dash recovery; **shortenable** by a second B press.

| Property | Frame(s) | Notes |
|---|---|---|
| Hitbox active | frames **22–25** | |
| Forward travel | **5 frames** | The 5 frames Fox moves forward = 5 shorten lengths. |
| Total (full) | **63 frames** | |
| Edge-cancel ledge grab | as early as **frame 29** | Grabbing ledge cancels end lag. |
| Landing lag | 20 pre-freefall / 3 post | High end lag if it whiffs onstage. |

**Input:** `Forward` (analog full side) **+ `B`**.
**Shorten input:** press **`B` again during the 5-frame forward-travel phase**.
- There are **5 shortened lengths**, one per travel frame — pressing B on travel-frame 1 = shortest, travel-frame 5 = nearly full.
- Macro: to get distance `n` (1–5), inject the second `B` on the `n`-th forward-travel frame.
- Edge-cancel: if landing on a platform/stage edge, the move can be edge-cancelled to remove end lag (ledge grab ≥ frame 29).

## Ledgedash (waveland from ledge)

Drop from ledge → jump → airdodge onto stage, carrying ledge intangibility ("GALINT").

| Property | Value | Notes |
|---|---|---|
| Cliffcatch animation | **7 frames** (Link 3) | On grabbing ledge. |
| Total ledge intangibility | **37 frames** (7 + 30) | Link = 33. Carries onto stage if you act fast. |
| Earliest ledge release for ledgedash | **frame 9** | Releasing before frame 9 = no-action drop (vulnerable normal getup). |
| **Fox GALINT (perfect ledgedash)** | **15 frames** | Tied for best in game (with Pichu). Frames of intangibility remaining after landing onstage, actionable. |
| Optimal airdodge angle | **down + toward stage ~45°** | Gives Fox his max 15f GALINT. |

**Input sequence:**
1. Hang on ledge (cliffcatch + intangible).
2. **Release ledge on frame 9** (earliest): tap **analog away from stage** (or C-stick) to drop.
3. **Jump immediately** (`Y`) — fast-fall not needed; minimal rise.
4. **Airdodge `L`/`R` + analog down-toward-stage (~45°, e.g. (toward·0.70, −0.70))** to waveland onto the stage.

**Timing / pitfalls:**
- Airdodge **too early** → fall off-stage (don't reach ground). **Too late** → airdodge with landing lag (no waveland, lose invuln).
- Goal: waveland onto the stage **before** the 37-frame intangibility expires so the remainder (up to 15f for Fox) covers your first onstage action (aerial, grab, upsmash, shine).
- **Fox-specific ECB caveat:** the animation *before* grabbing ledge changes Fox's environmental collision box. Some pre-grab states (e.g. certain aerials) leave the ECB small; others enlarge it, requiring Fox to **jump higher before airdodging** to avoid SD'ing off the bottom. A robust macro must account for ECB state → adjust jump-to-airdodge delay. This is the #1 source of ledgedash inconsistency for Fox.
- libmelee: release: `tilt_analog(MAIN, away, 0.5)`; jump `press_button(BUTTON_Y)`; next frame `tilt_analog(MAIN, toward·0.7, 0.15)` + `press_button(BUTTON_L)`.

## Ledge options / ledge intangibility frames

| Option | Availability | Intangibility |
|---|---|---|
| Total ledge intangibility | first **37 frames** of hang (7 cliffcatch + 30) | full intangible. |
| Ledge jump | immediately after cliffcatch (frame ≥8) | carries remaining intangibility. |
| Ledge roll | immediately after cliffcatch | intangible during roll. |
| Ledge attack | immediately after cliffcatch | intangible portion early. |
| Ledge getup (stand) | immediately after cliffcatch | intangible portion. |
| **Fox/Falco invincible ledgestall (up-B)** | drop then up-B within a **14-frame window** | refreshes full intangibility. |
| Ledgedash | release frame 9 → jump → airdodge | up to **15f GALINT** onstage (Fox). |

- **Invincible ledgestall:** drop off ledge and input **Up-B within 14 frames** of dropping → regrab ledge with refreshed 37f intangibility. Repeatable stall.
- After the 37-frame intangibility expires while hanging, Fox becomes vulnerable on the ledge (re-grab or act before then).

---

# Source notes & confidence

| Datum | Confidence | Notes / sources |
|---|---|---|
| Shine JC frames 4–21, total 39, hitbox f1, invuln f1 | **High** | SmashWiki Fox/Down special; FightCore; Smashboards "Shine Frame Data". |
| Jumpsquat 3f, shine on frame-4-after-jump | **High** | Hit Box Arcade; SmashWiki Jump-canceling. |
| Multishine 7f first / 8f subsequent cycle | **Medium-High** | Smashboards/community consensus; the per-cycle 8f = 3 jumpsquat + frame-4 shine + offset. Treat 8f as the steady period. |
| Tech window 20f, lockout 40f, mid-hitlag 1f window, end vuln 6f | **High** | SmashWiki Tech; Smashboards throws/techs/getups data. |
| Powershield 4f (physical) / 2f (projectile) | **High** | SmashWiki Perfect shield. |
| Spotdodge 2–15 / total 26; Roll 4–19 / total 30; Airdodge 4–29 / total 49 | **High** | Liquipedia Fox/Frame_Data. (Active-frame edges ±1 across sources.) |
| Firefox: charge to f42, aim locked f42, launch f43, hits 43–72, total 92, ledge-grab f16 | **High** | SmashWiki Fox/Up special + Fire Fox; FightCore; smash20xx. "aim at frame 42" is the load-bearing number. |
| Firefox ~352 travel angles | **Medium** | Community (Smashboards "Angles in Melee"); the "8-direction" model is a simplification. |
| Illusion: hit 22–25, 5 travel frames / 5 shortens, total 63, edge-cancel f29 | **High** | SmashWiki Fox/Side special. |
| Ledgedash: cliffcatch 7f, 37f intangibility, release f9, Fox GALINT 15f, ~45° airdodge | **High** | SmashWiki Ledgedash; Alex's Puff Stuff (Fox ledgedash). ECB-dependence is well documented but per-animation values vary. |
| Invincible ledgestall up-B within 14f | **High** | SmashWiki Ledgestall/Intangibility. |
| Amsah/ASDI-down tech inputs (DI down/away + C-down + shield pre-hitlag) | **High** (inputs) / **Medium** (timing) | SmashWiki Tech / SDI / Crouch cancel; matchup-dependent timing. |

## Macro-implementation cheat ratios (60 fps)

- **Multishine loop:** alternate `Down+B` and `Y` every **4 frames** → 8-frame shine period.
- **Waveshine:** `Down+B` → +4f `Y` → +1f `L`+down-forward analog.
- **JC anything off shine:** `Down+B` → +4f `Y` → within next 3f inject the follow-up (`Z` grab / `C-up` usmash / `Down+B` shine).
- **Firefox angle:** set analog to target `(x,y)` no later than frame **38**, hold through frame **42**, expect launch frame **43**.
- **Illusion shorten n (1–5):** `Forward+B` → second `B` on travel-frame `n`.
- **Ledgedash:** release ledge frame **9** → `Y` → airdodge down-toward ~45° (delay jump→airdodge tuned per ECB state).
- **Tech:** single `L`/`R` press on the **last hitlag frame**; never double-tap (40f lockout).
