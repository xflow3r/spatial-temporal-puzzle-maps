# jigsaw_tiles.py
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Any, List, Tuple, Optional

Point = Tuple[float, float]
GridPos = Tuple[int, int]


def direction_from_to(a: GridPos, b: GridPos) -> str:
    """
    Cardinal direction from a -> b in grid coords (row, col).
    row increases downward, col increases rightward.
    Returns one of: 'E','W','N','S'
    """
    ar, ac = a
    br, bc = b
    dr, dc = br - ar, bc - ac

    if abs(dr) + abs(dc) == 1:
        if dc == 1:
            return "E"
        if dc == -1:
            return "W"
        if dr == 1:
            return "S"
        return "N"

    # Fallback for unexpected jumps
    if abs(dc) >= abs(dr):
        return "E" if dc > 0 else "W"
    return "S" if dr > 0 else "N"


@dataclass(frozen=True)
class JigsawParams:
    piece_size: float                 # square base size
    tab_radius: float                 # radius of the knob/socket bulge
    tab_offset: float                 # how far knob/socket protrudes (relative to edge)
    samples_per_arc: int = 10         # smoothness of arcs


def _arc_points(cx: float, cy: float, r: float, a0: float, a1: float, n: int) -> List[Point]:
    pts: List[Point] = []
    for i in range(n + 1):
        t = i / n
        a = a0 + (a1 - a0) * t
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _edge_with_tab_or_socket(
    p0: Point,
    p1: Point,
    side: str,
    kind: str,
    params: JigsawParams,
) -> List[Point]:
    """
    Build points along one edge from p0 -> p1, optionally with a tab or socket.
    kind: 'flat' | 'tab' | 'socket'
    side: 'N' | 'E' | 'S' | 'W' (used to orient the bulge)
    """
    if kind == "flat":
        return [p0, p1]

    # Work in edge direction
    x0, y0 = p0
    x1, y1 = p1
    mx, my = (x0 + x1) / 2.0, (y0 + y1) / 2.0

    # Unit tangent along edge and unit normal (outward)
    dx, dy = (x1 - x0), (y1 - y0)
    L = math.hypot(dx, dy)
    tx, ty = dx / L, dy / L

    # Outward normal depends on side in our (x right, y down) coordinate system
    # We'll define outward relative to the square:
    if side == "N":
        nx, ny = 0.0, -1.0
    elif side == "S":
        nx, ny = 0.0, 1.0
    elif side == "E":
        nx, ny = 1.0, 0.0
    else:  # 'W'
        nx, ny = -1.0, 0.0

    # For socket we invert outward direction (go inward)
    sgn = 1.0 if kind == "tab" else -1.0

    r = params.tab_radius
    protrude = params.tab_offset

    # Split edge into three segments: start -> before arc, arc, after arc -> end
    # Arc is centered at (mx, my) shifted by normal * protrude
    cx = mx + nx * protrude * sgn
    cy = my + ny * protrude * sgn

    # We want the arc endpoints to lie on the original edge line near the middle.
    # Choose arc endpoints along the edge at +/- r from the midpoint.
    ex0 = mx - tx * r
    ey0 = my - ty * r
    ex1 = mx + tx * r
    ey1 = my + ty * r

    # Arc angles depend on side and tab/socket.
    # Compute angles from center to endpoints:
    a0 = math.atan2(ey0 - cy, ex0 - cx)
    a1 = math.atan2(ey1 - cy, ex1 - cx)

    # We need the *outer* semicircle for tab, *inner* semicircle for socket,
    # but since we already shifted center by +/- normal, taking the shorter arc
    # often works. We'll force a half-turn arc by adjusting direction.
    # Make arc go the long way around (~pi) in a consistent direction:
    da = a1 - a0
    while da <= -math.pi:
        da += 2 * math.pi
    while da > math.pi:
        da -= 2 * math.pi

    # We want about pi radians sweep; if current sweep is too small, flip it.
    # This yields the bulge shape more like puzzle knobs.
    if abs(da) < math.pi / 2:
        if da >= 0:
            a1 = a1 - 2 * math.pi
        else:
            a1 = a1 + 2 * math.pi

    pts: List[Point] = []
    pts.append(p0)
    pts.append((ex0, ey0))

    arc = _arc_points(cx, cy, r, a0, a1, params.samples_per_arc)
    pts.extend(arc)

    pts.append((ex1, ey1))
    pts.append(p1)
    return pts


def jigsaw_polygon_points(
    *,
    top_left_x: float,
    top_left_y: float,
    piece_size: float,
    edge_kinds: Dict[str, str],  # keys: 'N','E','S','W' values: 'flat'|'tab'|'socket'
    params: JigsawParams,
) -> List[Point]:
    """
    Returns a closed polygon ring (first point repeated at end).
    """
    x0, y0 = top_left_x, top_left_y
    x1, y1 = x0 + piece_size, y0 + piece_size

    # Corner points of the base square
    TL = (x0, y0)
    TR = (x1, y0)
    BR = (x1, y1)
    BL = (x0, y1)

    # Build clockwise, stitching edges
    pts: List[Point] = []

    # Top edge TL -> TR
    pts.extend(_edge_with_tab_or_socket(TL, TR, "N", edge_kinds.get("N", "flat"), params)[:-1])
    # Right edge TR -> BR
    pts.extend(_edge_with_tab_or_socket(TR, BR, "E", edge_kinds.get("E", "flat"), params)[:-1])
    # Bottom edge BR -> BL
    pts.extend(_edge_with_tab_or_socket(BR, BL, "S", edge_kinds.get("S", "flat"), params)[:-1])
    # Left edge BL -> TL
    pts.extend(_edge_with_tab_or_socket(BL, TL, "W", edge_kinds.get("W", "flat"), params)[:-1])

    # Close ring
    pts.append(pts[0])
    return pts


def piece_edge_kinds_for_timeline(pieces: List[Dict[str, Any]], i: int) -> Dict[str, str]:
    """
    Decide which side has the incoming socket and outgoing tab.
    Start piece: no incoming socket.
    End piece: no outgoing tab.
    """
    n = len(pieces)
    kinds = {"N": "flat", "E": "flat", "S": "flat", "W": "flat"}

    # Incoming: socket on side facing previous piece
    if i > 0:
        cur = tuple(pieces[i]["grid_position"])
        prev = tuple(pieces[i - 1]["grid_position"])
        incoming_dir = direction_from_to(cur, prev)  # direction from current toward prev
        # If prev is to our West, incoming_dir == 'W' => socket on W
        kinds[incoming_dir] = "socket"

    # Outgoing: tab on side facing next piece
    if i < n - 1:
        cur = tuple(pieces[i]["grid_position"])
        nxt = tuple(pieces[i + 1]["grid_position"])
        outgoing_dir = direction_from_to(cur, nxt)  # direction from current toward next
        kinds[outgoing_dir] = "tab"

    # If both would land on same side (rare), keep outgoing tab over socket
    # (timeline direction becomes more visible)
    if i > 0 and i < n - 1:
        cur = tuple(pieces[i]["grid_position"])
        prev = tuple(pieces[i - 1]["grid_position"])
        nxt = tuple(pieces[i + 1]["grid_position"])
        if direction_from_to(cur, prev) == direction_from_to(cur, nxt):
            kinds[direction_from_to(cur, nxt)] = "tab"

    return kinds


def polygon_xy(points: List[Point]) -> Tuple[List[float], List[float]]:
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return xs, ys
