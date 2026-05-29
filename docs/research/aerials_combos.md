# Fox — Aerials, L-Cancel & Combo Frame Data

**Game:** Super Smash Bros. Melee (NTSC 1.02), 60 fps. 1 frame ≈ 16.67 ms.
**Scope:** Fox McCloud only. All frame numbers are for input-injection. Frame 1 = first frame of the relevant state (jumpsquat, aerial animation, or landing animation) unless noted.

> **Convention used throughout:** "Airborne on frame 4" means after a 3-frame jumpsquat (frames 1–3 grounded), Fox leaves the ground on the 4th frame. Aerial frame counts (startup/active/total) are counted from the first frame of the aerial animation, which can be input as early as the airborne frame.

---

## 1. Fox Core Movement Constants

| Property | Value | Notes |
|---|---|---|
| Jumpsquat | **3 frames** | Grounded frames 1–3; airborne frame 4. "Magic" 4th frame is first airborne frame. |
| Short-hop input window | **2 frames** | Must release X/Y before frame 3 of jumpsquat (jump held ≤2 frames). One of the tightest in the game. |
| Short hop air time | **21 frames** | Total time airborne on a short hop (no fast fall). |
| Full hop air time | **35 frames** | Total time airborne on a full hop (no fast fall). |
| Earliest fast fall — short hop | **frame 12** | (Of the 21-frame SH airtime; i.e. the SH apex region.) FF air time then 15 frames. |
| Earliest fast fall — full hop | **frame 18** | FF air time then 27 frames. |
| Normal fall speed | **2.8** | |
| Fast fall speed | **3.4** | +21.4% vs normal. |

Sources: SmashWiki *Short hop* / *Jump* / *Fast-falling*; Hit Box Arcade Fox jumpsquats article; Smashboards SH-input thread. Air-time numbers (21 SH / 35 FH; FF earliest frame 12 SH / 18 FH) are widely cited and mutually consistent across SmashWiki + community frame tables.

---

## 2. L-Cancel

### Mechanic
- **Input:** Press **L**, **R**, or **Z** within **7 frames before landing** while in an aerial-attack animation (the trigger press counts on the landing frame and the 6 frames prior — a 7-frame window).
- **Effect:** Landing animation plays at **double speed → landing lag halved, rounded down**.
- **Analog/digital:** Any analog or digital L/R press works. A *digital* (full) L/R press also triggers a tech input simultaneously (relevant if injecting digital trigger).
- **Cannot L-cancel:** auto-cancelled aerials (no aerial landing lag to cancel) or special-move landing lag.

### Hitlag extension (important for the macro)
- If L/R/Z is pressed **during hitlag** (i.e. while the aerial connects with a target/shield), the L-cancel stays valid even if Fox lands **up to 6 frames after the hitlag ends**.
- Practical consequence: when the aerial will hit something, the effective input window is much larger than 7 frames. For a whiffed aerial, only the strict 7-frame-before-landing window applies.

### Macro timing recommendation
- Safest robust approach: press and **hold/repeat** the L/R trigger across the final ~7 frames before the predicted landing frame, OR re-press every few frames during descent. A single press exactly on `landFrame - k` (0 ≤ k ≤ 6) is sufficient.

Sources: SmashWiki *L-canceling*, *Lag*. The **7-frame** window and **halve-rounded-down** effect are uncontested. The hitlag-extension (+6 after hitlag) is documented on SmashWiki.

---

## 3. Fox Aerial Frame-Data Table

Counted from frame 1 of the aerial animation. Multi-hit moves show per-hit active windows. "AC window" = auto-cancel: aerial auto-cancels (full landing lag avoided, no L-cancel needed) if Fox lands on/before the first number OR on/after the second number.

