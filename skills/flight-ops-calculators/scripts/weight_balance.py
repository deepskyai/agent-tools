#!/usr/bin/env python3
"""
Generic Weight & Balance + CG calculator.

You provide a list of stations (name, weight, arm); the script sums weight and
moment and returns the CG arm. Optionally you can supply a forward/aft CG limit
pair (either as arms or as %MAC, with MAC length + LEMAC) and the script will
report whether CG is in-limits and the remaining margin.

Unit system is up to you — as long as weights and arms are internally
consistent. The script doesn't convert units.

Station inputs
--------------
Option 1 — CLI, repeat --station with "name:weight:arm":
  weight_balance.py --station "BEW:42000:21.5" --station "Crew:400:10.2" ...

Option 2 — JSON file:
  weight_balance.py --json wb.json
  where wb.json is:
    {
      "stations": [
        {"name": "BEW",   "weight": 42000, "arm": 21.5},
        {"name": "Crew",  "weight":   400, "arm": 10.2},
        {"name": "Pax",   "weight":  8400, "arm": 20.0},
        {"name": "Cargo", "weight":  3200, "arm": 28.1},
        {"name": "Fuel",  "weight":  9000, "arm": 19.7}
      ],
      "cg_limit_fwd": 18.5,
      "cg_limit_aft": 24.0,
      "max_weight":   62000
    }

CG in %MAC
----------
If --mac-length and --lemac are supplied, output also includes CG as %MAC:
   %MAC = 100 × (cg_arm − LEMAC) / MAC_length
"""

from __future__ import annotations

import argparse
import json
import sys


def parse_station(spec: str) -> dict:
    parts = spec.split(":")
    if len(parts) != 3:
        raise ValueError(f"Station must be name:weight:arm, got {spec!r}")
    name, w, a = parts
    return {"name": name.strip(), "weight": float(w), "arm": float(a)}


def compute(
    stations: list,
    cg_limit_fwd: float = None,
    cg_limit_aft: float = None,
    max_weight: float = None,
    mac_length: float = None,
    lemac: float = None,
) -> dict:
    total_w = sum(s["weight"] for s in stations)
    total_m = sum(s["weight"] * s["arm"] for s in stations)
    cg = total_m / total_w if total_w else float("nan")

    out = {
        "stations": [
            {**s, "moment": s["weight"] * s["arm"]} for s in stations
        ],
        "total_weight": total_w,
        "total_moment": total_m,
        "cg_arm": cg,
    }
    if mac_length is not None and lemac is not None:
        out["cg_pct_mac"] = 100.0 * (cg - lemac) / mac_length
    if cg_limit_fwd is not None and cg_limit_aft is not None:
        in_lim = cg_limit_fwd <= cg <= cg_limit_aft
        out["cg_limits"] = {
            "forward": cg_limit_fwd,
            "aft": cg_limit_aft,
            "within_limits": in_lim,
            "margin_fwd": cg - cg_limit_fwd,
            "margin_aft": cg_limit_aft - cg,
        }
    if max_weight is not None:
        out["weight_limits"] = {
            "max_weight": max_weight,
            "within_limits": total_w <= max_weight,
            "margin": max_weight - total_w,
        }
    return out


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Generic Weight & Balance / CG calculator.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("--station", action="append", default=[],
                   help='Station entry "name:weight:arm" (repeatable)')
    p.add_argument("--json", type=str, help="Path to JSON file with full W&B spec")
    p.add_argument("--cg-fwd", type=float, help="Forward CG limit (arm units)")
    p.add_argument("--cg-aft", type=float, help="Aft CG limit (arm units)")
    p.add_argument("--max-weight", type=float, help="Maximum allowable weight")
    p.add_argument("--mac-length", type=float, help="MAC length for %%MAC output")
    p.add_argument("--lemac", type=float,
                   help="Leading-edge MAC arm (reference) for %%MAC output")
    p.add_argument("--pretty", action="store_true")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)

    stations = [parse_station(s) for s in args.station]
    cfg = {
        "cg_limit_fwd": args.cg_fwd,
        "cg_limit_aft": args.cg_aft,
        "max_weight": args.max_weight,
        "mac_length": args.mac_length,
        "lemac": args.lemac,
    }
    if args.json:
        with open(args.json) as f:
            data = json.load(f)
        stations.extend(data.get("stations", []))
        for k in cfg:
            if cfg[k] is None and k in data:
                cfg[k] = data[k]

    if not stations:
        print("No stations provided. Use --station or --json.", file=sys.stderr)
        return 2

    result = compute(stations, **cfg)

    if args.pretty:
        print(f"{'Station':<20}{'Weight':>12}{'Arm':>10}{'Moment':>14}")
        print("─" * 56)
        for s in result["stations"]:
            print(f"{s['name']:<20}{s['weight']:>12,.1f}{s['arm']:>10.2f}{s['moment']:>14,.1f}")
        print("─" * 56)
        print(f"{'TOTAL':<20}{result['total_weight']:>12,.1f}"
              f"{'':>10}{result['total_moment']:>14,.1f}")
        print(f"\nCG arm       : {result['cg_arm']:.3f}")
        if "cg_pct_mac" in result:
            print(f"CG %MAC      : {result['cg_pct_mac']:.2f}%")
        if "cg_limits" in result:
            c = result["cg_limits"]
            tag = "IN LIMITS" if c["within_limits"] else "OUT OF LIMITS"
            print(f"CG limits    : {c['forward']}..{c['aft']}   →   {tag}")
            print(f"  margin fwd : {c['margin_fwd']:+.3f}")
            print(f"  margin aft : {c['margin_aft']:+.3f}")
        if "weight_limits" in result:
            w = result["weight_limits"]
            tag = "OK" if w["within_limits"] else "OVERWEIGHT"
            print(f"Max weight   : {w['max_weight']:,.1f}   ({tag}, margin {w['margin']:+,.1f})")
    else:
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
