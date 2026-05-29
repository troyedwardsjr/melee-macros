"""Fox (SSBM) competitive-tech macros, as frame-accurate input timelines.

Frame numbers below are stated in the builder's 0-indexed convention
(frame 0 = first frame the macro is applied). The research docs in
``docs/`` use a 1-indexed convention, so research "frame N" == builder
"frame N-1". Key Fox constants reused throughout:

    jumpsquat            = 3 frames  (grounded 0,1,2; airborne on frame 3)
    short-hop window     = release jump within frames 0..1
    shine jump-cancel    = earliest builder frame 3 (research frame 4)
    multishine period    = 6 frames (reshine builder f6; research "2nd reflector frame 7")
    wavedash airdodge    = first airborne frame
    firefox aim lock     = builder frame 41 (research frame 42)

OPEN-LOOP CAVEATS: techniques that truly depend on game state — L-cancel
landing frame, teching on contact, ledgedash ECB, multishine drift, throw
follow-ups — are encoded as best-effort fixed timelines. They are reliable in
libmelee (frame-stepped) mode and approximate in wall-clock pipe mode. Such
macros are flagged "STATE-DEPENDENT" in their description.
"""

from __future__ import annotations

from ..library import MacroLibrary
from ..macro import MacroBuilder

# --- Fox frame constants ------------------------------------------------
JUMPSQUAT = 3
AIRBORNE = JUMPSQUAT  # first airborne builder frame after a frame-0 jump
SHINE_JC = 3  # earliest builder frame to act out of a shine (research frame 4)
MULTISHINE_PERIOD = 6
AIM_LOCK = 41  # firefox direction is read here (research frame 42)

# --- analog coordinates (unit convention: -1..+1, +y = up) --------------
DOWN = (0.0, -1.0)
UP = (0.0, 1.0)
NEUTRAL = (0.0, 0.0)

# Wavedash: shallow down-forward (~17 deg) for max slide (research §3).
WD_FWD = (0.85, -0.50)
WD_BACK = (-0.85, -0.50)
# Ledgedash / waveland-onto-stage airdodge: ~45 deg down-toward stage.
WL_TOWARD_RIGHT = (0.70, -0.70)
WL_TOWARD_LEFT = (-0.70, -0.70)


def _mirror_x(coord: tuple[float, float]) -> tuple[float, float]:
    return (-coord[0], coord[1])


# ======================================================================
# MOVEMENT
# ======================================================================
def _short_hop() -> MacroBuilder:
    b = MacroBuilder("short_hop", "Short hop: tap Y for 1 frame (Fox SH window = 2f).")
    b.tap("Y", 0, dur=1)
    return b.pad_to(4)


def _full_hop() -> MacroBuilder:
    b = MacroBuilder("full_hop", "Full hop: hold Y through jumpsquat (>=3 frames).")
    b.hold("Y", 0, 5)
    return b.pad_to(6)


def _wavedash(name: str, coord: tuple[float, float]) -> MacroBuilder:
    b = MacroBuilder(
        name,
        "Wavedash: hold down-diagonal, jump (Y) f0, airdodge (L) on first "
        "airborne frame (f3). ~10f landing lag follows.",
    )
    b.main(coord[0], coord[1], 0, AIRBORNE + 3)  # hold diagonal through airdodge
    b.tap("Y", 0, dur=1)
    b.tap("L", AIRBORNE, dur=2)  # digital airdodge on first airborne frame
    return b.pad_to(AIRBORNE + 4)


def _dash_dance(name: str, first_right: bool, cycles: int = 4) -> MacroBuilder:
    """Reverse the control stick within the 11f initial-dash window."""
    b = MacroBuilder(name, f"Dash dance: alternate full L/R every 8f ({cycles} legs).")
    leg = 8  # comfortably inside the 11f dash window
    x = 1.0 if first_right else -1.0
    for i in range(cycles):
        sign = x if i % 2 == 0 else -x
        b.main(sign, 0.0, i * leg, (i + 1) * leg)
    return b.pad_to(cycles * leg)


def _foxtrot(name: str, right: bool, steps: int = 3) -> MacroBuilder:
    """Re-smash the same direction before the run animation locks (within 11f)."""
    b = MacroBuilder(name, f"Foxtrot: re-dash same direction every 10f ({steps} steps).")
    x = 1.0 if right else -1.0
    period = 10
    for i in range(steps):
        b.main(x, 0.0, i * period, i * period + 6)  # dash, then neutral gap before re-dash
    return b.pad_to(steps * period)


