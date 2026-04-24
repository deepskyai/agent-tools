#!/usr/bin/env python3
"""
PET (Point of Equal Time) and PSR (Point of Safe Return).

PET — the point along a route between A and B where the time to return to A
equals the time to continue to B. Used for diversion planning (medical, depress,
engine-out). PET depends only on distance and groundspeeds, not on fuel.

  D_pet_from_A   = D_total · GS_home / (GS_out + GS_home)
  T_pet_from_A   = D_pet_from_A / GS_out

Where:
  GS_out   = groundspeed continuing toward B
  GS_home  = groundspeed returning toward A (usually different due to wind)

PSR — the furthest point from A you can fly and still return to A within your
fuel endurance (excluding final reserve).

  D_psr_from_A   = E · GS_out · GS_home / (GS_out + GS_home)
  T_psr_from_A   = D_psr_from_A / GS_out
  T_home_from_psr = D_psr_from_A / GS_home

Where E is the total usable endurance (hours) — i.e. flight time available
for the out-and-back, after deducting reserves.
"""

from __future__ import annotations

import argparse
import json
import sys


def pet(distance_nm: float, gs_out: float, gs_home: float) -> dict:
    d_from_a = distance_nm * gs_home / (gs_out + gs_home)
    return {
        "distance_from_departure_nm": d_from_a,
        "distance_from_destination_nm": distance_nm - d_from_a,
        "time_from_departure_min": 60.0 * d_from_a / gs_out,
    }


def psr(endurance_hr: float, gs_out: float, gs_home: float) -> dict:
    d_from_a = endurance_hr * gs_out * gs_home / (gs_out + gs_home)
    return {
        "distance_from_departure_nm": d_from_a,
        "time_out_min": 60.0 * d_from_a / gs_out,
        "time_home_min": 60.0 * d_from_a / gs_home,
        "endurance_used_hr": d_from_a / gs_out + d_from_a / gs_home,
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="PET (Point of Equal Time) and PSR (Point of Safe Return).",
        epilog=(
            "Examples:\n"
            "  # PET only: 2200 NM, GS out 460 kt, GS home 420 kt (headwinds home)\n"
            "  pet_psr.py --distance-nm 2200 --gs-out 460 --gs-home 420 --pretty\n\n"
            "  # PSR only: 6.5 hr usable endurance, symmetric 450 kt\n"
            "  pet_psr.py --endurance-hr 6.5 --gs-out 450 --gs-home 450 --pretty\n\n"
            "  # Both at once\n"
            "  pet_psr.py --distance-nm 2200 --endurance-hr 5.8 \\\n"
            "             --gs-out 460 --gs-home 420 --pretty\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--distance-nm", type=float, help="Total route distance A→B (for PET)")
    p.add_argument("--endurance-hr", type=float,
                   help="Usable endurance after reserves, in hours (for PSR)")
    p.add_argument("--gs-out", type=float, required=True, help="GS outbound toward B, kt")
    p.add_argument("--gs-home", type=float, required=True, help="GS returning to A, kt")
    p.add_argument("--pretty", action="store_true")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.distance_nm is None and args.endurance_hr is None:
        print("Supply --distance-nm (for PET) and/or --endurance-hr (for PSR).",
              file=sys.stderr)
        return 2

    out = {
        "inputs": {
            "distance_nm": args.distance_nm,
            "endurance_hr": args.endurance_hr,
            "gs_out_kt": args.gs_out,
            "gs_home_kt": args.gs_home,
        }
    }
    if args.distance_nm is not None:
        out["pet"] = pet(args.distance_nm, args.gs_out, args.gs_home)
    if args.endurance_hr is not None:
        out["psr"] = psr(args.endurance_hr, args.gs_out, args.gs_home)

    if args.pretty:
        print(f"GS out {args.gs_out:.0f} kt   GS home {args.gs_home:.0f} kt")
        if "pet" in out:
            pet_d = out["pet"]
            print(f"\nPET")
            print(f"  From departure : {pet_d['distance_from_departure_nm']:>7.1f} NM  "
                  f"({pet_d['time_from_departure_min']:.1f} min)")
            print(f"  To destination : {pet_d['distance_from_destination_nm']:>7.1f} NM")
        if "psr" in out:
            psr_d = out["psr"]
            print(f"\nPSR")
            print(f"  From departure : {psr_d['distance_from_departure_nm']:>7.1f} NM")
            print(f"  Time out       : {psr_d['time_out_min']:>7.1f} min")
            print(f"  Time home      : {psr_d['time_home_min']:>7.1f} min")
    else:
        print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
