#!/usr/bin/env python3
"""
Fuel uplift reconciliation for Jet A / Jet A-1.

Compares the mass actually delivered (volume × density) against the mass the
crew requested, and flags discrepancies exceeding a tolerance (default 3%).

Why 3%? Jet A-1 specific gravity at 15 °C varies across the industry spec
(ASTM D1655 / DEF STAN 91-091): typically 0.775–0.840, with 0.800 as the
common nominal. That ±3% band around 0.800 is the classic "fuel SG 3% rule".
If the mass you received differs from what you ordered by more than ~3%, the
most likely culprits are: wrong SG applied, wrong unit (L vs USG), cold-fuel
volume correction missed, or an actual short-fuel condition.

Inputs (at least one pair of {mass, volume} and an SG required):
  --expected-mass-kg / --expected-mass-lbs
  --volume-L         / --volume-usg
  --sg-15c           Specific gravity at 15 °C (from the fuel ticket). Defaults to 0.800.
  --fuel-temp-c      Fuel temperature in Celsius at uplift. Defaults to 15 °C.
  --tolerance-pct    Pass/fail threshold. Defaults to 3.0.

Output: JSON with actual mass, expected vs actual delta, and a PASS/FAIL flag.
Use --pretty for a human-readable summary.

Temperature correction:
  Approximate volumetric expansion coefficient for Jet A-1 ≈ 0.00070 kg/L per °C.
  SG_at_temp = SG_15C - 0.00070 * (fuel_temp_C - 15).
  This is a linear approximation of ASTM D1250 and is accurate to ~0.1%
  for fuel temperatures within ±30 °C of 15 °C.
"""

from __future__ import annotations

import argparse
import json
import sys

L_PER_USG = 3.785411784
KG_PER_LB = 0.45359237
JETA1_THERMAL_COEF_KG_PER_L_PER_C = 0.00070
NOMINAL_SG = 0.800


def sg_at_temp(sg_15c: float, fuel_temp_c: float) -> float:
    """Correct SG from the reference 15 °C to the fuel's actual temperature."""
    return sg_15c - JETA1_THERMAL_COEF_KG_PER_L_PER_C * (fuel_temp_c - 15.0)


def reconcile(
    expected_mass_kg: float,
    volume_L: float,
    sg_15c: float = NOMINAL_SG,
    fuel_temp_c: float = 15.0,
    tolerance_pct: float = 3.0,
) -> dict:
    """
    Compute actual mass uplifted and compare to the mass ordered.

    Returns a dict with every relevant figure in both metric and imperial,
    plus a boolean `within_tolerance` flag.
    """
    sg_eff = sg_at_temp(sg_15c, fuel_temp_c)
    actual_mass_kg = volume_L * sg_eff
    diff_kg = actual_mass_kg - expected_mass_kg
    diff_pct = (100.0 * diff_kg / expected_mass_kg) if expected_mass_kg else float("nan")
    expected_volume_L = expected_mass_kg / sg_eff

    return {
        "inputs": {
            "expected_mass_kg": expected_mass_kg,
            "expected_mass_lbs": expected_mass_kg / KG_PER_LB,
            "actual_volume_L": volume_L,
            "actual_volume_usg": volume_L / L_PER_USG,
            "sg_15c": sg_15c,
            "fuel_temp_c": fuel_temp_c,
            "tolerance_pct": tolerance_pct,
        },
        "sg_effective": sg_eff,
        "actual_mass": {
            "kg": actual_mass_kg,
            "lbs": actual_mass_kg / KG_PER_LB,
        },
        "expected_volume": {
            "L": expected_volume_L,
            "usg": expected_volume_L / L_PER_USG,
        },
        "discrepancy": {
            "kg": diff_kg,
            "lbs": diff_kg / KG_PER_LB,
            "pct": diff_pct,
        },
        "within_tolerance": abs(diff_pct) <= tolerance_pct,
        "verdict": "PASS" if abs(diff_pct) <= tolerance_pct else "FAIL",
    }


def pretty(r: dict) -> str:
    i = r["inputs"]
    am = r["actual_mass"]
    ev = r["expected_volume"]
    dc = r["discrepancy"]
    lines = [
        "Fuel Uplift Reconciliation",
        "=" * 36,
        f"  SG @ 15 °C        {i['sg_15c']:.4f}",
        f"  Fuel temp         {i['fuel_temp_c']:.1f} °C",
        f"  SG @ fuel temp    {r['sg_effective']:.4f}",
        "",
        f"  Ordered mass      {i['expected_mass_kg']:>10.1f} kg   ({i['expected_mass_lbs']:.1f} lbs)",
        f"  Expected volume   {ev['L']:>10.1f} L    ({ev['usg']:.1f} USG)",
        "",
        f"  Actual volume     {i['actual_volume_L']:>10.1f} L    ({i['actual_volume_usg']:.1f} USG)",
        f"  Actual mass       {am['kg']:>10.1f} kg   ({am['lbs']:.1f} lbs)",
        "",
        f"  Δ mass            {dc['kg']:>+10.1f} kg   ({dc['lbs']:+.1f} lbs)",
        f"  Δ mass            {dc['pct']:>+10.2f} %",
        f"  Tolerance         ±{i['tolerance_pct']:.1f} %",
        "",
        f"  Verdict           {r['verdict']}",
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Jet A-1 fuel uplift reconciliation (3% SG rule).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Ordered 12 000 kg, ticket shows 15 200 L @ SG 0.794, temp 22 °C\n"
            "  fuel_uplift.py --expected-mass-kg 12000 --volume-L 15200 \\\n"
            "                 --sg-15c 0.794 --fuel-temp-c 22\n\n"
            "  # Same in imperial — ordered 26 455 lbs, 4016 USG, SG unknown (use default 0.80)\n"
            "  fuel_uplift.py --expected-mass-lbs 26455 --volume-usg 4016\n"
        ),
    )
    mass = p.add_mutually_exclusive_group(required=True)
    mass.add_argument("--expected-mass-kg",  type=float)
    mass.add_argument("--expected-mass-lbs", type=float)

    vol = p.add_mutually_exclusive_group(required=True)
    vol.add_argument("--volume-L",   type=float)
    vol.add_argument("--volume-usg", type=float)

    p.add_argument("--sg-15c",        type=float, default=NOMINAL_SG,
                   help=f"SG at 15 °C from the fuel ticket (default {NOMINAL_SG})")
    p.add_argument("--fuel-temp-c",   type=float, default=15.0,
                   help="Fuel temperature in °C at uplift (default 15)")
    p.add_argument("--tolerance-pct", type=float, default=3.0,
                   help="Pass/fail threshold in percent (default 3)")
    p.add_argument("--pretty", action="store_true",
                   help="Human-readable output instead of JSON")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    mass_kg = (args.expected_mass_kg
               if args.expected_mass_kg is not None
               else args.expected_mass_lbs * KG_PER_LB)
    vol_L = (args.volume_L
             if args.volume_L is not None
             else args.volume_usg * L_PER_USG)

    result = reconcile(
        expected_mass_kg=mass_kg,
        volume_L=vol_L,
        sg_15c=args.sg_15c,
        fuel_temp_c=args.fuel_temp_c,
        tolerance_pct=args.tolerance_pct,
    )

    if args.pretty:
        print(pretty(result))
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
