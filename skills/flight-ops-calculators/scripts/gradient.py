#!/usr/bin/env python3
"""
Flexible climb/descent gradient solver.

Supply any sufficient subset of the following; the script solves for the rest.

  --distance-nm          Horizontal distance (nautical miles)
  --time-min             Time along the path (minutes)
  --gs-kt                Ground speed (knots)
  --altitude-ft          Altitude change (feet). Positive = climb, negative = descent.
  --rate-fpm             Rate of climb/descent (feet per minute). Sign matches altitude.
  --angle-deg            Flight path angle (degrees above/below horizontal)
  --gradient-pct         Gradient as percentage (rise/run * 100)
  --gradient-ft-per-nm   Gradient as feet per nautical mile

Relationships used:
  distance_nm          = gs_kt * time_min / 60
  altitude_ft          = rate_fpm * time_min
  gradient_ft_per_nm   = altitude_ft / distance_nm
  gradient_pct         = 100 * altitude_ft / (distance_nm * 6076.11549)
  angle_deg            = degrees(atan(gradient_pct / 100))
  rate_fpm             = gradient_pct/100 * gs_kt * 6076.11549 / 60
                       (the classic "ROC = GS * gradient" relationship)

Output: JSON (default) with all solvable variables + metric/imperial mirrors.
Use --pretty for a human-readable table.
"""

from __future__ import annotations

import argparse
import json
import math
import sys

FT_PER_NM = 6076.11549
EPS = 1e-9


def _both(*vals) -> bool:
    """True when every value is not None."""
    return all(v is not None for v in vals)


def solve(
    d=None, t=None, gs=None,
    h=None, r=None,
    ang=None, pct=None, fpnm=None,
):
    """
    Iteratively propagate the six relationships until no new variable can be solved.

    Parameters
    ----------
    d    : distance_nm
    t    : time_min
    gs   : gs_kt
    h    : altitude_ft  (signed: + climb, - descent)
    r    : rate_fpm     (signed: + climb, - descent)
    ang  : angle_deg    (signed)
    pct  : gradient_pct (signed)
    fpnm : gradient_ft_per_nm (signed)
    """
    changed = True
    guard = 0
    while changed and guard < 20:
        changed = False
        guard += 1

        # 1) distance = GS * time / 60
        if _both(gs, t) and d is None:
            d = gs * t / 60.0; changed = True
        elif _both(d, t) and gs is None and abs(t) > EPS:
            gs = d * 60.0 / t; changed = True
        elif _both(d, gs) and t is None and abs(gs) > EPS:
            t = d * 60.0 / gs; changed = True

        # 2) altitude = rate * time
        if _both(r, t) and h is None:
            h = r * t; changed = True
        elif _both(h, t) and r is None and abs(t) > EPS:
            r = h / t; changed = True
        elif _both(h, r) and t is None and abs(r) > EPS:
            t = h / r; changed = True

        # 3) gradient_pct from altitude & distance
        if _both(h, d) and pct is None and abs(d) > EPS:
            pct = 100.0 * h / (d * FT_PER_NM); changed = True
        elif _both(pct, d) and h is None:
            h = pct / 100.0 * d * FT_PER_NM; changed = True
        elif _both(pct, h) and d is None and abs(pct) > EPS:
            d = 100.0 * h / (pct * FT_PER_NM); changed = True

        # 4) ft_per_nm from altitude & distance
        if _both(h, d) and fpnm is None and abs(d) > EPS:
            fpnm = h / d; changed = True
        elif _both(fpnm, d) and h is None:
            h = fpnm * d; changed = True
        elif _both(fpnm, h) and d is None and abs(fpnm) > EPS:
            d = h / fpnm; changed = True

        # 5) pct <-> ft_per_nm  (linear conversion)
        if pct is not None and fpnm is None:
            fpnm = pct * FT_PER_NM / 100.0; changed = True
        elif fpnm is not None and pct is None:
            pct = fpnm * 100.0 / FT_PER_NM; changed = True

        # 6) angle <-> pct
        if pct is not None and ang is None:
            ang = math.degrees(math.atan(pct / 100.0)); changed = True
        elif ang is not None and pct is None:
            pct = 100.0 * math.tan(math.radians(ang)); changed = True

        # 7) ROC from gradient & GS   (r_fpm = pct/100 * gs_kt * FT_PER_NM / 60)
        if _both(gs, pct) and r is None:
            r = pct / 100.0 * gs * FT_PER_NM / 60.0; changed = True
        elif _both(r, pct) and gs is None and abs(pct) > EPS:
            gs = r * 100.0 * 60.0 / (pct * FT_PER_NM); changed = True
        elif _both(r, gs) and pct is None and abs(gs) > EPS:
            pct = r * 100.0 * 60.0 / (gs * FT_PER_NM); changed = True

    return {
        "distance_nm": d,
        "time_min": t,
        "gs_kt": gs,
        "altitude_ft": h,
        "rate_fpm": r,
        "angle_deg": ang,
        "gradient_pct": pct,
        "gradient_ft_per_nm": fpnm,
    }


