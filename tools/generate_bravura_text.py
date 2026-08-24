#!/usr/bin/env python3
"""Build Bravura Text from Bravura - a text-flow font that repurposes
Bravura's glyphs at sizes/positions suited to being set inline with running
text, rather than for full music engraving.

This replaces the old smufl-admin FontLab/Glyphs/UFO conversion script
templates (fontlab_scripts/create_text_font_*.py in the smufl-admin repo).
The transform rules those scripts hardcoded per-class (as a long if/elif
chain, populated by hand at export time from the admin database) now live
in data/bravura-text-transforms.yaml; everything else - which glyphs make
up each class, which glyphs combine with which staff-position markers - is
read from the same metadata/generate.py index the rest of this pipeline
already uses.

The single largest piece of what this script does is generating the
"combining staff position" ligatures: every glyph in the combiningStaffPositions
class (noteheads, leger lines, etc.) combined with each of the 16 staff
position markers (data/ranges/combining-staff-positions.yaml), each as its
own glyph with a GSUB `liga` substitution AND a direct codepoint. That's
~972 x 16 =~ 15,500 new glyphs - see
https://github.com/steinbergmedia/bravura/issues/101: these used to
overflow past the end of the Basic Multilingual Plane's Private Use Area
(U+F8FF) into normal Unicode allocations, which is why they now start at
U+F0000 (Plane 15, Supplementary Private Use Area-A) instead.

Codepoints for these ligatures are assigned by deterministic enumeration
(base glyphs sorted by codepoint, markers in a fixed Raise1-8/Lower1-8
order) rather than recorded in a baseline file - see the PR description
for why. This means a newly-added combiningStaffPositions member always
gets its ligatures appended after all existing ones, keeping previously
published codepoints stable, PROVIDED the enumeration order here is never
changed and new members are only ever added with higher codepoints than
uses of the same base range (true under SMuFL's normal codepoint-immutable
allocation model, just not mechanically enforced).

Also classifies every ligature glyph (the newly-generated ones and
Bravura's own native ones, which pass through unchanged) for GDEF, and
adds a dummy DSIG table after compiling - see tools/generate_font.py and
tools/font_build_common.py for why.

Usage:
    python3 tools/generate_bravura_text.py [--output PATH] [--keep-tmp]
"""
import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate  # tools/generate.py
import font_version  # tools/font_version.py
import font_build_common  # tools/font_build_common.py

import ufoLib2
import yaml
from fontTools.ttLib import TTFont
from ufo2ft.filters.decomposeComponents import DecomposeComponentsFilter

ROOT = Path(__file__).resolve().parent.parent
UFO_DIR = ROOT / "font" / "Bravura.ufo"
DEFAULT_OUTPUT = ROOT / "font" / "BravuraText.woff"

LIGATURE_CODEPOINT_START = 0xF0000
MARKER_ORDER = [f"staffPosRaise{n}" for n in range(1, 9)] + [f"staffPosLower{n}" for n in range(1, 9)]

TEXT_METRICS = {
    "ascender": 800, "descender": -200, "capHeight": 720, "xHeight": 470,
    "openTypeOS2TypoAscender": 800, "openTypeOS2TypoDescender": -200, "openTypeOS2TypoLineGap": 200,
    "openTypeOS2WinAscent": 1130, "openTypeOS2WinDescent": 330,
    "openTypeHheaAscender": 1130, "openTypeHheaDescender": -330, "openTypeHheaLineGap": 0,
}


def uni_name(codepoint):
    return f"uni{codepoint:04X}" if codepoint <= 0xFFFF else f"u{codepoint:04X}"


def load_transforms():
    return yaml.safe_load((ROOT / "data" / "bravura-text-transforms.yaml").read_text())