def _moonwalk(name: str, right_facing: bool) -> MacroBuilder:
    """Down-back diagonal held >=2f, then straight back (research §10)."""
    # Moonwalk slides backward relative to facing; "back" = away from facing dir.
    back_x = -1.0 if right_facing else 1.0
    b = MacroBuilder(name, "Moonwalk: down-back diagonal >=2f, then straight back.")
    b.main(back_x * 0.7, -0.7, 0, 4)  # down-back notch, held 4 frames
    b.main(back_x, 0.0, 4, 12)  # straight back
    return b.pad_to(12)


def _pivot(name: str, right: bool) -> MacroBuilder:
    """Empty pivot: 1-frame opposite flick, then neutral (research §8/§9)."""
    b = MacroBuilder(name, "Empty pivot: dash then 1-frame opposite flick (1f window).")
    x = 1.0 if right else -1.0
    b.main(x, 0.0, 0, 6)  # initial dash
    b.main(-x, 0.0, 6, 7)  # exactly 1 frame opposite
    return b.pad_to(8)


def _jc_grab(name: str) -> MacroBuilder:
    """Jump-cancel grab: jump, press Z during the 3f jumpsquat (research §11)."""
    b = MacroBuilder(name, "JC grab: jump (Y) f0, Z during jumpsquat (f1) -> standing grab.")
    b.tap("Y", 0, dur=1)
    b.tap("Z", 1, dur=1)  # within jumpsquat frames 0..2
    return b.pad_to(4)


def _boost_grab(name: str) -> MacroBuilder:
    """Dash attack -> cancel into dash grab on frames 2-4 (research §12)."""
    b = MacroBuilder(name, "Boost grab: A (dash attack) f0, Z f1 (cancel window f2-4).")
    b.tap("A", 0, dur=1)
    b.tap("Z", 1, dur=1)
    return b.pad_to(4)


# ======================================================================
# SHINE
# ======================================================================
def _shine() -> MacroBuilder:
    b = MacroBuilder("shine", "Shine: Down+B. Hitbox f1, jump-cancellable from f3.")
    b.main(*DOWN, 0, 2)
    b.tap("B", 0, dur=1)
    return b.pad_to(4)


def _jc_shine() -> MacroBuilder:
    b = MacroBuilder("jc_shine", "JC shine: shine f0, jump (Y) f3 -> actionable.")
    b.main(*DOWN, 0, 2)
    b.tap("B", 0, dur=1)
    b.tap("Y", SHINE_JC, dur=1)
    return b.pad_to(SHINE_JC + 2)


def _waveshine(name: str, coord: tuple[float, float]) -> MacroBuilder:
    """Shine -> JC jump -> airdodge into ground (research shine_defense Waveshine)."""
    b = MacroBuilder(
        name,
        "Waveshine: shine f0, JC jump (Y) f3, airdodge (L)+down-diagonal on the "
        "new airborne frame (f6) -> slide, actionable on land.",
    )
    b.main(*DOWN, 0, 2)
    b.tap("B", 0, dur=1)
    b.tap("Y", SHINE_JC, dur=1)
    air = SHINE_JC + JUMPSQUAT  # airborne frame of the JC jump = f6
    b.main(coord[0], coord[1], air - 1, air + 2)  # diagonal set just before/through airdodge
    b.tap("L", air, dur=2)
    return b.pad_to(air + 3)


def _multishine(cycles: int = 6) -> MacroBuilder:
    """Looped JC shines. shine f0, jump f3, reshine f6, ... period 6 (research)."""
    b = MacroBuilder("multishine", f"Multishine: shine/jump on a 6f period ({cycles} shines). STATE-DEPENDENT timing.")
    for i in range(cycles):
        base = i * MULTISHINE_PERIOD
        b.main(*DOWN, base, base + 1)
        b.tap("B", base, dur=1)
        if i < cycles - 1:
            b.tap("Y", base + SHINE_JC, dur=1)  # JC jump between shines
    return b.pad_to(cycles * MULTISHINE_PERIOD)


def _shine_oos() -> MacroBuilder:
    """From shield: jump OOS, JC into shine (research Shine OOS)."""
    b = MacroBuilder("shine_oos", "Shine OOS: jump (Y) f0 out of shield, shine (Down+B) f3. STATE-DEPENDENT (must be shielding).")
    b.tap("Y", 0, dur=1)
    b.main(*DOWN, AIRBORNE, AIRBORNE + 2)
    b.tap("B", AIRBORNE, dur=1)
    return b.pad_to(AIRBORNE + 2)


