#!/usr/bin/env python3
"""
EDTO / ETOPS diversion-radius calculator.

Given the authorised diversion time and a one-engine-inoperative (OEI) cruise
TAS, returns the maximum diversion distance ("ETOPS circle" radius):

  D_still_air     = (threshold_min / 60) × OEI_TAS_kt
  D_with_headwind = (threshold_min / 60) × (OEI_TAS_kt − headwind_kt)

Typical ETOPS thresholds (FAA / EASA):
  60 / 75 / 90 / 120 / 138 / 180 / 207 / 240 / ≥ 300 minutes

Note: this is the still-air / constant-wind geometric radius only.
Operational ETOPS planning layers on equal-time-point analysis, fuel reserves,
decompression scenarios, and the specific aircraft's OEI drift-down profile.
For a single quick radius during dispatch review or route planning, this is
enough.
"""

from __future__ import annotations

import argparse
import json
import sys


def diversion_radius(threshold_min: float, oei_tas_kt: float,
                     headwind_kt: float = 0.0) -> dict:
    hrs = threshold_min / 60.0
    still = hrs * oei_tas_kt
    effective = hrs * (oei_tas_kt - headwind_kt)
    return {
        "threshold_min": threshold_min,
        "oei_tas_kt": oei_tas_kt,
        "headwind_kt": headwind_kt,
        "diversion_radius_still_air_nm": still,
        "effective_gs_kt": oei_tas_kt - headwind_kt,
        "diversion_radius_with_wind_nm": effective,
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="EDTO / ETOPS diversion-radius calculator.",
        epilog=(
            "Examples:\n"
            "  # ETOPS 180 with 400 kt OEI TAS, no wind\n"
            "  etops.py --threshold-min 180 --oei-tas 400 --pretty\n\n"
            "  # ETOPS 240 with 35 kt HW component on worst leg\n"
            "  etops.py --threshold-min 240 --oei-tas 410 --headwind 35 --pretty\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--threshold-min", type=float, required=True,
                   help="Authorised diversion time, minutes")
    p.add_argument("--oei-tas", type=float, required=True,
                   help="One-engine-inoperative cruise TAS, kt")
    p.add_argument("--headwind", type=float, default=0.0,
                   help="Mean headwind component on diversion leg, kt")
    p.add_argument("--pretty", action="store_true")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    r = diversion_radius(args.threshold_min, args.oei_tas, args.headwind)
    if args.pretty:
        print(f"Threshold   : {r['threshold_min']:.0f} min")
        print(f"OEI TAS     : {r['oei_tas_kt']:.0f} kt")
        print(f"Headwind    : {r['headwind_kt']:+.0f} kt")
        print()
        print(f"Still-air radius  : {r['diversion_radius_still_air_nm']:,.0f} NM")
        print(f"With headwind     : {r['diversion_radius_with_wind_nm']:,.0f} NM   "
              f"(GS {r['effective_gs_kt']:.0f} kt)")
    else:
        print(json.dumps(r, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
