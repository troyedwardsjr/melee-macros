"""Normalized live game-state view, read from libmelee's per-frame GameState.

Open-loop (pipe) mode has no game state, so everything here is optional: the
engine treats a ``None`` :class:`GameView` as "unknown" and falls back to fixed
timing. When the libmelee backend is active, each frame yields a populated
``GameView`` that closed-loop macros and trigger-gating can react to.

libmelee is imported lazily (only inside :func:`from_libmelee`) so the rest of
the package works without the optional ``melee`` dependency installed.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Action-state name groups. libmelee exposes the action as an enum whose `.name`
# we store as a string; matching by name keeps us tolerant across melee/libmelee
# versions where numeric ids shift. Names are matched case-insensitively.
_SHIELD = {"SHIELD", "SHIELD_START", "SHIELD_STRETCH", "SHIELD_REFLECT"}
_GRAB_HOLD = {"GRAB", "GRABBING", "GRAB_PULLING", "GRAB_WAIT", "GRAB_PULL"}
_LEDGE = {"EDGE_HANGING", "EDGE_CATCHING", "LEDGE_HANG", "EDGE_HANG"}
_LAND = {"LANDING", "LANDING_SPECIAL"}
# Actions from which Fox can immediately act (rough "actionable" set).
_ACTIONABLE = {
    "STANDING", "WALK_SLOW", "WALK_MIDDLE", "WALK_FAST", "DASHING", "RUNNING",
    "TURNING", "CROUCHING", "CROUCH_START", "WAIT_ITEM",
}


@dataclass
class GameView:
    """A flattened, character-agnostic snapshot of one game frame.

    All fields are best-effort; missing data stays at its default so predicates
    degrade safely rather than raising.
    """

    # --- self (our port) ---
    action: str = ""
    action_frame: int = 0
    on_ground: bool = True
    x: float = 0.0
    y: float = 0.0
    speed_y: float = 0.0
    speed_air_x: float = 0.0
    percent: float = 0.0
    jumps_left: int = 1
    invulnerable: bool = False
    hitstun: float = 0.0
    shield_strength: float = 60.0
    facing_right: bool = True
    off_stage: bool = False

    # --- opponent (nearest other port) ---
    opp_x: float = 0.0
    opp_y: float = 0.0
    opp_action: str = ""
    opp_action_frame: int = 0
    opp_percent: float = 0.0
    opp_off_stage: bool = False
    opp_on_ground: bool = True
    opp_facing_right: bool = True
    opp_hitstun: float = 0.0
    opp_present: bool = False

    # --- stage ---
    stage: str = ""
    edge_x: float = 0.0  # x of the right ground edge; left edge is -edge_x

    # ----- self predicates -----
    @property
    def airborne(self) -> bool:
        return not self.on_ground

    @property
    def shielding(self) -> bool:
        return self.action.upper() in _SHIELD

    @property
    def holding_grab(self) -> bool:
        return self.action.upper() in _GRAB_HOLD

    @property
    def on_ledge(self) -> bool:
        return self.action.upper() in _LEDGE

    @property
    def landing(self) -> bool:
        return self.action.upper() in _LAND

    @property
    def in_hitstun(self) -> bool:
        return self.hitstun > 0

    @property
    def falling(self) -> bool:
        return self.airborne and self.speed_y < 0.0

    @property
    def actionable(self) -> bool:
        return self.on_ground and self.action.upper() in _ACTIONABLE

    def about_to_land(self, lookahead: int = 2, ground_pad: float = 4.0) -> bool:
        """Predict an imminent ground landing for L-cancel timing.

        Heuristic (main-stage ground ~= y 0): we are airborne, descending, and
        the next ``lookahead`` frames of vertical travel reach the ground.
        Platforms aren't modeled, so this is conservative — it can miss aerials
        landing on a platform. Closed-loop callers also press L on the LANDING
        action as a backstop.
        """
        if not self.falling:
            return False
        return (self.y + self.speed_y * lookahead) <= ground_pad

    # ----- opponent predicates (for edgeguarding) -----
    @property
    def opp_below_ledge(self) -> bool:
        return self.opp_present and self.opp_off_stage and self.opp_y < -2.0

    @property
    def opp_recovering_high(self) -> bool:
        return self.opp_present and self.opp_off_stage and self.opp_y >= -2.0

    def opp_side(self) -> int:
        """-1 if opponent is off the left edge, +1 if off the right, else 0."""
        if not self.opp_present:
            return 0
        if self.opp_x < -self.edge_x:
            return -1
        if self.opp_x > self.edge_x:
            return 1
        return 0


# Named predicates usable in config `requires:` on a trigger.
REQUIRE_PREDICATES = {
    "shielding": lambda v: v.shielding,
    "airborne": lambda v: v.airborne,
    "grounded": lambda v: v.on_ground,
    "holding_grab": lambda v: v.holding_grab,
    "on_ledge": lambda v: v.on_ledge,
    "offstage": lambda v: v.off_stage,
    "in_hitstun": lambda v: v.in_hitstun,
    "actionable": lambda v: v.actionable,
    "opp_offstage": lambda v: v.opp_present and v.opp_off_stage,
}


def _attr(obj, *names, default=None):
    for n in names:
        if hasattr(obj, n):
            return getattr(obj, n)
    return default


def _action_name(state) -> str:
    a = _attr(state, "action")
    if a is None:
        return ""
    return getattr(a, "name", str(a))


def from_libmelee(gamestate, port: int, opp_port: int | None = None) -> GameView | None:
    """Convert a libmelee ``GameState`` into a :class:`GameView`.

    Returns ``None`` if our player isn't present in the frame (e.g. still on a
    menu). Field access is defensive so minor libmelee API drift won't crash the
    live loop.
    """
    if gamestate is None:
        return None
    players = _attr(gamestate, "players", default={}) or {}
    me = players.get(port)
    if me is None:
        return None

    # Pick the opponent: explicit port, else the first other present port.
    if opp_port is None:
        others = [p for p in players if p != port]
        opp_port = others[0] if others else None
    opp = players.get(opp_port) if opp_port is not None else None

    def pos(state, axis):
        p = _attr(state, "position")
        if p is not None:
            return float(_attr(p, axis, default=0.0) or 0.0)
        return float(_attr(state, f"{axis}", default=0.0) or 0.0)

    # Stage edge (right ground edge). API name varies across versions.
    stage = _attr(gamestate, "stage")
    edge_x = 0.0
    try:
        import melee  # lazy

        for fn in ("EDGE_GROUND_POSITION", "EDGE_POSITION"):
            f = getattr(melee.stages, fn, None)
            if callable(f) and stage is not None:
                edge_x = abs(float(f(stage)))
                break
    except Exception:
        edge_x = 0.0

    view = GameView(
        action=_action_name(me),
        action_frame=int(_attr(me, "action_frame", default=0) or 0),
        on_ground=bool(_attr(me, "on_ground", default=True)),
        x=pos(me, "x"),
        y=pos(me, "y"),
        speed_y=float(_attr(me, "speed_y_self", "speed_y", default=0.0) or 0.0),
        speed_air_x=float(_attr(me, "speed_air_x_self", default=0.0) or 0.0),
        percent=float(_attr(me, "percent", default=0.0) or 0.0),
        jumps_left=int(_attr(me, "jumps_left", default=1) or 0),
        invulnerable=bool(_attr(me, "invulnerable", default=False)),
        hitstun=float(_attr(me, "hitstun_frames_left", default=0.0) or 0.0),
        shield_strength=float(_attr(me, "shield_strength", default=60.0) or 0.0),
        facing_right=bool(_attr(me, "facing", default=True)),
        off_stage=bool(_attr(me, "off_stage", default=False)),
        stage=getattr(stage, "name", "") if stage is not None else "",
        edge_x=edge_x,
    )
    if opp is not None:
        view.opp_present = True
        view.opp_x = pos(opp, "x")
        view.opp_y = pos(opp, "y")
        view.opp_action = _action_name(opp)
        view.opp_action_frame = int(_attr(opp, "action_frame", default=0) or 0)
        view.opp_percent = float(_attr(opp, "percent", default=0.0) or 0.0)
        view.opp_off_stage = bool(_attr(opp, "off_stage", default=False))
        view.opp_on_ground = bool(_attr(opp, "on_ground", default=True))
        view.opp_facing_right = bool(_attr(opp, "facing", default=True))
        view.opp_hitstun = float(_attr(opp, "hitstun_frames_left", default=0.0) or 0.0)
    return view
