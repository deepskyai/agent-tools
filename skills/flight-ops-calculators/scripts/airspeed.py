#!/usr/bin/env python3
"""
Airspeed conversions: CAS ↔ TAS ↔ Mach  (subsonic, troposphere).

Supply any one airspeed plus pressure altitude and temperature (OAT or ISA
deviation); the script reports CAS, TAS, EAS, Mach, and the speed of sound.

Conventions & formulas (ICAO standard atmosphere, troposphere ≤ 36 089 ft)
-------------------------------------------------------------------------
  T_isa(h)   = 288.15 − 0.0019812·h_ft                          (Kelvin)
  T(h)       = T_isa(h) + ΔISA                                  (if OAT not given)
  P/P0       = (1 − 6.87559e-6·h_ft)^5.2561                     (pressure ratio δ)
  σ          = δ·(288.15/T)                                     (density ratio)
  a_kts      = 38.967854·√T_K                                   (speed of sound)
  EAS        = CAS  (compressibility correction <1% under M 0.5; ignored)
  TAS        = EAS / √σ
  Mach       = TAS / a_kts
"""

from __future__ import annotations

import argparse
import json
import math
import sys

T0_K = 288.15
LAPSE_K_PER_FT = 0.0019812
P_EXP = 5.2561


def isa_temp_k(pa_ft: float) -> float:
    return T0_K - LAPSE_K_PER_FT * pa_ft


def pressure_ratio(pa_ft: float) -> float:
    return (1.0 - 6.87559e-6 * pa_ft) ** P_EXP


def sigma(pa_ft: float, t_k: float) -> float:
    return pressure_ratio(pa_ft) * T0_K / t_k


def a_sound_kt(t_k: float) -> float:
    return 38.967854 * math.sqrt(t_k)


def convert(
    pa_ft: float,
    cas_kt: float = None,
    tas_kt: float = None,
    mach: float = None,
    oat_c: float = None,
    isa_dev_c: float = 0.0,
):
    t_isa = isa_temp_k(pa_ft)
    t_k = (oat_c + 273.15) if oat_c is not None else (t_isa + isa_dev_c)
    sig = sigma(pa_ft, t_k)
    a = a_sound_kt(t_k)
    sqrt_sig = math.sqrt(sig)

    if cas_kt is not None:
        tas = cas_kt / sqrt_sig
        m = tas / a
    elif tas_kt is not None:
        tas = tas_kt
        cas_kt = tas * sqrt_sig
        m = tas / a
    elif mach is not None:
        tas = mach * a
        cas_kt = tas * sqrt_sig
        m = mach
    else:
        raise ValueError("Supply one of --cas-kt, --tas-kt, --mach.")

    return {
        "inputs": {
            "pressure_altitude_ft": pa_ft,
            "oat_c": oat_c,
            "isa_dev_c": isa_dev_c if oat_c is None else (t_k - t_isa),
            "temperature_k": t_k,
            "temperature_c": t_k - 273.15,
        },
        "sigma": sig,
        "speed_of_sound_kt": a,
        "cas_kt": cas_kt,
        "eas_kt": cas_kt,
        "tas_kt": tas,
        "mach": m,
    }


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="CAS / TAS / Mach conversions (subsonic, troposphere).",
        epilog=(
            "Examples:\n"
            "  # IAS 250 at FL100, ISA  → TAS & Mach\n"
            "  airspeed.py --cas-kt 250 --pa-ft 10000 --pretty\n\n"
            "  # M0.78 at FL370 ISA+10 → TAS\n"
            "  airspeed.py --mach 0.78 --pa-ft 37000 --isa-dev 10 --pretty\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--pa-ft", type=float, required=True, help="Pressure altitude, ft")
    temp = p.add_mutually_exclusive_group()
    temp.add_argument("--oat-c", type=float, help="Outside air temperature, °C")
    temp.add_argument("--isa-dev", type=float, default=None, help="ISA deviation, °C")
    speed = p.add_mutually_exclusive_group(required=True)
    speed.add_argument("--cas-kt", type=float, help="Calibrated airspeed (≈IAS), kt")
    speed.add_argument("--tas-kt", type=float, help="True airspeed, kt")
    speed.add_argument("--mach", type=float, help="Mach number")
    p.add_argument("--pretty", action="store_true")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    isa_dev = args.isa_dev if args.isa_dev is not None else 0.0
    result = convert(
        pa_ft=args.pa_ft,
        cas_kt=args.cas_kt,
        tas_kt=args.tas_kt,
        mach=args.mach,
        oat_c=args.oat_c,
        isa_dev_c=isa_dev,
    )
    if args.pretty:
        i = result["inputs"]
        print(f"PA {i['pressure_altitude_ft']:,.0f} ft   "
              f"T {i['temperature_c']:+.1f} °C   σ {result['sigma']:.4f}   "
              f"a {result['speed_of_sound_kt']:.1f} kt")
        print()
        print(f"  CAS / EAS   {result['cas_kt']:>7.1f} kt")
        print(f"  TAS         {result['tas_kt']:>7.1f} kt")
        print(f"  Mach        {result['mach']:>7.3f}")
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
