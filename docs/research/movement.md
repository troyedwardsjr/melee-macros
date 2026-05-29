# Fox Movement Tech — Frame Data & Input Reference

Target: Slippi/Dolphin SSBM, NTSC 1.02, 60 fps. Character: **Fox**.
Purpose: input-injection macros. Frame timing accuracy is the priority.

> **Frame convention used here:** Frame 1 = the first frame an input is registered.
> "Jumpsquat is 3 frames" means the character is in jumpsquat on frames 1, 2, 3
> and becomes airborne on frame 4. When a step says "on frame 4 input X," it means
> the 4th frame of the sequence (first airborne frame).

---

## 0. Analog Stick Coordinate System (CRITICAL for injection)

Two coordinate conventions appear in the wild. Pick one and stay consistent.

| Convention | Left/Down | Neutral | Right/Up | Notes |
|---|---|---|---|---|
| **libmelee `tilt_analog()`** | 0.0 | **0.5** | 1.0 | Default in libmelee. `[0.5, 0.5]` = neutral. |
| **libmelee `tilt_analog_unit()`** | -1.0 | 0.0 | +1.0 | "Unit" / compat helper. Maps to the [-1,1] math convention. |
| **Raw game / melee math** | -1.0 | 0.0 | +1.0 | Internally scaled to ±80 (axis) / ±56 (diagonal) raw bytes; magnitude is what physics reads. |

**Deadzone:** magnitude (per axis) below **|0.2750|–|0.2875|** reads as neutral. Anything
`< 0.2875` should be treated as no input. (Sources vary: 0.2750 used as the physics
deadzone, 0.2875 cited as the edge of accessible coordinates in controller rulesets.)

**Magnitude saturation:** above the deadzone, for *direction-based* actions the game cares
about **angle**, not magnitude — a tilt just outside the deadzone gives the same direction
result as touching the octagon gate. But for *physics that scale with magnitude*
(wavedash distance, dash threshold, crouch), magnitude matters. See per-technique notes.

**Key reference coordinates** (math/unit convention, ±1.0 = gate):

| Direction | X | Y | Raw (≈) | Use |
|---|---|---|---|---|
| Full cardinal | ±1.0 | 0 / ±1.0 | ±80 | dash, full stick |
| True 45° diagonal | ±0.7071 | ±0.7071 | ±56 each | standard diagonal |
| **Wavedash (shallow)** | ±0.8500 | −0.5000 | — | down-forward airdodge, good distance |
| **Wavedash (alt)** | ±0.5000 | −0.8500 | — | steeper, shorter slide |
| Shield drop (notch) | ±0.5446 | −0.6250 | — | not movement, listed for completeness |

> In libmelee `tilt_analog()` (0–1) convention, to get math `(+0.85, −0.50)` you write
> `tilt_analog(Button.BUTTON_MAIN, 0.5 + 0.85/2, 0.5 + (-0.50)/2)` = `(0.925, 0.25)`.
> Or just use `tilt_analog_unit(Button.BUTTON_MAIN, 0.85, -0.50)`.

---

## 1. Fox Core Frame Data (NTSC)

| Stat | Value | Source |
|---|---|---|
| **Jumpsquat** | **3 frames** (airborne on frame 4) | SmashWiki Fox (SSBM) |
| Short-hop input window | **2 frames** (release jump before frame 3 of jumpsquat) | window = jumpsquat − 1 |
| **Initial dash animation** | **11 frames** | SmashWiki Dash |
| Dash-dance window | **= 11 frames** (matches initial dash) | SmashWiki Dash-dance |
| Foxtrot re-dash | re-input dash before run anim begins (within the 11f dash) | see §6 |
| Walk speed | 1.6 | SmashWiki Fox |
| Initial dash speed | 1.9 | SmashWiki Fox |
| Run speed | 2.2 (2nd fastest in game) | SmashWiki Fox |
| Traction | 0.08 | SmashWiki Fox |
| Air speed | 0.83 | SmashWiki Fox |
| Air accel | 0.02 base / 0.06 additional | SmashWiki Fox |
| Gravity | 0.23 | SmashWiki Fox |
| Fall speed | 2.8 base / **3.4 fast-fall** | SmashWiki Fox |
| Full-hop height | 31.28 units | SmashWiki Fox |
| Short-hop height | 10.65 units | SmashWiki Fox |
| Weight | 75 (NTSC) / 73 (PAL) | SmashWiki Fox |

---

## 2. Short Hop & Full Hop

**Jump buttons:** X, Y (tap jump = Up on control stick, less precise — avoid for macros).