def add_unit_mirrors(result: dict) -> dict:
    """Attach metric equivalents so the output shows both systems."""
    if result["distance_nm"] is not None:
        result["distance_km"] = result["distance_nm"] * 1.852
    if result["altitude_ft"] is not None:
        result["altitude_m"] = result["altitude_ft"] * 0.3048
    if result["gs_kt"] is not None:
        result["gs_kmh"] = result["gs_kt"] * 1.852
    if result["rate_fpm"] is not None:
        result["rate_mps"] = result["rate_fpm"] * 0.00508
    if result["time_min"] is not None:
        result["time_sec"] = result["time_min"] * 60.0
    return result


def pretty(result: dict) -> str:
    rows = [
        ("Distance",      result.get("distance_nm"),        "NM", result.get("distance_km"),  "km"),
        ("Time",          result.get("time_min"),           "min", result.get("time_sec"),    "s"),
        ("Ground speed",  result.get("gs_kt"),              "kt", result.get("gs_kmh"),       "km/h"),
        ("Altitude Δ",    result.get("altitude_ft"),        "ft", result.get("altitude_m"),   "m"),
        ("Rate",          result.get("rate_fpm"),           "fpm", result.get("rate_mps"),    "m/s"),
        ("Angle",         result.get("angle_deg"),          "°",  None, None),
        ("Gradient",      result.get("gradient_pct"),       "%",  None, None),
        ("Gradient",      result.get("gradient_ft_per_nm"), "ft/NM", None, None),
    ]
    out = []
    for label, v1, u1, v2, u2 in rows:
        if v1 is None:
            out.append(f"  {label:<14}  —")
        elif v2 is None:
            out.append(f"  {label:<14}  {v1:>10.3f} {u1}")
        else:
            out.append(f"  {label:<14}  {v1:>10.3f} {u1}   ({v2:.3f} {u2})")
    unsolved = [k for k, v in result.items() if v is None and not k.startswith("_")]
    footer = "" if not unsolved else f"\n  Unsolved: {', '.join(unsolved)}"
    return "\n".join(out) + footer


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Flexible climb/descent gradient solver.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Required climb gradient check: crossed a fix 5 NM out needing 1500 ft clearance, GS 140\n"
            "  gradient.py --distance-nm 5 --altitude-ft 1500 --gs-kt 140\n\n"
            "  # 3:1 descent from 10 000 ft, GS 250\n"
            "  gradient.py --altitude-ft -10000 --gradient-ft-per-nm -333 --gs-kt 250\n\n"
            "  # ROC required for 5% gradient at GS 180\n"
            "  gradient.py --gradient-pct 5 --gs-kt 180\n"
        ),
    )
    p.add_argument("--distance-nm",        type=float)
    p.add_argument("--time-min",           type=float)
    p.add_argument("--gs-kt",              type=float)
    p.add_argument("--altitude-ft",        type=float, help="Signed: + climb, - descent")
    p.add_argument("--rate-fpm",           type=float, help="Signed: + climb, - descent")
    p.add_argument("--angle-deg",          type=float)
    p.add_argument("--gradient-pct",       type=float)
    p.add_argument("--gradient-ft-per-nm", type=float)
    p.add_argument("--pretty", action="store_true",
                   help="Human-readable output instead of JSON")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    result = solve(
        d=args.distance_nm, t=args.time_min, gs=args.gs_kt,
        h=args.altitude_ft, r=args.rate_fpm,
        ang=args.angle_deg, pct=args.gradient_pct, fpnm=args.gradient_ft_per_nm,
    )
    result = add_unit_mirrors(result)
    result["_unsolved"] = [
        k for k in
        ("distance_nm", "time_min", "gs_kt", "altitude_ft",
         "rate_fpm", "angle_deg", "gradient_pct", "gradient_ft_per_nm")
        if result.get(k) is None
    ]
    if args.pretty:
        print(pretty(result))
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
