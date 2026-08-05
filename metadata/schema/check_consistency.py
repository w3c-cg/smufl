#!/usr/bin/env python3
"""Cross-file consistency checks for the SMuFL metadata files.

These are checks that a JSON Schema alone can't express: relationships
between glyphnames.json, ranges.json and classes.json. Run after schema
validation has already passed.
"""
import json
import sys
from pathlib import Path

METADATA_DIR = Path(__file__).resolve().parent.parent


def codepoint_to_int(codepoint):
    return int(codepoint[2:], 16)


def main():
    errors = []

    glyphnames = json.loads((METADATA_DIR / "glyphnames.json").read_text())
    ranges = json.loads((METADATA_DIR / "ranges.json").read_text())
    classes = json.loads((METADATA_DIR / "classes.json").read_text())

    # Every glyph referenced by a range must exist in glyphnames.json, and
    # its codepoint must fall within that range's start/end.
    glyphs_in_ranges = set()
    for range_name, range_data in ranges.items():
        range_start = codepoint_to_int(range_data["range_start"])
        range_end = codepoint_to_int(range_data["range_end"])
        if range_start > range_end:
            errors.append(
                f"ranges.json: '{range_name}' has range_start after range_end"
            )
        for glyph_name in range_data["glyphs"]:
            glyphs_in_ranges.add(glyph_name)
            glyph = glyphnames.get(glyph_name)
            if glyph is None:
                errors.append(
                    f"ranges.json: '{range_name}' references unknown glyph '{glyph_name}'"
                )
                continue
            codepoint = codepoint_to_int(glyph["codepoint"])
            if not (range_start <= codepoint <= range_end):
                errors.append(
                    f"ranges.json: '{glyph_name}' codepoint {glyph['codepoint']} "
                    f"is outside range '{range_name}' "
                    f"({range_data['range_start']}-{range_data['range_end']})"
                )

    # Every glyph in glyphnames.json should belong to exactly one range.
    for glyph_name in glyphnames:
        if glyph_name not in glyphs_in_ranges:
            errors.append(
                f"glyphnames.json: '{glyph_name}' is not a member of any range in ranges.json"
            )

    # No two glyphs should share a codepoint.
    codepoints_seen = {}
    for glyph_name, glyph in glyphnames.items():
        codepoint = glyph["codepoint"]
        if codepoint in codepoints_seen:
            errors.append(
                f"glyphnames.json: codepoint {codepoint} is used by both "
                f"'{codepoints_seen[codepoint]}' and '{glyph_name}'"
            )
        else:
            codepoints_seen[codepoint] = glyph_name

    # Every glyph referenced by a class must exist in glyphnames.json.
    for class_name, glyph_list in classes.items():
        for glyph_name in glyph_list:
            if glyph_name not in glyphnames:
                errors.append(
                    f"classes.json: '{class_name}' references unknown glyph '{glyph_name}'"
                )

    if errors:
        print(f"Found {len(errors)} consistency error(s):\n", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print(f"ok -- {len(glyphnames)} glyphs, {len(ranges)} ranges, {len(classes)} classes consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