| Aerial | Startup (1st active) | Active frames | Total frames | Auto-cancel window | Landing lag | **L-cancel landing lag** | Damage |
|---|---|---|---|---|---|---|---|
| **Nair** | 4 | 4–27 (single long hitbox, ~28 active) | 39 | ≤3 / ≥37 | 10 | **7** | 12 |
| **Fair** | 6 | 6–8, 16–18, 24–26, 33–35, 43–45 (5-hit) | 59 | ≤5 / ≥49 | 22 | **11** | 17 (total) |
| **Bair** | 4 | 4–19 (16 active) | ~33 | ≤3 / ≥24 | 20 | **10** | 9–15 |
| **Uair** | 8 | 8–11 (multi-hit "2(1)4") | ~32 | ≤7 / ≥26 | 18 | **9** | 17 |
| **Dair** | 5 | 5–6, 8–9, 11–12, 14–15, 17–18, 20–21, 23–24 (7 hits) | 49 | ≤4 / ≥33 | 18 | **9** | 2 or 3 per hit (~19 total) |

Notes:
- **Startup** values: Nair/Bair active frame 4, Fair frame 6, Dair frame 5, Uair frame 8. (Liquipedia + FightCore.)
- **Active-frame counts** in Liquipedia's compact notation: Nair `28`, Bair `16`, Fair `3(7)3(5)3(6)3(7)3`, Uair `2(1)4`, Dair `2(1)2(1)2(1)2(1)2`. FightCore's explicit dair windows (5-6,8-9,11-12,14-15,17-18,20-21,23-24) are the most precise and used above.
- **L-cancel landing lag** = floor(landing lag / 2): Nair 10→7? (10/2=5 — see contested note), Fair 22→11, Bair 20→10, Uair 18→9, Dair 18→9.

> **CONTESTED — Nair landing lag/L-cancel:** Liquipedia lists Nair landing lag **10** and L-cancelled **7**. A pure halve-rounded-down of 10 would be 5, so the listed "7" suggests either a different base value or source rounding. Treat Nair L-cancel landing lag as **~5–7 frames**; verify in-engine before locking the macro. All other aerials are exact floor(lag/2).

> **CONTESTED — Bair total:** Liquipedia gives active "16" (frames 4–19) but does not list a clean total; ~33 is inferred. Verify if precise total needed.

Sources: Liquipedia *Fox/Frame Data*; FightCore Fox Dair page; meleeframedata.com / Smashboards "COMPLETE: Fox Hitboxes and Frame Data".

---

## 4. Dair (Drill) — Detail (for drillshine)

| Property | Value |
|---|---|
| Startup (1st hit) | frame 5 |
| Hit frames | 5–6, 8–9, 11–12, 14–15, 17–18, 20–21, 23–24 (7 hits, 1-frame gaps) |
| Total animation | 49 frames |
| IASA | 18 |
| Auto-cancel | land ≤ frame 4 or ≥ frame 33 |
| Landing lag | 18 |
| **L-cancel landing lag** | **9** |
| Damage | 2% (id1) / 3% (id0) per hit |

- It is a **multi-hit move**; opponents can DI/SDI out. For drillshine, the macro typically only needs the **last 1–2 hits** to connect before landing → then shine.
Source: FightCore Fox Dair.

---

## 5. Fast Fall

- **Input:** Tap **down on the control stick** (full down, past the fast-fall threshold) while in the falling phase. Must be a fresh tap from a non-down position; held-down-from-jump can register depending on stick history — for a macro, return the stick to neutral after the jump, then snap to **full down (−1.0 Y)**.
- **When valid:** Only while **falling** (descending) and **not tumbling**. Earliest frames: short hop = **frame 12**, full hop = **frame 18** (i.e. at/after apex). Inputting down before the apex does nothing for FF.
- **C-stick down:** Does **not** trigger fast fall. C-stick down in the air issues a **down-aerial (dair)**. Fast fall MUST come from the **control stick**. (This matters for the macro: use control-stick down for FF, C-stick for the aerial.)
- **Effect:** fall speed 2.8 → 3.4.

Sources: SmashWiki *Fast-falling*, *Short hop*. C-stick = aerials (control stick = movement/FF) is standard Melee behavior.

---

## 6. SHFFL (Short Hop Fast Fall L-Cancel)

**Goal:** Fastest possible grounded → aerial → grounded cycle. Sequence: short hop → aerial (C-stick) → fast fall at apex → L-cancel before landing.

