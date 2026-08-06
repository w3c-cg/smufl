#!/usr/bin/env python3
"""Generate Bravura.json - the font-specific SMuFL metadata file - from
font/Bravura.ufo, a compiled Bravura.otf, and the same spec metadata
tools/sync_ufo_glyphs.py and tools/generate_font.py already use.

Where each section comes from:

- fontName: fixed.
- fontVersion: data/font-version.yaml (see tools/font_version.py) - NOT
  font/Bravura.ufo/fontinfo.plist's own version fields, which get
  overwritten at build time anyway (see tools/generate_font.py).
- engravingDefaults: data/engraving-defaults.yaml, copied verbatim - these
  are hand-set design decisions, not something derivable from outlines.
- glyphAdvanceWidths / glyphBBoxes: measured from the *compiled* OTF (not
  the raw UFO), so components are decomposed and overlaps removed exactly
  as they will be in the shipped font. Values are in staff spaces
  (1 staff space = unitsPerEm / 4, SMuFL's standard convention).
- glyphsWithAnchors: the UFO's own <anchor> elements. These never reach the
  compiled OTF (Bravura has no GPOS mark-to-base lookups - see
  CONTRIBUTING.md), so the UFO is the only place to read them from.
- glyphsWithAlternates / ligatures / optionalGlyphs / sets: derived from
  tools/generate.py's build_font_glyph_index(), the same
  font-optional-codepoints.json-backed index tools/generate_font.py uses
  for GDEF classification.

Usage:
    python3 tools/generate_font_metadata.py <compiled.otf> [--output PATH]
"""
import argparse
import json
import plistlib
import sys
from pathlib import Path
from xml.etree import ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate  # tools/generate.py
import font_version  # tools/font_version.py

import yaml
from fontTools.pens.boundsPen import BoundsPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
UFO_DIR = ROOT / "font" / "Bravura.ufo"
GLYPHS_DIR = UFO_DIR / "glyphs"
DEFAULT_OUTPUT = ROOT / "font" / "Bravura.json"
FONT_NAME = "Bravura"


def font_info():
    fontinfo = plistlib.loads((UFO_DIR / "fontinfo.plist").read_bytes())
    staff_space = fontinfo["unitsPerEm"] / 4
    # fontVersion is a JSON number (matching the historical smufl-admin
    # export), which can't distinguish "1.4900" from "1.49" - the build
    # number's trailing zeros are only meaningful in the font's own
    # name-table "Version" string and in versionMajor/versionMinor.
    _, _, version_str = font_version.format_version()
    return staff_space, float(version_str)


def su(value, staff_space):
    """Font units -> staff spaces."""
    return round(value / staff_space, 6)


def load_ufo_contents():
    contents = plistlib.loads((GLYPHS_DIR / "contents.plist").read_bytes())
    return contents


def build_advance_widths_and_bboxes(otf_path, index, staff_space):
    font = TTFont(otf_path)
    glyph_set = font.getGlyphSet()
    hmtx = font["hmtx"]
    widths = {}
    bboxes = {}
    for ufo_name, info in index.items():
        if ufo_name not in glyph_set:
            continue
        name = info["name"]
        width = hmtx[ufo_name][0]
        widths[name] = su(width, staff_space)

        pen = BoundsPen(glyph_set)
        glyph_set[ufo_name].draw(pen)
        if pen.bounds is not None:
            xmin, ymin, xmax, ymax = pen.bounds
            bboxes[name] = {
                "bBoxNE": [su(xmax, staff_space), su(ymax, staff_space)],
                "bBoxSW": [su(xmin, staff_space), su(ymin, staff_space)],
            }
    return widths, bboxes


def build_anchors(index, staff_space):
    contents = load_ufo_contents()
    anchors_by_name = {}
    for ufo_name, info in index.items():
        filename = contents.get(ufo_name)
        if filename is None:
            continue
        glif_path = GLYPHS_DIR / filename
        root = ET.fromstring(glif_path.read_text())
        glyph_anchors = {}
        for anchor_el in root.findall("anchor"):
            anchor_name = anchor_el.get("name")
            x = float(anchor_el.get("x", "0"))
            y = float(anchor_el.get("y", "0"))
            if anchor_name:
                glyph_anchors[anchor_name] = [su(x, staff_space), su(y, staff_space)]
        if glyph_anchors:
            anchors_by_name[info["name"]] = glyph_anchors
    return anchors_by_name


