#!/usr/bin/env python3
"""
Pressure altitude, density altitude and ISA-deviation calculator.

Given field (or indicated) elevation, altimeter setting (QNH) and outside air
temperature, computes:
  - Pressure altitude (PA)
  - ISA standard temperature at PA
  - ISA deviation (OAT − ISA_at_PA)
  - Density altitude (DA)

Formulas
--------
  PA_ft  = elevation_ft + (1013.25 − QNH_hPa) × 30              (≈ pilot rule)
         or exact: PA_ft = elevation_ft
                  + (1 − (QNH_hPa/1013.25) ** 0.190284) × 145366.45
  ISA_C  = 15 − 1.98 × (PA_ft / 1000)                           (troposphere)
  ΔISA   = OAT_C − ISA_C
  DA_ft  = PA_ft + 118.8 × ΔISA                                 (good ≤ 10 kft)
         ("118.8" from dDA/dT analysis at ISA SL; FAA uses 120 as rule-of-thumb)

QNH may be given in hPa/mb (default) or inHg (use --qnh-inhg).
"""

from __future__ import annotations

import argparse
import json
import sys

HPA_PER_INHG = 33.8638866667
ISA_SL_HPA = 1013.25
ISA_LAPSE_C_PER_1000FT = 1.98
DA_K_FT_PER_C = 118.8


def pressure_altitude(elevation_ft: float, qnh_hpa: float) -> float:
    """Exact troposphere formula."""
    return elevation_ft + (1.0 - (qnh_hpa / ISA_SL_HPA) ** 0.190284) * 145366.45


def isa_temp_c(pa_ft: float) -> float:
    return 15.0 - ISA_LAPSE_C_PER_1000FT * (pa_ft / 1000.0)


def density_altitude(pa_ft: float, oat_c: float) -> float:
    isa = isa_temp_c(pa_ft)
    return pa_ft + DA_K_FT_PER_C * (oat_c - isa)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Pressure altitude / density altitude / ISA-deviation.",
        epilog=(
            "Examples:\n"
            "  altitude.py --elevation-ft 5000 --qnh-hpa 1005 --oat-c 28 --pretty\n"
            "  altitude.py --elevation-ft 34 --qnh-inhg 29.92 --oat-c 15 --pretty\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--elevation-ft", type=float, required=True,
                   help="Field elevation (or indicated altitude) in feet")
    qnh = p.add_mutually_exclusive_group(required=True)
    qnh.add_argument("--qnh-hpa", type=float)
    qnh.add_argument("--qnh-inhg", type=float)
    p.add_argument("--oat-c", type=float, required=True,
                   help="Outside air temperature, °C")
    p.add_argument("--pretty", action="store_true")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    qnh_hpa = args.qnh_hpa if args.qnh_hpa is not None else args.qnh_inhg * HPA_PER_INHG
    pa = pressure_altitude(args.elevation_ft, qnh_hpa)
    isa = isa_temp_c(pa)
    dev = args.oat_c - isa
    da = density_altitude(pa, args.oat_c)

    out = {
        "inputs": {
            "elevation_ft": args.elevation_ft,
            "qnh_hpa": qnh_hpa,
            "qnh_inhg": qnh_hpa / HPA_PER_INHG,
            "oat_c": args.oat_c,
        },
        "pressure_altitude_ft": pa,
        "isa_temp_c_at_pa": isa,
        "isa_deviation_c": dev,
        "density_altitude_ft": da,
    }
    if args.pretty:
        print(f"Field elevation  {args.elevation_ft:,.0f} ft")
        print(f"QNH              {qnh_hpa:.2f} hPa  ({qnh_hpa / HPA_PER_INHG:.2f} inHg)")
        print(f"OAT              {args.oat_c:+.1f} °C")
        print()
        print(f"Pressure altitude {pa:>9,.0f} ft")
        print(f"ISA at PA         {isa:>+9.1f} °C")
        print(f"ISA deviation     {dev:>+9.1f} °C  (ISA{'+' if dev >= 0 else ''}{dev:.0f})")
        print(f"Density altitude  {da:>9,.0f} ft")
    else:
        print(json.dumps(out, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