### Generic input sequence
1. **Frame 0:** Tap X or Y (jump). **Release within 2 frames** (short hop). Grounded jumpsquat = frames 1–3, airborne frame 4.
2. **Frames 4+:** Input aerial via **C-stick** in the desired direction (or A+stick). C-stick aerials don't affect drift, so movement stays clean.
3. **At/after SH apex (≈frame 12 of airtime):** Snap **control stick to full down** to fast fall.
4. **Within 7 frames before landing:** Press **L/R** (or Z) to L-cancel. With hitlag extension, pressing during a connecting hit also works.

### Per-aerial SHFFL timing (short hop, airborne on frame 4)

Times below reference the **short-hop airtime clock** (frame 1 = first airborne frame; SH lands at frame 21 if no FF, ~frame 15 region with FF from frame 12).

| Aerial | Earliest aerial input | Aerial total | Notes for SHFFL |
|---|---|---|---|
| **Nair** | airborne (frame 4 abs) | 39 | Short startup (active f4); easiest to fit in a short hop. Input immediately on leaving ground. |
| **Fair** | airborne | 59 | Longest aerial; on a SH it will NOT fully complete — input ASAP, expect to L-cancel mid-animation. |
| **Bair** | airborne | ~33 | Turn around (face away) before/at jump; input bair early. |
| **Uair** | airborne | ~32 | Startup f8 — input as soon as airborne so hit lands before descent. |
| **Dair** | airborne | 49 | Input immediately; for drillshine you want last hit(s) to connect just before landing, then L-cancel + shine. |

**Recommended macro pattern (relative to jump press at T=0):**
- T=0: press jump (X/Y), release by T=2.
- T≈4 (first airborne frame): C-stick toward aerial direction.
- T≈12–14: control stick full down (fast fall).
- T≈(predicted land − 5): press L/R, hold ~3–4 frames.

Sources: SmashWiki / Liquipedia *SHFFL*, *Short hop*; Fox airtime constants above. Exact land frame depends on aerial chosen and FF timing — compute `landFrame` from SH airtime (21) minus FF reduction.

---

## 7. Shine (Reflector, Down-B) — Frame Data

| Property | Value |
|---|---|
| Hitbox active | **frame 1 only** |
| Intangibility | **frame 1 only** |
| Jump-cancellable | **frames 4–21** |
| Reflect (vs projectiles) | frames 4 → release+1 |
| Total animation (no reflect) | 39 frames |
| IASA (via jump cancel) | frame 4 |
| Turnaround penalty | Turning the shine around disables jump-cancel for **3 frames** (those frames always reflect) |

- **Key for combos:** Fox can **jump-cancel the shine starting frame 4**. JC-shine for grounded movement: press Down-B, then on frame 4 press jump.
- **Multishine constants:** JC window 4–21; earliest 2nd reflector input frame 7; grounded again frame 11; earliest jump startup frame 12. Multishine = repeat {jump f1–3, shine f4} as fast as possible.

Sources: SmashWiki *Fox (SSBM)/Down special*, *Reflector (Fox)*, *Multishine*; Hit Box Arcade.

> Note: SmashWiki's move-data table lists shine **hitbox = frame 1**. Some older guides describe "reflecting begins frame 3"; that refers to the projectile-reflect bubble (frames 4+), not the knockback hitbox. For comboing, treat the **hitbox as frame 1** and **jump-cancel as frame 4**.

---

## 8. Combo / Tech Techniques

All combos below assume Fox grounded unless noted. "JC" = jump-cancel.

### 8.1 Waveshine
**Definition:** Wavedash immediately out of a jump-cancelled shine. Foundation of Fox's shine pressure.

**Input sequence:**
| Step | Input | Frame |
|---|---|---|
| 1 | Down-B (shine) | shine f1 (hitbox + intangible) |
| 2 | Jump (X/Y) | shine f4 (jump-cancel) |
| 3 | Air dodge (L/R) + control stick diagonally **down-toward** target | during the 3-frame jumpsquat of the JC jump → wavedash |

- Use **X/Y for the jump** (not stick up) so the stick is free to angle down for the wavedash.
- **Wavedash angle:** low angle = longer slide. Theoretical max distance ≈ **17.1°** above horizontal; practical "shallow but safe" angles common. Air dodge = L or R trigger + stick toward `down + forward`.
- Result: Fox slides forward still grounded and **actionable**, ready for the next action (another shine, grab, smash, dair).