### Full Hop
| Step | Input | Frame |
|---|---|---|
| 1 | Press & **hold** X or Y through frame 3 | frame 1 (held ≥3 frames) |
| — | Airborne | frame 4 |

- Holding the jump button past the jumpsquat → full hop.

### Short Hop (Fox = tight)
| Step | Input | Frame |
|---|---|---|
| 1 | Press X or Y | frame 1 |
| 2 | **Release** jump button | must release on frame 1 or 2 |
| — | Airborne (short) | frame 4 |

- Fox jumpsquat = 3, so short-hop window = **2 frames** (release before the 3rd jumpsquat frame).
- Macro: press jump for **1 frame**, release. Guarantees short hop.

---

## 3. Wavedash

Air-dodge diagonally into the ground during/after jumpsquat; the airdodge's
velocity is applied to ground position → slide.

### Inputs (sequence)
| Step | Input | Frame | Coord (math conv.) |
|---|---|---|---|
| 1 | Tilt control stick down-forward (shallow) | held from frame 1 | `(+0.85, −0.50)` for max distance |
| 2 | Press X/Y (jump) | frame 1 | — |
| 3 | Press **L or R** (airdodge) | **frame 4** (1st airborne frame) | with stick still down-forward |

- Fox **airdodges on frame 4** (first frame after the 3-frame jumpsquat).
- The diagonal must already be held when L/R is pressed. Common macro order:
  set stick → jump → (wait 3 frames) → airdodge on frame 4 while holding the diagonal.

### Angle / distance
- **Optimal angle ≈ 17.1° above horizontal** (i.e. very shallow, near-horizontal).
  Equivalent: ~73.5° measured from straight-down. The shallower (more horizontal) the
  stick, the longer the slide; steeper = shorter.
- Max-distance coordinate cited: **X = ±0.85, Y = −0.50**. Steeper alt: **X = ±0.50, Y = −0.85** (shorter).

### Timing / lag
- **Frame-perfect wavedash never visibly leaves the ground** — the airdodge changes
  velocity and that velocity is applied to position on the *same* frame (frame 4).
- **Landing lag after wavedash = jumpsquat + 10 = 3 + 10 = 13 frames** of total
  commitment from the jump input; specifically there are **10 frames** post-slide
  during which Fox cannot act (the airdodge "landing"). Any ground action (tilt,
  grab, shine, jump) becomes available after those 10 frames.
- **Delaying the airdodge past frame 4 shortens the wavedash** (more airtime = stick
  pulls velocity more downward by the time you touch ground).

### Direction
- Forward wavedash: down-**forward** diagonal. Backward wavedash: down-**back** diagonal
  (mirror X sign). The character does NOT need to be facing the slide direction.

---

## 4. Wavedance (wavedash → dash-dance variants)

"Wavedance" = chaining a wavedash into a dash/dash-dance, repeatedly, to cover ground
while staying actionable. Closely related to **wavesurfing** (dash → wavedash → dash …,
popularized by PPMD), which slides during jumpsquat to extend distance.

### Pattern (one cycle)
| Step | Input | Frame (relative) |
|---|---|---|
| 1 | Wavedash forward (§3) | 0 |
| 2 | Wait out the 10f wavedash landing lag | +10 |
| 3 | Smash control stick the chosen direction → enters initial dash | +11 |
| 4 | (optional) reverse for dash-dance, or wavedash again | within 11f dash window |

- The value is: wavedash repositions + you can immediately dash/dash-dance/turn,
  blending wavedash distance with dash-dance bait.
- **Wavesurf cycle:** dash (build momentum) → jump → airdodge into ground on frame 4
  (slide carries dash momentum) → dash again. Repeat. Extends total ground covered
  per wavedash vs. standing wavedash.
- No new unique frame numbers beyond §3 (wavedash) + §5 (dash-dance) combined.

---

## 5. Dash Dance

Rapidly reverse the control stick direction within the **initial dash window** so the
character repeatedly enters initial-dash, never committing to the run animation.

### Inputs
| Step | Input | Frame |
|---|---|---|
| 1 | Smash control stick fully left (`X = −1.0`) | frame 1 → initial dash starts |
| 2 | Smash control stick fully right (`X = +1.0`) | **before frame 12** (within 11f dash) |
| 3 | Smash left again | within next 11f dash |
| … | repeat | — |

- **Fox dash-dance window = 11 frames** (= initial dash length). You must reverse
  *before* the initial dash animation ends (≤ frame 11) or Fox enters run and the
  reverse becomes a turnaround (laggy, no actions).
- Tighter, faster reversals = a "smaller" dash dance that stays maximally actionable.
  Reversing near frame 11 = a wide dash dance covering more ground.