# ======================================================================
# AERIALS / SHFFL / COMBOS
# ======================================================================
def _shffl(name: str, aerial: str, facing_right: bool = True) -> MacroBuilder:
    """Short hop -> aerial (C-stick, except nair) -> fast fall -> L-cancel.

    aerial in {nair, fair, bair, uair, dair}. Fast fall from ~apex (f11),
    L-cancel press window before predicted landing. STATE-DEPENDENT (landing
    frame varies with fast-fall timing / aerial)."""
    b = MacroBuilder(name, f"SHFFL {aerial}: SH, {aerial} via C-stick, FF at apex, L-cancel. STATE-DEPENDENT.")
    b.tap("Y", 0, dur=1)  # short hop
    fwd = 1.0 if facing_right else -1.0
    if aerial == "nair":
        b.tap("A", AIRBORNE, dur=1)
    elif aerial == "uair":
        b.cstick(0.0, 1.0, AIRBORNE, AIRBORNE + 2)
    elif aerial == "dair":
        b.cstick(0.0, -1.0, AIRBORNE, AIRBORNE + 2)
    elif aerial == "fair":
        b.cstick(fwd, 0.0, AIRBORNE, AIRBORNE + 2)
    elif aerial == "bair":
        b.cstick(-fwd, 0.0, AIRBORNE, AIRBORNE + 2)
    else:
        raise ValueError(aerial)
    # Fast fall: control stick full down from ~apex (research: SH earliest FF f12 -> builder f11).
    b.main(0.0, -1.0, 11, 18)
    # L-cancel: press L across the predicted landing window (FF SH lands ~f15-16).
    b.tap("L", 14, dur=4)
    return b.pad_to(18)


def _drillshine(facing_right: bool = True) -> MacroBuilder:
    """Dair -> shine on landing, then JC out (research aerials §8.4). STATE-DEPENDENT."""
    b = MacroBuilder("drillshine", "Drillshine: SH dair, FF, L-cancel, shine on landing, JC. STATE-DEPENDENT.")
    b.tap("Y", 0, dur=1)
    b.cstick(0.0, -1.0, AIRBORNE, AIRBORNE + 2)  # dair
    b.main(0.0, -1.0, 11, 18)  # fast fall
    b.tap("L", 14, dur=3)  # L-cancel near landing
    # Shine shortly after the L-cancelled landing (dair L-cancel lag = 9):
    shine_f = 19
    b.main(*DOWN, shine_f, shine_f + 1)
    b.tap("B", shine_f, dur=1)
    b.tap("Y", shine_f + SHINE_JC, dur=1)  # JC out
    return b.pad_to(shine_f + SHINE_JC + 2)


def _upthrow_uair() -> MacroBuilder:
    """Up-throw then up-air. STATE-DEPENDENT (requires an active grab; follow-up gap is %/char dependent)."""
    b = MacroBuilder("upthrow_uair", "Up-throw -> up-air kill confirm. STATE-DEPENDENT (must already be holding a grab).")
    b.main(*UP, 0, 2)  # up throw
    jump_f = 6
    b.tap("Y", jump_f, dur=1)  # jump to chase
    b.cstick(0.0, 1.0, jump_f + AIRBORNE, jump_f + AIRBORNE + 2)  # uair
    return b.pad_to(jump_f + AIRBORNE + 3)


# ======================================================================
# DEFENSE / TECH
# ======================================================================
def _tech(name: str, direction: tuple[float, float] | None) -> MacroBuilder:
    """Single L press (+optional roll direction). STATE-DEPENDENT: only valid
    on the contact frame; never double-tap (40f lockout)."""
    label = {None: "in place", (-1.0, 0.0): "roll left", (1.0, 0.0): "roll right"}.get(
        direction, "roll"
    )
    b = MacroBuilder(name, f"Tech {label}: single L press on contact (20f window). STATE-DEPENDENT.")
    if direction is not None:
        b.main(direction[0], direction[1], 0, 3)
    b.tap("L", 0, dur=1)
    return b.pad_to(3)


def _spotdodge() -> MacroBuilder:
    b = MacroBuilder("spotdodge", "Spotdodge: down + L. Intangible f2-15.")
    b.main(*DOWN, 0, 3)
    b.tap("L", 0, dur=1)
    return b.pad_to(3)