def load_markers():
    """Returns {marker_name: codepoint} for the 16 staff-position markers,
    in MARKER_ORDER."""
    range_data = yaml.safe_load((ROOT / "data" / "ranges" / "combining-staff-positions.yaml").read_text())
    start = generate.cp_int(range_data["codepointRangeStart"])
    codepoints = {g["name"]: start + i for i, g in enumerate(range_data["glyphs"])}
    return {name: codepoints[name] for name in MARKER_ORDER}


def build_scale_and_shift_maps(transforms, classes_by_glyph, index):
    """Returns (scale_by_ufo_name, shift_by_ufo_name, zero_width_ufo_names,
    unicode_scale, unicode_shift) - the last two keyed by raw codepoint for
    the special-cased standard Unicode music symbols."""
    scale_by_name = {}
    shift_by_name = {}

    # SMuFL name -> ufo name, for base glyphs (classes.json only lists base
    # glyphs) and for alternates (needed for chordSymbols includeAlternates).
    smufl_name_to_ufo_name = {info["name"]: ufo_name for ufo_name, info in index.items()}
    alternates_by_base = {}
    for ufo_name, info in index.items():
        if info["category"] == "alternate":
            alternates_by_base.setdefault(info["for"], []).append(info["name"])

    for rule in transforms["scaleByClass"]:
        members = classes_by_glyph.get(rule["class"], [])
        for smufl_name in members:
            ufo_name = smufl_name_to_ufo_name.get(smufl_name)
            if ufo_name:
                scale_by_name[ufo_name] = rule["scale"]
            if rule.get("includeAlternates"):
                for alt_name in alternates_by_base.get(smufl_name, []):
                    alt_ufo_name = smufl_name_to_ufo_name.get(alt_name)
                    if alt_ufo_name:
                        scale_by_name[alt_ufo_name] = rule["scale"]

    for rule in transforms["shiftByClass"]:
        members = classes_by_glyph.get(rule["class"], [])
        for smufl_name in members:
            ufo_name = smufl_name_to_ufo_name.get(smufl_name)
            if ufo_name:
                shift_by_name[ufo_name] = rule["shiftY"]

    zero_width_names = {
        smufl_name_to_ufo_name[n]
        for n in classes_by_glyph.get(transforms["zeroWidthClass"], [])
        if n in smufl_name_to_ufo_name
    }
    # A Bravura ligature composed of a zero-width component is itself
    # zero-width in Bravura Text (matches the old smufl-admin behaviour).
    zero_width_smufl_names = set(classes_by_glyph.get(transforms["zeroWidthClass"], []))
    for ufo_name, info in index.items():
        if info["category"] == "ligature" and zero_width_smufl_names & set(info["components"]):
            zero_width_names.add(ufo_name)

    unicode_scale = {}
    unicode_shift = {}
    for rule in transforms["unicodeSymbols"]:
        for cp in rule["codepoints"]:
            if "scale" in rule:
                unicode_scale[cp] = rule["scale"]
            if "shiftY" in rule:
                unicode_shift[cp] = rule["shiftY"]

    return scale_by_name, shift_by_name, zero_width_names, unicode_scale, unicode_shift


def scale_glyph(glyph, scale):
    if scale == 1.0:
        return
    for contour in glyph.contours:
        for point in contour.points:
            point.x *= scale
            point.y *= scale


def shift_glyph(glyph, shift_y):
    if not shift_y:
        return
    for contour in glyph.contours:
        for point in contour.points:
            point.y += shift_y


