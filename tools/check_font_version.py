#!/usr/bin/env python3
"""Enforces that data/font-version.yaml's build number gets incremented
whenever the font's actual build inputs change - see that file for the
versioning scheme.

Usage:
    python3 tools/check_font_version.py [--check | --update]

    --check   (default) exit non-zero if the build inputs have changed
              since inputsHash was last recorded, without a version bump
              to go with it. For CI.
    --update  recompute and record inputsHash for the CURRENT build
              inputs and CURRENT version number - run this locally after
              you've made a material change AND incremented build (or
              changed stem) in data/font-version.yaml.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import font_version


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--update", action="store_true")
    args = parser.parse_args()

    data = font_version.load()
    current_hash = font_version.compute_inputs_hash()
    _, _, version = font_version.format_version(data)

    if args.update:
        data["inputsHash"] = current_hash
        font_version.save(data)
        print(f"Recorded inputsHash for version {version}")
        return 0

    if not data["inputsHash"]:
        print("error: data/font-version.yaml has no inputsHash recorded yet - "
              "run `python3 tools/check_font_version.py --update` once to set a baseline",
              file=sys.stderr)
        return 1

    if current_hash != data["inputsHash"]:
        print(f"error: font build inputs (font/Bravura.ufo, engraving defaults, "
              f"stylistic sets, etc.) have changed since version {version} was recorded, "
              f"but data/font-version.yaml wasn't updated to match.\n\n"
              f"If this is a material change (new/edited outlines, anchors, kerning, "
              f"hinting, engraving defaults, or anything that affects the compiled "
              f"font's content): increment 'build' (or bump 'stem' if SMuFL 1.5 has "
              f"shipped) in data/font-version.yaml, then run:\n"
              f"  python3 tools/check_font_version.py --update\n\n"
              f"If this was NOT a material change (e.g. only a re-export with no real "
              f"difference), figure out what triggered the hash change before ignoring "
              f"this - see tools/font_version.py's HASH_INPUTS list for what's covered.",
              file=sys.stderr)
        return 1

    print(f"OK - version {version} matches recorded build inputs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