def _roll(name: str, right: bool) -> MacroBuilder:
    b = MacroBuilder(name, "Roll: L + direction. Intangible f4-19. STATE-DEPENDENT (from shield/stand).")
    x = 1.0 if right else -1.0
    b.main(x, 0.0, 0, 3)
    b.tap("L", 0, dur=1)
    return b.pad_to(3)


def _powershield() -> MacroBuilder:
    b = MacroBuilder("powershield", "Powershield: brief L tap (4f window vs physical). STATE-DEPENDENT (time to the hit).")
    b.tap("L", 0, dur=1)
    return b.pad_to(2)


# ======================================================================
# RECOVERY
# ======================================================================
def _firefox(name: str, angle: tuple[float, float]) -> MacroBuilder:
    """Up-B: trigger with up+B, then hold the travel angle through the f41 aim
    lock (research frame 42). Launches f42 (builder)."""
    b = MacroBuilder(name, "Firefox (up-B): up+B f0, hold angle through aim-lock (f41); launches.")
    b.main(*UP, 0, 1)  # up+B to trigger
    b.tap("B", 0, dur=1)
    b.main(angle[0], angle[1], 1, AIM_LOCK + 2)  # set & hold travel angle through lock
    return b.pad_to(AIM_LOCK + 3)


def _illusion(name: str, right: bool, shorten_frame: int | None = None) -> MacroBuilder:
    """Side-B (Fox Illusion). Optional second-B shorten during travel (research:
    5 forward-travel frames = 5 shorten lengths)."""
    desc = "Fox Illusion (side-B): forward+B."
    if shorten_frame is not None:
        desc += f" Shortened (2nd B at f{shorten_frame})."
    b = MacroBuilder(name, desc)
    x = 1.0 if right else -1.0
    b.main(x, 0.0, 0, 3)
    b.tap("B", 0, dur=1)
    if shorten_frame is not None:
        b.tap("B", shorten_frame, dur=1)
    return b.pad_to((shorten_frame or 0) + 2)


def _ledgedash(name: str, stage_to_right: bool) -> MacroBuilder:
    """From ledge hang: drop, jump back toward stage, airdodge ~45 deg into
    stage to waveland (research Ledgedash). STATE-DEPENDENT (ECB-sensitive)."""
    toward = WL_TOWARD_RIGHT if stage_to_right else WL_TOWARD_LEFT
    away_x = 1.0 if not stage_to_right else -1.0  # away from stage to release ledge
    b = MacroBuilder(name, "Ledgedash: drop ledge, jump toward stage, airdodge ~45deg to waveland. STATE-DEPENDENT (ECB).")
    b.main(away_x, 0.0, 0, 1)  # release ledge (research: ~frame 9 of hang)
    b.tap("Y", 1, dur=1)  # jump toward stage
    air = 1 + AIRBORNE
    b.main(toward[0], toward[1], air, air + 3)  # angle into stage
    b.tap("L", air + 1, dur=2)  # airdodge to waveland
    return b.pad_to(air + 4)


# ======================================================================
# EDGEGUARD (aimable / fixed — you position yourself; opponent not read)
# ======================================================================
def _ledgehog(name: str, right: bool) -> MacroBuilder:
    """Walk off the edge to grab the ledge and deny the opponent's recovery.
    `right` = guarding the right ledge. Position next to the ledge first."""
    x = 1.0 if right else -1.0
    b = MacroBuilder(name, "Ledgehog: walk off the edge to grab the ledge (deny recovery). Stand at the ledge first. STATE-DEPENDENT.")
    b.main(x, -0.10, 0, 14)
    return b.pad_to(14)


def _offstage_bair(name: str, right: bool) -> MacroBuilder:
    """Short hop and bair outward toward a recovering opponent. `right` =
    guarding the right ledge (bair hits to the right). Aim yourself offstage."""
    out = 1.0 if right else -1.0
    b = MacroBuilder(name, "Offstage bair: SH + bair toward the ledge/opponent, fast-fall back, L-cancel. Aim yourself. STATE-DEPENDENT.")
    b.tap("Y", 0, dur=1)
    b.cstick(out, 0.0, AIRBORNE, AIRBORNE + 2)  # bair (c-stick outward)
    b.main(0.0, -1.0, AIRBORNE + 3, AIRBORNE + 9)  # fast fall back toward stage
    b.tap("L", AIRBORNE + 6, dur=3)  # L-cancel if you land on-stage
    return b.pad_to(AIRBORNE + 9)