def transform_glyphs(font, transforms, classes_by_glyph, index):
    print("Decomposing components")
    DecomposeComponentsFilter()(font)

    scale_by_name, shift_by_name, zero_width_names, unicode_scale, unicode_shift = \
        build_scale_and_shift_maps(transforms, classes_by_glyph, index)
    default_scale = transforms["defaultScale"]

    print("Scaling, resizing and shifting glyphs")
    for glyph in font:
        glyph.clearAnchors()  # not meaningful for a text-flow font

        codepoint = glyph.unicode
        if codepoint in unicode_scale:
            scale = unicode_scale[codepoint]
        else:
            scale = scale_by_name.get(glyph.name, default_scale)
        scale_glyph(glyph, scale)

        if glyph.name in zero_width_names:
            glyph.width = 0
        elif glyph.contours:
            bounds = glyph.getBounds(font)
            if bounds is not None:
                # Fitting width to the bbox's right edge (matching the old
                # smufl-admin scripts) can go negative for a narrow glyph
                # whose outline sits entirely left of the origin (seen on
                # u1D19E, a legacy SMuFL Supplementary-Plane duplicate
                # implemented as a component shifted -108 in x) - clamp
                # rather than emit an invalid negative advance width.
                glyph.width = max(0, bounds.xMax)

        if codepoint in unicode_shift:
            shift_glyph(glyph, unicode_shift[codepoint])
        elif glyph.name in shift_by_name:
            shift_glyph(glyph, shift_by_name[glyph.name])


def generate_ligatures(font, classes_by_glyph, merged_glyphnames, markers):
    print("Generating combining staff position ligatures")
    base_names = sorted(
        classes_by_glyph.get("combiningStaffPositions", []),
        key=lambda n: generate.cp_int(merged_glyphnames[n]["codepoint"]),
    )

    substitutions = []
    new_ligature_names = []
    codepoint = LIGATURE_CODEPOINT_START
    for base_name in base_names:
        base_cp = generate.cp_int(merged_glyphnames[base_name]["codepoint"])
        base_ufo_name = uni_name(base_cp)
        if base_ufo_name not in font:
            continue
        base_width = font[base_ufo_name].width

        for marker_name, marker_cp in markers.items():
            marker_ufo_name = uni_name(marker_cp)
            offset = int(marker_name[-1]) * 100
            if "Lower" in marker_name:
                offset = -offset

            lig_name = f"{marker_cp:04X}_{base_cp:04X}"
            lig_glyph = font.newGlyph(lig_name)
            lig_glyph.unicode = codepoint
            lig_glyph.note = f"{base_name} with {marker_name}"
            lig_glyph.width = base_width
            lig_glyph.components.append(
                ufoLib2.objects.Component(baseGlyph=base_ufo_name, transformation=(1, 0, 0, 1, 0, offset))
            )

            substitutions.append(f"  sub {marker_ufo_name} {base_ufo_name} by {lig_name}; # {base_name} with {marker_name}")
            new_ligature_names.append(lig_name)
            codepoint += 1

    print(f"Created {len(substitutions)} ligature glyphs (U+{LIGATURE_CODEPOINT_START:X}-U+{codepoint - 1:X})")
    return substitutions, new_ligature_names


def build_liga_feature(substitutions):
    """Splits into multiple lookups if a single subtable would get too
    large for some feature compilers to handle in one go (48000 chars/
    subtable - matches the limit the old smufl-admin scripts used)."""
    lines = ["feature liga {"]
    subtable_idx = 1
    subtable_len = 0
    lines.append(f"  lookup liga_{subtable_idx} useExtension {{")
    for sub in substitutions:
        if subtable_len > 48000:
            lines.append(f"  }} liga_{subtable_idx};")
            subtable_idx += 1
            subtable_len = 0
            lines.append(f"  lookup liga_{subtable_idx} useExtension {{")
        lines.append(sub)
        subtable_len += len(sub)
    lines.append(f"  }} liga_{subtable_idx};")
    lines.append("} liga;")
    return "\n".join(lines)


def rename_font(font, base_family):
    text_family = f"{base_family} Text"
    font.info.familyName = text_family
    font.info.openTypeNamePreferredFamilyName = text_family
    font.info.postscriptFontName = text_family.replace(" ", "")
    font.info.postscriptFullName = text_family
    font.info.styleMapFamilyName = text_family
    for attr, value in TEXT_METRICS.items():
        setattr(font.info, attr, value)
    font_version.set_ufo_version(font)
    font_version.set_ufo_copyright_year(font)


