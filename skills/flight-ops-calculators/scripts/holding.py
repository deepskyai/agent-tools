#!/usr/bin/env python3
"""
Holding-pattern entry type solver (direct / parallel / teardrop).

Given the inbound holding course, your aircraft heading at the fix, and the
turn direction of the hold (right is standard), returns which of the three
standard entries applies.

Sector rules (70° wedges either side of the outbound leg)
---------------------------------------------------------
Let θ = (aircraft_heading − inbound_course) mod 360.

Right-turn holding (standard):
  Parallel  : 110° < θ ≤ 180°    (70° wedge on non-hold side of outbound)
  Teardrop  : 180° < θ < 250°    (70° wedge on hold side of outbound)
  Direct    : elsewhere          (180° arc)

Left-turn holding (non-standard):
  mirror of the above — Parallel ↔ Teardrop sectors swap.

Reference: FAA AIM 5-3-8.
"""

from __future__ import annotations

import argparse
import json
import sys


def entry(inbound_course_deg: float, heading_deg: float, turn: str = "right") -> dict:
    turn = turn.lower().strip()
    if turn not in ("right", "left"):
        raise ValueError("turn must be 'right' or 'left'")

    rel = (heading_deg - inbound_course_deg) % 360.0
    outbound = (inbound_course_deg + 180.0) % 360.0

    if turn == "right":
        if 110.0 < rel < 180.0:
            name = "teardrop"
        elif 180.0 <= rel < 250.0:
            name = "parallel"
        else:
            name = "direct"
    else:  # left (mirror)
        if 110.0 < rel < 180.0:
            name = "parallel"
        elif 180.0 <= rel < 250.0:
            name = "teardrop"
        else:
            name = "direct"

    return {
        "inbound_course_deg": inbound_course_deg,
        "outbound_course_deg": outbound,
        "aircraft_heading_deg": heading_deg,
        "turn_direction": turn,
        "relative_angle_deg": rel,
        "entry": name,
        "description": {
            "direct":   "Cross fix, turn in the hold direction onto the outbound leg.",
            "parallel": "Cross fix, turn OPPOSITE the hold direction to parallel the "
                        "outbound course for one minute, then turn back through "
                        ">180° to intercept the inbound.",
            "teardrop": "Cross fix, turn in the hold direction to a heading offset "
                        "≤30° from outbound (on the hold side), fly one minute, "
                        "then turn back to intercept inbound.",
        }[name],
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Holding-pattern entry type (direct / parallel / teardrop).",
        epilog=(
            "Examples:\n"
            "  # Holding on inbound 270°, standard right turns, arriving heading 120°\n"
            "  holding.py --inbound 270 --heading 120\n\n"
            "  # Non-standard left-turn hold, inbound 180°, heading 060°\n"
            "  holding.py --inbound 180 --heading 060 --turn left --pretty\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--inbound", type=float, required=True,
                   help="Inbound holding course, °T (direction flown TO the fix)")
    p.add_argument("--heading", type=float, required=True,
                   help="Aircraft heading at the fix, °T")
    p.add_argument("--turn", choices=["right", "left"], default="right",
                   help="Turn direction (default: right / standard)")
    p.add_argument("--pretty", action="store_true")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    r = entry(args.inbound, args.heading, args.turn)
    if args.pretty:
        print(f"Inbound {r['inbound_course_deg']:.0f}°   Outbound {r['outbound_course_deg']:.0f}°   "
              f"({r['turn_direction']} turns)")
        print(f"Arriving heading {r['aircraft_heading_deg']:.0f}°   "
              f"(θ = {r['relative_angle_deg']:.0f}°)")
        print()
        print(f"  ENTRY: {r['entry'].upper()}")
        print(f"  {r['description']}")
    else:
        print(json.dumps(r, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
