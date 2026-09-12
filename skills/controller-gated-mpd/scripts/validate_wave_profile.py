#!/usr/bin/env python3
"""Validate an Adaptive-native CG-MPD V6 wave profile."""
from __future__ import annotations

import argparse
import sys

from policy import PolicyError, load_profile, risk_gate_ids


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("profile")
    args = parser.parse_args()
    try:
        _, data = load_profile(args.profile)
    except PolicyError as exc:
        print(f"PROFILE INVALID: {exc}", file=sys.stderr)
        return 2
    levels = "/".join(str(len(risk_gate_ids(data, level))) for level in ("FAST", "STANDARD", "CRITICAL"))
    transport = data["adaptive"]["transport"]
    print(f"PROFILE OK: {data['wave']} ({len(data['lanes'])} lanes, risk gates FAST/STANDARD/CRITICAL={levels}, transport={transport})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