def odds_and_sods(font):
    font["space"].width = 100
    hyphen = font.newGlyph("hyphen")
    hyphen.unicode = 0x2D
    hyphen.width = 200
    equal = font.newGlyph("equal")
    equal.unicode = 0x3D
    equal.width = 400


def run(cmd, **kwargs):
    print(f"$ {' '.join(str(c) for c in cmd)}")
    subprocess.run(cmd, check=True, **kwargs)


def relpath(path):
    return path.relative_to(ROOT) if path.is_relative_to(ROOT) else path


def build_otf(tmp_dir):
    """Builds BravuraText.otf into tmp_dir and returns its path. Doesn't
    manage tmp_dir's lifecycle - the caller owns cleanup, since
    tools/generate_release.py needs the working directory to stick around
    afterwards to derive SVG/WOFF/WOFF2 from the same compile."""
    sources = generate.Sources()
    merged_glyphnames, _, merged_classes = generate.merge_metadata(sources)
    index = generate.build_font_glyph_index(sources, merged_glyphnames)
    classes_by_glyph = {}
    for class_name, members in merged_classes.items():
        for m in members:
            classes_by_glyph.setdefault(class_name, []).append(m)

    transforms = load_transforms()
    markers = load_markers()

    print(f"Opening {UFO_DIR}")
    font = ufoLib2.Font.open(UFO_DIR)
    base_family = font.info.familyName

    transform_glyphs(font, transforms, classes_by_glyph, index)
    substitutions, new_ligature_names = generate_ligatures(font, classes_by_glyph, merged_glyphnames, markers)
    liga_feature = build_liga_feature(substitutions)
    font.features.text = (font.features.text or "") + "\n\n" + liga_feature

    rename_font(font, base_family)
    odds_and_sods(font)

    # GDEF ligature classification - not something FontLab's export carries
    # (same reasoning as tools/generate_font.py), covering both the newly
    # generated combining-staff-position ligatures and Bravura's own native
    # ligatures (which pass through into Bravura Text unchanged).
    native_ligature_names = {ufo_name for ufo_name, info in index.items() if info["category"] == "ligature"}
    all_ligature_names = set(new_ligature_names) | native_ligature_names
    font.lib["public.openTypeCategories"] = {n: "ligature" for n in all_ligature_names if n in font}
    print(f"Classified {len(font.lib['public.openTypeCategories'])} ligature glyph(s) for GDEF")

    working_ufo = tmp_dir / "BravuraText.ufo"
    print(f"Saving working UFO to {working_ufo} ({len(font)} glyphs)")
    font.save(working_ufo)

    otf_path = tmp_dir / "BravuraText.otf"
    run(["fontmake", "-u", str(working_ufo), "-o", "otf", "--output-path", str(otf_path), "--no-subroutinize"])

    ttfont = TTFont(otf_path)
    font_build_common.add_dummy_dsig(ttfont)
    ttfont.save(otf_path)
    print("Added DSIG table")

    return otf_path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--keep-tmp", action="store_true")
    args = parser.parse_args()

    if not UFO_DIR.exists():
        print(f"error: {UFO_DIR} not found", file=sys.stderr)
        return 1

    tmp_dir = Path(tempfile.mkdtemp(prefix="bravura-text-build-"))
    try:
        otf_path = build_otf(tmp_dir)

        args.output.parent.mkdir(parents=True, exist_ok=True)
        suffix = args.output.suffix.lower()
        if suffix in (".woff", ".woff2"):
            flavor = suffix.lstrip(".")
            print(f"Converting to {flavor.upper()}")
            ttfont = TTFont(otf_path)
            ttfont.flavor = flavor
            ttfont.save(args.output)
        else:
            shutil.copy(otf_path, args.output)

        print(f"\nWrote {relpath(args.output)}")
        return 0
    finally:
        if args.keep_tmp:
            print(f"(kept working directory: {tmp_dir})")
        else:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