def build_alternates_ligatures_optional_sets(index, classes_by_glyph, stylistic_sets_full):
    glyphs_with_alternates = {}
    ligatures = {}
    optional_glyphs = {}
    sets = {}

    set_descriptions = {s["opentype"]: s["description"] for s in stylistic_sets_full}

    for info in index.values():
        if info["category"] == "base":
            continue

        name = info["name"]
        codepoint = f"U+{info['codepoint']:04X}"

        if info["category"] == "alternate":
            base_name = info["for"]
            glyphs_with_alternates.setdefault(base_name, {"alternates": []})
            glyphs_with_alternates[base_name]["alternates"].append(
                {"codepoint": codepoint, "name": name}
            )
            optional_glyphs[name] = {
                "codepoint": codepoint,
                "description": info["description"],
            }
            optional_glyphs[name]["classes"] = sorted(classes_by_glyph.get(base_name, []))

            if info["set"]:
                tag = info["set"]
                sets.setdefault(tag, {
                    "description": set_descriptions.get(tag, tag),
                    "glyphs": [],
                })
                sets[tag]["glyphs"].append({
                    "alternateFor": base_name,
                    "codepoint": codepoint,
                    "description": info["description"],
                    "name": name,
                })

        elif info["category"] == "ligature":
            ligatures[name] = {
                "codepoint": codepoint,
                "componentGlyphs": info["components"],
                "description": info["description"],
            }
            optional_glyphs[name] = {
                "codepoint": codepoint,
                "description": info["description"],
            }

    # The old smufl-admin-era metadata gave each set a bespoke "type" slug
    # (e.g. "opticalVariantsSmall") with no equivalent in our registry -
    # data/stylistic-sets.yaml's opentype tag is used here instead.
    for tag, entry in sets.items():
        entry["type"] = tag
        entry["glyphs"].sort(key=lambda g: g["codepoint"])

    return glyphs_with_alternates, ligatures, optional_glyphs, sets


def build_metadata(otf_path):
    staff_space, font_version = font_info()
    sources = generate.Sources()
    merged_glyphnames, _, merged_classes = generate.merge_metadata(sources)
    index = generate.build_font_glyph_index(sources, merged_glyphnames)
    classes_by_glyph = {}
    for class_name, members in merged_classes.items():
        for m in members:
            classes_by_glyph.setdefault(m, []).append(class_name)

    stylistic_sets_full = yaml.safe_load((ROOT / "data" / "stylistic-sets.yaml").read_text())["sets"]
    engraving_defaults = yaml.safe_load((ROOT / "data" / "engraving-defaults.yaml").read_text())

    glyph_advance_widths, glyph_bboxes = build_advance_widths_and_bboxes(otf_path, index, staff_space)
    glyphs_with_anchors = build_anchors(index, staff_space)
    glyphs_with_alternates, ligatures, optional_glyphs, sets = build_alternates_ligatures_optional_sets(
        index, classes_by_glyph, stylistic_sets_full
    )

    return {
        "fontName": FONT_NAME,
        "fontVersion": font_version,
        "engravingDefaults": engraving_defaults,
        "glyphAdvanceWidths": glyph_advance_widths,
        "glyphBBoxes": glyph_bboxes,
        "glyphsWithAlternates": glyphs_with_alternates,
        "glyphsWithAnchors": glyphs_with_anchors,
        "ligatures": ligatures,
        "optionalGlyphs": optional_glyphs,
        "sets": sets,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("otf", type=Path, help="path to a compiled Bravura.otf")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    metadata = build_metadata(args.otf)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(metadata, indent=4, sort_keys=True))
    print(f"Wrote {args.output.relative_to(ROOT) if args.output.is_relative_to(ROOT) else args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