- Stick must cross neutral and reach a **smash/dash magnitude** (full cardinal, |X|≈1.0)
  to register a new dash rather than a walk. Tilting only (sub-dash magnitude) → walk.

---

## 6. Foxtrot

Repeatedly re-trigger the **initial dash** without entering run — moves at initial-dash
speed (which for many chars, including the general technique's namesake, can chain).

### Inputs (per foxtrot step)
| Step | Input | Frame |
|---|---|---|
| 1 | Smash control stick forward (`X = +1.0`) → initial dash | frame 1 |
| 2 | Return stick to **neutral** (let dash play, do NOT hold into run) | — |
| 3 | Smash forward **again** before run anim locks in | re-dash within the 11f dash, classically near the end of the dash |
| … | repeat | — |

- General rule: re-dash must occur **before the character enters the run animation**.
  The widely-cited "frame 16" re-dash figure is **Smash 4/Ultimate**, NOT Melee — in
  Melee the window is the initial-dash length (Fox = 11 frames). Re-input the dash
  late in that window for a clean foxtrot.
- **Melee-specific alternate foxtrots:** (a) jump-cancel a dash into a wavedash, then
  dash again; (b) dash-cancel a full dash into another dash.
- Difference vs. dash-dance: foxtrot keeps **same** direction each re-dash; dash-dance
  alternates direction.

---

## 7. Extended Dash Dance

Use a foxtrot/dash-cancel to lengthen one "leg" of a dash dance before reversing,
covering more ground than a plain dash-dance while staying out of the run animation.

- In Melee this is achieved by **dash-canceling a full dash into another dash** (same
  direction) to extend, then reversing — effectively foxtrot-into-dash-dance.
- No distinct Melee frame constant beyond the 11f initial-dash window; "extended" just
  means re-dashing forward (foxtrot) one or more times before the reversal.
- NOTE: the formal "extended dash dance" with a dedicated frame-16 interrupt window is a
  **Brawl/Smash 4** mechanic. In Melee the equivalent is built from foxtrot + dash-cancel.
  Sources blur the two — flag for the engine.

---

## 8. Perfect Pivot / Pivot

A pivot = catch the **single standing-upright frame** that occurs when the control stick
crosses neutral while changing direction during the dash-dance window.

### Inputs (empty pivot / pivot)
| Step | Input | Frame |
|---|---|---|
| 1 | Dash one direction (smash stick) | frame 1 |
| 2 | **Smash stick the opposite direction for exactly 1 frame** | within dash-dance window |
| 3 | Let stick **reset to neutral the next frame** | +1 |

- **Pivot window in Melee = 1 frame** (vs. 5 frames in Smash 64). Extremely strict.
- There is exactly **one frame during each direction-change of a dash dance where Fox is
  standing upright (turnaround frame)**. Inputting an attack/grab on *that* frame halts
  the dash and performs the action out of the turnaround (this is the "perfect pivot"
  use — e.g. pivot grab, pivot ftilt).
- If you flick back but hold too long / don't reset, you get a moonwalk or a full
  turnaround dash instead. (See §10 moonwalk — the failure mode overlaps.)
- **"Perfect pivot" sliding variant** (keeping dash momentum) is primarily a Smash 4
  term; in Melee the analogous tech is the 1-frame turnaround pivot above.

---

## 9. Empty Pivot

An **empty pivot** = a pivot from §8 that is **not** canceled into any action — you simply
catch the turnaround/upright frame to face the other way (or micro-reposition) with no
follow-up attack.

| Step | Input | Frame |
|---|---|---|
| 1 | Dash forward | frame 1 |
| 2 | Flick stick fully backward for **1 frame** | within dash window |
| 3 | Release to neutral | +1 |
| — | Result: Fox stands, now facing reversed direction, no commitment | — |

- Same 1-frame leeway as §8. Only difference from perfect pivot: no buffered attack/grab.
- Failure mode: 1-frame miss → moonwalk (if held back slightly long) or initial dash the
  other way (dash-dance) rather than a clean stationary pivot.

---

## 10. Moonwalk

Slide backward while keeping forward-ish facing/momentum by ramping the stick from a
back-diagonal to straight-back during the dash.

### Inputs
| Step | Input | Frame |
|---|---|---|
| 1 | Begin a forward dash | frame 1 |
| 2 | Move stick to the **lower-back diagonal** (down-back notch) | held |
| 3 | **Hold that diagonal ≥ 2 frames** | frames held ≥2 |
| 4 | Tilt stick **straight back** (horizontal back) | next frame |

- Requirement: the stick must be **lightly tilted back for at least 2 frames** before
  going fully horizontal-back. The down-back octagon notch is the convenient way to hit
  this. It does not matter if the stick passes through neutral or points down on the way.
- "Perfect moonwalk" (TAS-tier, rarely used): smash fully back within the first 3 frames
  of the dash, or tilt back on frame 3 then fully back next frame.
- Relationship to pivots: moonwalk is the natural *failure mode* of an empty pivot held
  one frame too long. The engine should treat the 2+ frame down-back hold as the
  distinguishing feature.

---

## 11. JC (Jump-Cancel) Grab

Interrupt a dash/run with a jump, then cancel the **jumpsquat** with grab → get the
fast standing grab while keeping dash momentum. (Standing grab is far faster/safer than
Fox's laggy dash grab.)

### Inputs
| Step | Input | Frame |
|---|---|---|
| 1 | Dash or run | — |
| 2 | Press X/Y (jump) | frame 1 of jumpsquat |
| 3 | Press **Z (grab)** (or A+Shield) during jumpsquat | **frame 1, 2, or 3** (within the 3f jumpsquat) |
| — | Standing grab executes, momentum retained | — |

- Window for Fox = the **3 jumpsquat frames**. Press grab on any of frames 1–3 of
  jumpsquat (do NOT let it reach frame 4 / airborne, or you'll jump and air-grab/nothing).
- Practical macro: press jump and grab on (nearly) the same frame, or grab 1 frame after
  jump. Both land inside the 3-frame jumpsquat.
- Z is the cleanest grab input for the macro. (A + L/R also grabs but couples with shield.)

---

## 12. Boost Grab

Dash attack → cancel into dash grab on its first cancelable frames → grab with extended
dash-attack momentum & range. Fox is one of the 4 chars (Sheik, Fox, Falco, Marth) that
gain significant range from it.

### Inputs
| Step | Input | Frame |
|---|---|---|
| 1 | Dash | — |
| 2 | Press A (dash attack) | frame 1 of dash attack |
| 3 | Press **Z (grab)** | **frames 2–4** of the dash attack (3-frame window) |
| — | Dash attack cancels into dash grab, boosted forward | — |

- **3-frame cancel window**; the **first frame of the dash attack is NOT cancelable**, so
  the effective window is frames 2, 3, 4.
- Result is still a **dash grab** (laggier than standing JC grab) but with extra forward
  reach — use boost grab for range, JC grab for speed/safety.
- Audio cue: Fox's dash attack has a sound effect, useful for human timing (irrelevant
  for frame-injection but noted).

---

## 13. Crouch Cancel (movement-relevant basics)

Not locomotion, but governs grounded defensive movement & must be modeled.

### Inputs
| Step | Input | Frame |
|---|---|---|
| 1 | Hold control stick **down** (full, into crouch) | continuous |
| — | When hit while crouching, knockback & hitlag ×**0.67** | on hit |

- **Crouch:** hold stick down past crouch magnitude (cardinal down). Fox enters
  crouch (squat) — full down required.
- **0.67× knockback & hitlag multiplier** while crouching when hit.
- **ASDI down** is the real engine: holding down moves Fox slightly down on the first
  frame after hitlag; if that downward ASDI movement exceeds the vertical knockback,
  Fox collides with the ground on frame 1 of hitstun instead of launching.
- **Landing during crouch-cancel hitstun → universal 4-frame landing recovery** takes
  priority over remaining hitstun (lets you act fast and reposition/wavedash out).
- Frame-advantage formulas:
  - Grounded move CC'd: `RoundUp(hitlag × 1/3) + (attack lag − 4)`
  - Aerial CC'd: `RoundUp(hitlag × 1/3) + (fall frames after hitlag) + (aerial landing lag − 4)`
- Fox example: Fox nair at 0% normally launches up; CC'd, reduced knockback drops it to
  the ~0° (low) trajectory — relevant for spacing/punish reads.

---

## 14. Macro Implementation Cheat-Sheet (Fox)

| Tech | Min input sequence (math coords) | Critical frame |
|---|---|---|
| Short hop | jump 1f, release | release ≤ frame 2 |
| Full hop | jump, hold ≥3f | — |
| Wavedash F | stick (+0.85,−0.50); jump; L/R on frame 4 | airdodge = **frame 4** |
| Wavedash B | stick (−0.85,−0.50); jump; L/R on frame 4 | frame 4 |
| Dash dance | X=−1 ↔ X=+1, reverse ≤ frame 11 each leg | ≤ frame 11 |
| Foxtrot | X=+1, neutral, X=+1 again before run | within 11f dash |
| Pivot grab | dash; flick opposite 1f; Z on the upright turnaround frame | 1-frame window |
| Empty pivot | dash; flick opposite 1f; neutral next frame | 1-frame window |
| Moonwalk | dash; down-back notch ≥2f; then straight back | ≥2f diagonal hold |
| JC grab | dash; jump; Z within jumpsquat | frames 1–3 |
| Boost grab | dash; A; Z frames 2–4 of dash attack | frames 2–4 |
| Crouch cancel | hold stick full down; (ASDI down on hit) | continuous |

---

## Conflicts / Uncertainties Flagged for the Engine

1. **Deadzone value:** physics deadzone cited as **0.2750**; controller-ruleset edge as
   **0.2875**. Use 0.2875 as a safe "treat as neutral below this" threshold; physics may
   read 0.2750. Verify against your injection target in-game.
2. **Wavedash optimal coordinate:** the **17.1° / ~73.5°-from-down** angle is consistent
   across sources; the exact stick coordinate for *Fox specifically* (vs. generic) is not
   character-tuned in sources — `(+0.85, −0.50)` is the widely-used max-distance value but
   confirm Fox's traction (0.08) doesn't change the optimum vs. heavier-traction chars.
3. **Foxtrot "frame 16":** appears in many results but is the **Smash 4/Ultimate** number.
   In **Melee** use the initial-dash length (Fox = **11 frames**). Do NOT hardcode 16.
4. **Extended dash dance / "frame 16 interrupt":** a **Brawl+** mechanic. Melee's
   equivalent is foxtrot + dash-cancel; no dedicated Melee frame constant exists.
5. **Perfect pivot (sliding-momentum) terminology** is Smash 4; Melee's pivot is the
   1-frame turnaround. Sources conflate them.
6. **Fox initial dash = 11 frames** comes from SmashWiki's Dash ranking table. Some
   community frame data lists vary by ±1; if your macro misses the dash-dance reversal,
   test reversing at frame 10 and 11.
7. **Wavedash landing lag = 10 frames** (post-slide) is consistent; total commitment from
   the jump press = jumpsquat(3) + 10 = 13 frames.

---

## Sources

- [SmashWiki — Fox (SSBM)](https://www.ssbwiki.com/Fox_(SSBM)) — jumpsquat 3, speeds, weights, hop heights
- [SmashWiki — Dash](https://www.ssbwiki.com/Dash) — Fox initial dash = 11 frames, range 7–15
- [SmashWiki — Dash-dance](https://www.ssbwiki.com/Dash-dance) — DD window = initial dash length
- [SmashWiki — Fox-trotting](https://www.ssbwiki.com/Fox-trotting) — re-dash before run; Melee alt methods
- [SmashWiki — Pivoting](https://www.ssbwiki.com/Pivoting) — 1-frame pivot window in Melee, empty pivot
- [SmashWiki — Moonwalk](https://www.ssbwiki.com/Moonwalk) — 2+ frame down-back hold then straight back
- [SmashWiki — Short hop](https://www.ssbwiki.com/Short_hop) — SH window = jumpsquat − 1
- [SmashWiki — Wavedash](https://www.ssbwiki.com/Wavedash) — 10f landing lag, 17.1° angle, never leaves ground
- [SmashWiki — Jump-canceled grab](https://www.ssbwiki.com/Jump-canceled_grab) — cancel jumpsquat with grab
- [SmashWiki — Boost grab](https://www.ssbwiki.com/Boost_grab) — 3-frame cancel window, frame 1 not cancelable
- [SmashWiki — Crouch cancel](https://www.ssbwiki.com/Crouch_cancel) — 0.67×, ASDI down, 4f landing recovery
- [Liquipedia — Wavedash (gameplay)](https://liquipedia.net/smash/Wavedash_(gameplay)) — 73.5° = longest WD, 10f lag
- [MeleeConchRuleset (CarVac, GitHub)](https://github.com/CarVac/MeleeConchRuleset/blob/main/ruleset.md) — coordinate values, deadzone, wavedash coords (±0.85,−0.50)
- [libmelee — Controller docs](https://libmelee.readthedocs.io/en/latest/controller.html) — 0–1 stick convention (0.5 neutral), tilt_analog_unit
- [libmelee docs](https://libmelee.readthedocs.io/en/latest/index.html)
- [Dignitas — Movement Options in Melee Part 1](https://dignitas.gg/articles/movement-options-in-melee-part-1-the-basics) — dash 7–18f, jumpsquat 3–8f general ranges
- [Hit Box Arcade — Fox Jumpsquats & Multishine](https://www.hitboxarcade.com/blogs/smash-box/ssbm-fox-squats-and-jump-cancels)
