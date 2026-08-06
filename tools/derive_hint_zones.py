#!/usr/bin/env python3
"""Derive PostScript hinting zone/stem-snap parameters (BlueValues,
OtherBlues, StemSnapH, StemSnapV) for fontinfo.plist, from the per-glyph
hint data FontLab already computed and stored in each glyph's
public.postscript.hints lib key.

Rationale: FontLab's UFO export carries real per-glyph stem hints (hstem/
vstem position+width pairs), but not the font-level summary zone/stem-snap
arrays that psautohint requires to operate at all. This script recovers a
reasonable approximation of those font-level values by finding which
Y-positions (for horizontal stems) and widths (for both) recur most often
across the whole font - i.e. reverse-engineering the shared "design grid"
FontLab's own hinting evidently converged on, from its aggregate output.

This is a heuristic, not a guarantee of matching FontLab's actual internal
zone model - it should be reviewed, not trusted blindly. It reports its
reasoning (frequency tables) rather than just asserting an answer.

Usage:
    python3 tools/derive_hint_zones.py <path-to-UFO> [--write]

Without --write, only reports the analysis. --write updates fontinfo.plist.
"""
import argparse
import glob
import os
import plistlib
import re
import sys
from collections import Counter

STEM_RE = re.compile(r"^(hstem|vstem)\s+(-?\d+(?:\.\d+)?)\s+(-?\d+(?:\.\d+)?)$")


def iter_glyph_stems(ufo_path):
    """Yields (glyph_name, kind, pos, width) for every stem hint found."""
    glyphs_dir = os.path.join(ufo_path, "glyphs")
    for glif_path in glob.glob(os.path.join(glyphs_dir, "*.glif")):
        with open(glif_path, "rb") as f:
            content = f.read()
        # Extract the lib plist fragment manually - glif files embed a
        # <lib><dict>...</dict></lib> block that's itself valid plist XML
        # once wrapped, so we can reuse plistlib rather than write an XML
        # parser here.
        start = content.find(b"<lib>")
        end = content.find(b"</lib>")
        if start == -1 or end == -1:
            continue
        lib_xml = content[start + len(b"<lib>"):end].strip()
        wrapped = (
            b'<?xml version="1.0" encoding="UTF-8"?>\n'
            b'<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
            b'"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            b'<plist version="1.0">\n' + lib_xml + b"\n</plist>"
        )
        try:
            lib = plistlib.loads(wrapped)
        except Exception:
            continue
        hints = lib.get("public.postscript.hints")
        if not hints:
            continue
        glyph_name = os.path.splitext(os.path.basename(glif_path))[0]
        for hint_set in hints.get("hintSetList", []):
            for stem_str in hint_set.get("stems", []):
                m = STEM_RE.match(stem_str.strip())
                if not m:
                    continue
                kind, pos, width = m.group(1), float(m.group(2)), float(m.group(3))
                yield glyph_name, kind, pos, width


def top_n_by_frequency(counter, n, min_count=1):
    return [(val, count) for val, count in counter.most_common() if count >= min_count][:n]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ufo_path")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--blue-zones", type=int, default=4,
                         help="Number of BlueValues zone pairs to derive (default 4, i.e. 8 values)")
    parser.add_argument("--stem-snaps", type=int, default=6,
                         help="Number of stem-snap widths to keep per axis (default 6)")
    args = parser.parse_args()

    hstem_positions = Counter()
    hstem_widths = Counter()
    vstem_widths = Counter()
    glyphs_with_hints = set()

    for glyph_name, kind, pos, width in iter_glyph_stems(args.ufo_path):
        glyphs_with_hints.add(glyph_name)
        if kind == "hstem":
            hstem_positions[pos] += 1
            hstem_positions[round(pos + width, 2)] += 1  # top edge of the stem too
            hstem_widths[abs(width)] += 1
        else:
            vstem_widths[abs(width)] += 1

    print(f"Glyphs with hint data: {len(glyphs_with_hints)}")
    print(f"Distinct hstem edge Y-positions seen: {len(hstem_positions)}")
    print(f"Distinct hstem widths seen: {len(hstem_widths)}")
    print(f"Distinct vstem widths seen: {len(vstem_widths)}")

    print("\n=== Most common hstem edge Y-positions (candidate blue zones) ===")
    top_positions = top_n_by_frequency(hstem_positions, 20)
    for val, count in top_positions:
        print(f"  y={val:>8}  seen {count} times")

    print("\n=== Most common hstem widths (candidate StemSnapH) ===")
    top_hwidths = top_n_by_frequency(hstem_widths, args.stem_snaps)
    for val, count in top_hwidths:
        print(f"  width={val:>6}  seen {count} times")

    print("\n=== Most common vstem widths (candidate StemSnapV) ===")
    top_vwidths = top_n_by_frequency(vstem_widths, args.stem_snaps)
    for val, count in top_vwidths:
        print(f"  width={val:>6}  seen {count} times")

    # --- Derive BlueValues: pick the most frequent Y-positions, pair each
    # with itself as a zero-width zone (min bottom/top pair), sorted.
    # This preserves whatever meaningful shared reference lines exist in
    # the data, without inventing an overshoot tolerance we have no basis
    # for (real overshoot values need outline-shape analysis, not just
    # stem edge frequency - flagged in the summary as a known limitation).
    chosen_positions = sorted(v for v, _ in top_positions[:args.blue_zones])
    blue_values = []
    for v in chosen_positions:
        blue_values.extend([v, v])

    stem_snap_h = sorted(v for v, _ in top_hwidths)
    stem_snap_v = sorted(v for v, _ in top_vwidths)

    print("\n=== Derived values ===")
    print(f"postscriptBlueValues: {blue_values}")
    print(f"postscriptStemSnapH: {stem_snap_h}")
    print(f"postscriptStemSnapV: {stem_snap_v}")

    if not args.write:
        print("\nDry run - pass --write to update fontinfo.plist")
        return 0

    fontinfo_path = os.path.join(args.ufo_path, "fontinfo.plist")
    with open(fontinfo_path, "rb") as f:
        fontinfo = plistlib.load(f)

    fontinfo["postscriptBlueValues"] = blue_values
    fontinfo["postscriptStemSnapH"] = stem_snap_h
    fontinfo["postscriptStemSnapV"] = stem_snap_v

    with open(fontinfo_path, "wb") as f:
        plistlib.dump(fontinfo, f)

    print(f"\nWrote {fontinfo_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