def _offstage_dair(name: str, right: bool) -> MacroBuilder:
    """Short hop and dair (spike) straight down onto the recovery."""
    b = MacroBuilder(name, "Offstage dair spike: SH + dair down on the recovering opponent. STATE-DEPENDENT.")
    b.tap("Y", 0, dur=1)
    b.cstick(0.0, -1.0, AIRBORNE, AIRBORNE + 2)
    b.main(0.0, -1.0, AIRBORNE + 2, AIRBORNE + 9)
    return b.pad_to(AIRBORNE + 9)


def _shine_spike(name: str, right: bool) -> MacroBuilder:
    """Hop offstage, shine to spike, then firefox back to the stage. High risk.
    `right` = guarding the right ledge (jump out to the right, recover left)."""
    out = 1.0 if right else -1.0
    back = -out
    b = MacroBuilder(name, "Shine spike: hop offstage, shine to spike, then firefox back. HIGH RISK. STATE-DEPENDENT.")
    b.tap("Y", 0, dur=1)
    b.main(out, 0.20, 0, 6)  # drift offstage
    sf = 8
    b.main(0.0, -1.0, sf, sf + 1)
    b.tap("B", sf, dur=1)  # shine (spike)
    rec = sf + 6
    b.tap("Y", rec, dur=1)  # jump to recover
    b.main(0.0, 1.0, rec + AIRBORNE, rec + AIRBORNE + 1)
    b.tap("B", rec + AIRBORNE, dur=1)  # firefox up-B
    b.main(back * 0.70, 0.70, rec + AIRBORNE + 1, rec + AIRBORNE + 1 + AIM_LOCK + 1)  # angle back to stage
    return b.pad_to(rec + AIRBORNE + 2 + AIM_LOCK)


# ======================================================================
# REGISTRATION
# ======================================================================
def register_fox_macros(lib: MacroLibrary) -> None:
    builders: list[MacroBuilder] = [
        # movement
        _short_hop(),
        _full_hop(),
        _wavedash("wavedash_forward", WD_FWD),
        _wavedash("wavedash_back", WD_BACK),
        _dash_dance("dash_dance_right", first_right=True),
        _dash_dance("dash_dance_left", first_right=False),
        _foxtrot("foxtrot_right", right=True),
        _foxtrot("foxtrot_left", right=False),
        _moonwalk("moonwalk_right", right_facing=True),
        _moonwalk("moonwalk_left", right_facing=False),
        _pivot("pivot_right", right=True),
        _pivot("pivot_left", right=False),
        _jc_grab("jc_grab"),
        _boost_grab("boost_grab"),
        # shine
        _shine(),
        _jc_shine(),
        _waveshine("waveshine_forward", WD_FWD),
        _waveshine("waveshine_back", WD_BACK),
        _multishine(),
        _shine_oos(),
        # aerials / combos
        _shffl("shffl_nair", "nair"),
        _shffl("shffl_fair", "fair"),
        _shffl("shffl_bair", "bair"),
        _shffl("shffl_uair", "uair"),
        _shffl("shffl_dair", "dair"),
        _drillshine(),
        _upthrow_uair(),
        # defense / tech
        _tech("tech_in_place", None),
        _tech("tech_roll_left", (-1.0, 0.0)),
        _tech("tech_roll_right", (1.0, 0.0)),
        _spotdodge(),
        _roll("roll_right", right=True),
        _roll("roll_left", right=False),
        _powershield(),
        # recovery
        _firefox("firefox_up", UP),
        _firefox("firefox_up_forward", (0.70, 0.70)),
        _firefox("firefox_up_back", (-0.70, 0.70)),
        _firefox("firefox_side_forward", (0.90, 0.40)),
        _firefox("firefox_side_back", (-0.90, 0.40)),
        _illusion("illusion_forward", right=True),
        _illusion("illusion_back", right=False),
        _illusion("illusion_forward_short", right=True, shorten_frame=20),
        _ledgedash("ledgedash_stage_right", stage_to_right=True),
        _ledgedash("ledgedash_stage_left", stage_to_right=False),
        # edgeguard (aimable / fixed — you position; opponent not read)
        _ledgehog("ledgehog_right", right=True),
        _ledgehog("ledgehog_left", right=False),
        _offstage_bair("offstage_bair_right", right=True),
        _offstage_bair("offstage_bair_left", right=False),
        _offstage_dair("offstage_dair_right", right=True),
        _offstage_dair("offstage_dair_left", right=False),
        _shine_spike("shine_spike_right", right=True),
        _shine_spike("shine_spike_left", right=False),
    ]
    for b in builders:
        lib.add(b.build())