### 8.2 Waveshine → Grab → Up-throw → Up-air
**Use:** Low-% combo / kill confirm at higher %.

| Step | Input | Timing note |
|---|---|---|
| 1 | Shine (Down-B) | hits opponent |
| 2 | JC + wavedash forward | waveshine to close distance |
| 3 | Grab (Z, or dash-attack-cancel grab via dash→Z) | grab once in range; "dashed JC grab" is the standard follow-up |
| 4 | Up-throw (control stick up + throw) | |
| 5 | Up-air (jump → C-stick up) | after up-throw; **up-throw up-air is a near-guaranteed kill at high %** |

- **Throw-window note:** opponents at **>~30%** may be able to shine/jump out — at those %s prefer up-tilt or immediate up-air to continue rather than re-grab.
- Up-throw → up-air: jump after the throw and uair (startup f8) timed so the multi-hit catches the rising opponent. Exact frame gap is %-/character-dependent; not a fixed-frame combo.

### 8.3 Up-throw → Up-air (standalone)
- Up-throw, then **full-hop or short-hop + uair** depending on opponent's launch height and %. Uair active frame 8. This is Fox's primary vertical kill confirm at high %.

### 8.4 Drillshine (Dair → Shine)
**Input sequence:**
| Step | Input | Frame note |
|---|---|---|
| 1 | Short hop (X/Y, release ≤2 frames) | airborne f4 |
| 2 | Dair (C-stick down) | active f5–24, multi-hit |
| 3 | Fast fall (control stick down) at/after apex | so dair's later hits land low |
| 4 | **L-cancel** (L/R) within 7 frames of landing | dair L-cancel lag = **9** |
| 5 | Shine (Down-B) on landing | immediately after the 9-frame L-cancelled landing |
| (repeat) | JC the shine (f4) → short hop → dair … | drillshine "infinite" / pressure |

- Critical: **C-stick down = dair**, **control stick down = fast fall** (do not conflate). With C-stick handling the aerial, the control stick is free for the FF input.
- The drill's last hit should connect just before/at landing so the shine links.

### 8.5 Pillar Combo (Waveshine → Dair → Shine, repeat)
"Pillaring" = stacking waveshine + drill loops to trap the opponent vertically/horizontally.

| Step | Input |
|---|---|
| 1 | Shine (Down-B) |
| 2 | JC + wavedash forward (waveshine) — repositions under/behind opponent |
| 3 | Short hop → dair (C-stick down) → fast fall → L-cancel |
| 4 | Shine on landing |
| 5 | Repeat from step 2 |

- This is essentially {waveshine → drillshine} chained. Each shine resets hitstun; spacing via wavedash keeps the opponent in the "pillar."

### 8.6 Shine Turnaround / Pivot Shine
- **Turnaround shine:** While shining, push control stick the opposite direction. The reflect bubble persists, but **jump-cancel is disabled for 3 frames** after the turnaround (those 3 frames force a reflect). After the 3 frames, JC/turn again is available.
- **Pivot shine:** Use to flip Fox's facing direction mid-pressure so the next waveshine/grab goes the other way. Macro note: after issuing turnaround-shine, **wait 3 frames** before attempting JC.
Source: SmashWiki *Fox (SSBM)/Down special* (turnaround disables JC for 3 frames).

### 8.7 Ledgedash + Aerial Follow-ups
**Standard ledgedash:** drop from ledge → jump back toward stage → air dodge diagonally into the ground (waveland onto stage) to gain **GALINT** (Guaranteed Actionable Ledge INTangibility).

| Step | Input | Frame (from ledge release) |
|---|---|---|
| 1 | Drop ledge (down or back, or jump straight from ledge) | f0 |
| 2 | Jump toward stage (double jump if dropped) | "jump for 3+ frames before air dodging" — preserve height |
| 3 | Air dodge (L/R) + stick **down-toward stage ≈45°** | best GALINT across timings |
| 4 | Waveland onto stage; act during intangible frames | best-case **15 frames GALINT** |

