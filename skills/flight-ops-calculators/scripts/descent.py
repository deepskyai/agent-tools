#!/usr/bin/env python3
"""
Top-of-Descent planner (3-to-1 rule + speed-brake / deceleration tax).

Pure rule-of-thumb planning for airliners:
  • Base TOD  = altitude_to_lose / 1000 × 3     (the "3× rule" ≈ 3° path)
  • Speed tax = (current_speed − target_speed) / 10   NM of level flight to decelerate
  • Wind tax  = (headwind_kt / 10) NM  added,  or subtracted for tailwind
  • Ice/anti-ice tax: extra NM you want for a flatter buffer (default 0)

Outputs recommended TOD distance, with each contribution itemised so the crew
can see where the numbers come from.

No compressibility, idle thrust or aircraft-specific modelling — this is the
same math you do in your head on approach. For precise descent profiles use
the FMS.
"""

from __future__ import annotations

import argparse
import json
import sys


def plan(
    current_alt_ft: float,
    target_alt_ft: float,
    current_speed_kt: float = None,
    target_speed_kt: float = None,
    headwind_kt: float = 0.0,
    extra_buffer_nm: float = 0.0,
    slope_per_1000ft: float = 3.0,
) -> dict:
    altitude_to_lose = current_alt_ft - target_alt_ft
    base_nm = altitude_to_lose / 1000.0 * slope_per_1000ft
    speed_nm = 0.0
    if current_speed_kt is not None and target_speed_kt is not None:
        speed_nm = max(0.0, (current_speed_kt - target_speed_kt) / 10.0)
    wind_nm = headwind_kt / 10.0
    total = base_nm + speed_nm + wind_nm + extra_buffer_nm

    return {
        "inputs": {
            "current_alt_ft": current_alt_ft,
            "target_alt_ft": target_alt_ft,
            "current_speed_kt": current_speed_kt,
            "target_speed_kt": target_speed_kt,
            "headwind_kt": headwind_kt,
            "extra_buffer_nm": extra_buffer_nm,
            "slope_per_1000ft": slope_per_1000ft,
        },
        "altitude_to_lose_ft": altitude_to_lose,
        "base_3x_nm": base_nm,
        "speed_reduction_nm": speed_nm,
        "wind_correction_nm": wind_nm,
        "recommended_tod_nm": total,
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Top-of-Descent rule-of-thumb planner (3× rule + speed/wind tax).",
        epilog=(
            "Examples:\n"
            "  # FL370 → 2000 ft, slow from M0.78 (≈290 KIAS) to 250 KIAS, 20 kt HW\n"
            "  descent.py --current-alt 37000 --target-alt 2000 \\\n"
            "             --current-speed 290 --target-speed 250 --headwind 20 --pretty\n\n"
            "  # Just the bare 3× rule: FL350 to SL\n"
            "  descent.py --current-alt 35000 --target-alt 0 --pretty\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--current-alt", type=float, required=True, help="Current altitude, ft")
    p.add_argument("--target-alt", type=float, required=True, help="Target altitude, ft")
    p.add_argument("--current-speed", type=float, help="Current speed (KIAS or KTAS)")
    p.add_argument("--target-speed", type=float, help="Target speed")
    p.add_argument("--headwind", type=float, default=0.0,
                   help="Net headwind component along descent, kt (negative for tailwind)")
    p.add_argument("--buffer-nm", type=float, default=0.0,
                   help="Additional NM cushion (anti-ice, turbulence, etc.)")
    p.add_argument("--slope", type=float, default=3.0,
                   help="NM per 1000 ft of altitude (default 3; use 2.5 for shallower)")
    p.add_argument("--pretty", action="store_true")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    r = plan(
        current_alt_ft=args.current_alt,
        target_alt_ft=args.target_alt,
        current_speed_kt=args.current_speed,
        target_speed_kt=args.target_speed,
        headwind_kt=args.headwind,
        extra_buffer_nm=args.buffer_nm,
        slope_per_1000ft=args.slope,
    )
    if args.pretty:
        print(f"Descent  {args.current_alt:,.0f} → {args.target_alt:,.0f} ft  "
              f"({r['altitude_to_lose_ft']:,.0f} ft to lose)")
        print()
        print(f"  Base ({args.slope:g}× rule) : {r['base_3x_nm']:>6.1f} NM")
        print(f"  Speed reduction    : {r['speed_reduction_nm']:>6.1f} NM")
        print(f"  Wind correction    : {r['wind_correction_nm']:>+6.1f} NM")
        print(f"  Extra buffer       : {args.buffer_nm:>6.1f} NM")
        print(f"  ─────────────────────────────")
        print(f"  Recommended TOD    : {r['recommended_tod_nm']:>6.1f} NM before target")
    else:
        print(json.dumps(r, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
