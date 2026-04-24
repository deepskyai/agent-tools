#!/usr/bin/env python3
"""
Headwind / crosswind component solver.

Given the reported wind (direction, speed) and the runway you're using,
computes headwind and crosswind components.

Conventions
-----------
- Wind direction is the direction the wind is coming FROM (°T).
- Runway heading can be given as a magnetic runway number (e.g. 27, 09L)
  which will be multiplied by 10, OR as a full heading in degrees.
- Headwind: positive = headwind, negative = tailwind.
- Crosswind: positive = from the right, negative = from the left.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys


def parse_runway(token: str) -> float:
    """Accept '27', '09L', '27R', '270', or '273.4' and return degrees."""
    m = re.match(r"^\s*(\d+(?:\.\d+)?)\s*[LRClrc]?\s*$", token)
    if not m:
        raise ValueError(f"Unrecognised runway token: {token!r}")
    val = float(m.group(1))
    if val < 37:
        val *= 10.0
    return val % 360.0


def components(wind_dir_deg: float, wind_speed_kt: float, runway_heading_deg: float):
    """
    Return (headwind_kt, crosswind_kt).

    Positive headwind = headwind. Positive crosswind = from the right of the runway.
    """
    angle_deg = (wind_dir_deg - runway_heading_deg + 540.0) % 360.0 - 180.0
    angle_rad = math.radians(angle_deg)
    head = wind_speed_kt * math.cos(angle_rad)
    cross = wind_speed_kt * math.sin(angle_rad)
    return head, cross, angle_deg


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Headwind / crosswind component solver.",
        epilog=(
            "Examples:\n"
            "  wind_components.py --wind-from 210 --wind-kt 18 --runway 27\n"
            "  wind_components.py --wind-from 050 --wind-kt 25 --runway 09L --pretty\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--wind-from", type=float, required=True,
                   help="Wind direction (°T), i.e. direction wind is coming FROM")
    p.add_argument("--wind-kt", type=float, required=True, help="Wind speed, knots")
    p.add_argument("--runway", type=str, required=True,
                   help="Runway number (e.g. 27, 09L) or full heading (e.g. 273)")
    p.add_argument("--pretty", action="store_true")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    rwy = parse_runway(args.runway)
    head, cross, rel = components(args.wind_from, args.wind_kt, rwy)
    out = {
        "inputs": {
            "wind_from_deg": args.wind_from,
            "wind_speed_kt": args.wind_kt,
            "runway": args.runway,
            "runway_heading_deg": rwy,
        },
        "relative_wind_angle_deg": rel,
        "headwind_kt": head,
        "tailwind_kt": -head if head < 0 else 0.0,
        "crosswind_kt": cross,
        "crosswind_direction": "from right" if cross >= 0 else "from left",
    }
    if args.pretty:
        label = "HEADWIND" if head >= 0 else "TAILWIND"
        xdir = "from RIGHT" if cross >= 0 else "from LEFT"
        print(f"Wind {args.wind_from:.0f}° @ {args.wind_kt:.0f} kt — Runway heading {rwy:.0f}°")
        print(f"  {label}  {abs(head):.1f} kt")
        print(f"  Crosswind {abs(cross):.1f} kt {xdir}")
        print(f"  Relative wind angle: {rel:+.1f}°")
    else:
        print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