- **Fox JC-shine ledgedash variant (high intangibility):** after letting go of ledge — jump on **frame 2**, **shine on frame 4**, **jump again on frame 7** — yields large semi-actionable intangibility, then air dodge to waveland.
- **Aerial follow-ups out of ledgedash:** during the GALINT window, the macro can immediately issue a SHFFL'd aerial (nair/bair/uair) or a grab/shine. Because intangibility is active, these are effectively safe "get-off-ledge" pressure or punish starters.
- **Optimal air dodge angle:** ~45° down-toward-stage (best GALINT across the widest timing/ECB range).

Sources: SmashWiki *Ledgedash*; Alex's Puff Stuff Fox ledgedash article; Smashboards ledgedash frame-data thread.

### 8.8 Gentleman-style follow-ups
**N/A for Fox.** "Gentleman" is a Captain Falcon (jab → jab → jab-reset) tech. Fox has no equivalent jab-string finisher. Skipped per request.

---

## 9. Quick Reference — Macro Input Mapping

| Action | Recommended physical input |
|---|---|
| Jump | X or Y (digital) |
| Short hop | X/Y held ≤2 frames |
| Aerial (nair/fair/bair/uair) | **C-stick** in direction (keeps drift clean) |
| Dair | **C-stick down** |
| Fast fall | **Control stick full down** (NOT C-stick), only after apex |
| L-cancel | L or R trigger, within 7 frames pre-landing (hold/repeat for safety) |
| Shine | Down-B (control stick down + B) |
| Jump-cancel shine | Down-B, then X/Y on shine frame 4 |
| Wavedash / waveshine | (JC) jump → L/R air dodge + control stick down-forward (~17° for distance, ~45° for ledgedash) |
| Grab | Z (or dash → Z for dash-grab) |

---

## 10. Source Reliability Summary

| Data point | Confidence | Source(s) |
|---|---|---|
| L-cancel 7-frame window, halve-rounded-down | **High** | SmashWiki *L-canceling* (uncontested) |
| L-cancel hitlag +6 extension | High | SmashWiki *L-canceling* |
| Jumpsquat 3 / airborne frame 4 | **High** | Hit Box Arcade, SmashWiki *Jump* |
| SH airtime 21 / FH 35; FF earliest 12/18 | High | SmashWiki, community frame tables |
| Shine hitbox f1, JC f4–21, total 39 | **High** | SmashWiki *Fox down special* |
| Aerial landing lag + L-cancel lag (fair/bair/uair/dair) | **High** | Liquipedia + FightCore (agree) |
| **Nair landing lag/L-cancel (10→7?)** | **CONTESTED** | Liquipedia lists 10/7; floor(10/2)=5. Verify in-engine. |
| Dair exact hit frames (5-6…23-24) | **High** | FightCore (explicit windows) |
| Bair total frames (~33) | Medium | Inferred from active-16; verify |
| Ledgedash 45° / 15 GALINT; Fox JC-shine ledgedash f2/f4/f7 | High | SmashWiki *Ledgedash*, Alex's Puff Stuff |
| Fast fall = control stick only (C-stick = aerial) | High | Standard Melee mechanic / SmashWiki |

---

### Primary Sources
- SmashWiki: L-canceling, Lag, Fast-falling, Short hop, Jump, Reflector (Fox), Fox (SSBM)/Down special, Multishine, Waveshine, Wavedashing, Ledgedash, SHFFL
- Liquipedia: Fox/Frame Data, Short Hop Fast Fall L-Cancel
- FightCore: Fox Dair (fightcore.gg/characters/224/fox)
- meleeframedata.com/fox (cross-reference; site cert expired at fetch time)
- Smashboards: "COMPLETE: Fox Hitboxes and Frame Data" (#285177); Ledgedash Frame Data thread
- Hit Box Arcade: "SSBM — Fox Jumpsquats & Multishine"
- Alex's Puff Stuff: Fox Ledgedash Consistency

> **Before locking the input-injection timings, validate the two CONTESTED rows (Nair landing lag, Bair total) against an in-engine frame counter (Slippi frame advance / 20XX), since these feed real timing.**
