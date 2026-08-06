#!/usr/bin/env python3
"""Sync placeholder glyphs into font/Bravura.ufo for every glyph the spec
defines (data/ranges/*.yaml, via metadata/glyphnames.json and
metadata/font-optional-codepoints.json) that doesn't yet exist in the UFO -
base glyphs, stylistic alternates, and ligatures.

Adding a glyph to the spec should always mean an empty, correctly-named,
correctly-encoded glyph shows up in Bravura.ufo, ready for a font designer
to draw in FontLab - this closes the gap between "defined in the spec" and
"has a slot in the reference font".

New glyphs are inserted surgically (one new .glif file each, plus new
entries appended into glyphs/contents.plist) rather than round-tripping the
whole UFO through a library such as ufoLib2/defcon - those reformat every
file in the UFO on save (confirmed empirically), which would bury real
changes in an unreviewable diff across a file FontLab itself owns.

Usage:
    python3 tools/sync_ufo_glyphs.py [--check]

    --check   don't write anything; exit non-zero if the UFO is missing
              any glyphs the spec defines (for CI)
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate  # tools/generate.py

from fontTools.ufoLib.filenames import userNameToFileName

ROOT = Path(__file__).resolve().parent.parent
UFO_DIR = ROOT / "font" / "Bravura.ufo"
GLYPHS_DIR = UFO_DIR / "glyphs"
CONTENTS_PATH = GLYPHS_DIR / "contents.plist"

GLIF_TEMPLATE = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<glyph name="{name}" format="2">\n'
    '  <advance width="0"/>\n'
    '  <unicode hex="{hex}"/>\n'
    "  <note>{note}</note>\n"
    "</glyph>\n"
)


def xml_escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def load_contents():
    """Returns (raw_text, [(name, filename), ...]) in file order, parsed
    without going through plistlib so re-emitting untouched entries stays
    byte-identical to what FontLab wrote."""
    text = CONTENTS_PATH.read_text()
    entries = []
    lines = text.split("\n")
    i = 0
    while i < len(lines) - 1:
        line = lines[i]
        if line.startswith("  <key>") and line.endswith("</key>"):
            name = line[len("  <key>"):-len("</key>")]
            next_line = lines[i + 1]
            filename = next_line[len("  <string>"):-len("</string>")]
            entries.append((name, filename))
            i += 2
        else:
            i += 1
    return text, entries


def build_font_glyph_index():
    sources = generate.Sources()
    merged_glyphnames, _, _ = generate.merge_metadata(sources)
    return generate.build_font_glyph_index(sources, merged_glyphnames)


def add_glyphs(missing, index, text, entries):
    entries_by_name = dict(entries)
    existing_filenames = {filename for _, filename in entries}

    added = []
    for name in sorted(missing):
        info = index[name]
        filename = userNameToFileName(name, existing=existing_filenames, suffix=".glif")
        existing_filenames.add(filename)
        glif = GLIF_TEMPLATE.format(
            name=name, hex=f"{info['codepoint']:04X}", note=xml_escape(info["name"])
        )
        (GLYPHS_DIR / filename).write_text(glif)
        entries_by_name[name] = filename
        added.append((name, filename))

    header = text.split("<dict>\n", 1)[0] + "<dict>\n"
    body = "".join(
        f"  <key>{name}</key>\n  <string>{entries_by_name[name]}</string>\n"
        for name in sorted(entries_by_name)
    )
    CONTENTS_PATH.write_text(header + body + "</dict>\n</plist>\n")
    return added


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    index = build_font_glyph_index()
    text, entries = load_contents()
    existing_names = {name for name, _ in entries}
    missing = sorted(n for n in index if n not in existing_names)

    if args.check:
        if missing:
            print(f"{len(missing)} glyph(s) defined in the spec are missing from Bravura.ufo:")
            for name in missing:
                print(f"  {name}  ({index[name]['name']})")
            print("\nRun `python3 tools/sync_ufo_glyphs.py` to add placeholder glyphs.")
            return 1
        print("OK - Bravura.ufo has a glyph for everything the spec defines")
        return 0

    if not missing:
        print("Nothing to do - Bravura.ufo already has a glyph for everything the spec defines")
        return 0

    added = add_glyphs(missing, index, text, entries)
    print(f"Added {len(added)} placeholder glyph(s) to Bravura.ufo:")
    for name, filename in added:
        print(f"  {name} -> glyphs/{filename}  ({index[name]['name']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
