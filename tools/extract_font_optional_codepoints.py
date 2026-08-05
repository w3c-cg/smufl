#!/usr/bin/env python3
"""Extract the current optional-codepoint assignments (stylistic alternates
and ligatures) from a Bravura font, using its GSUB tables as the source of
truth, and write them to metadata/font-optional-codepoints.json.

This becomes the immutability baseline for optional codepoints: once an
alternate or ligature is recorded here, its codepoint must never change.
New alternates/ligatures are appended at the next free U+F400+ slot.

Usage:
    python3 tools/extract_font_optional_codepoints.py \
        --font /path/to/Bravura.otf \
        --glyphnames metadata/glyphnames.json \
        --out metadata/font-optional-codepoints.json
"""
import argparse
import json
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

OPTIONAL_CODEPOINT_START = 0xF400


def load_name_by_codepoint(glyphnames_path):
    glyphnames = json.loads(Path(glyphnames_path).read_text())
    name_by_cp = {}
    for name, data in glyphnames.items():
        cp = int(data["codepoint"][2:], 16)
        name_by_cp[cp] = name
    return name_by_cp


def resolve(glyph_name, cp_by_glyph, name_by_cp, unresolved):
    cp = cp_by_glyph.get(glyph_name)
    if cp is None:
        unresolved.append(f"{glyph_name}: no cmap entry")
        return f"<{glyph_name}>"
    name = name_by_cp.get(cp)
    if name is None:
        unresolved.append(f"{glyph_name}: U+{cp:04X} not in glyphnames.json")
        return f"U+{cp:04X}"
    return name


def format_cp(cp):
    return f"U+{cp:04X}"


def load_extra_names(extra_names_path):
    """Load a {"U+XXXX": "glyphName"} map for glyphs the font already has but
    that haven't been added to metadata/glyphnames.json yet (e.g. a new range
    prototyped in the font ahead of the spec). Lets base-glyph resolution
    succeed with real names instead of falling back to a codepoint placeholder."""
    if extra_names_path is None:
        return {}
    raw = json.loads(Path(extra_names_path).read_text())
    return {int(cp[2:], 16): name for cp, name in raw.items()}


def extract(font_path, glyphnames_path, extra_names_path=None):
    font = TTFont(font_path)
    gsub = font["GSUB"].table
    cmap = font.getBestCmap()
    cp_by_glyph = {name: cp for cp, name in cmap.items()}
    name_by_cp = load_name_by_codepoint(glyphnames_path)
    extra_names = load_extra_names(extra_names_path)
    overlap = set(name_by_cp) & set(extra_names)
    if overlap:
        raise ValueError(
            f"--extra-names overlaps glyphnames.json for: "
            f"{', '.join(f'U+{cp:04X}' for cp in sorted(overlap))}"
        )
    name_by_cp = {**name_by_cp, **extra_names}

    lookup_to_features = {}
    for feature_record in gsub.FeatureList.FeatureRecord:
        for lookup_index in feature_record.Feature.LookupListIndex:
            lookup_to_features.setdefault(lookup_index, set()).add(feature_record.FeatureTag)

    unresolved = []
    skipped_core_range = []
    stylistic_alternates = []
    ligatures = []

    for lookup_index, tags in lookup_to_features.items():
        lookup = gsub.LookupList.Lookup[lookup_index]

        # LookupType 3 = Alternate Substitution: base glyph -> [alternate glyphs].
        # Used by ssNN (exactly one alternate) and salt (one or more, ordered).
        if lookup.LookupType == 3:
            for tag in tags:
                if tag == "salt":
                    for subtable in lookup.SubTable:
                        for base_glyph, alt_glyphs in subtable.alternates.items():
                            base_name = resolve(base_glyph, cp_by_glyph, name_by_cp, unresolved)
                            for index, alt_glyph in enumerate(alt_glyphs, start=1):
                                alt_cp = cp_by_glyph.get(alt_glyph)
                                if alt_cp is None:
                                    unresolved.append(f"{alt_glyph}: no cmap entry (salt alternate)")
                                    continue
                                if alt_cp < OPTIONAL_CODEPOINT_START:
                                    skipped_core_range.append(
                                        f"salt: {base_name} -> U+{alt_cp:04X} (already a core glyph)"
                                    )
                                    continue
                                stylistic_alternates.append({
                                    "for": base_name,
                                    "feature": "salt",
                                    "index": index,
                                    "codepoint": format_cp(alt_cp),
                                })
                elif tag.startswith("ss") and tag[2:].isdigit():
                    for subtable in lookup.SubTable:
                        for base_glyph, alt_glyphs in subtable.alternates.items():
                            base_name = resolve(base_glyph, cp_by_glyph, name_by_cp, unresolved)
                            if len(alt_glyphs) != 1:
                                unresolved.append(
                                    f"{base_glyph}: expected exactly 1 alternate for {tag}, found {len(alt_glyphs)}"
                                )
                            for alt_glyph in alt_glyphs:
                                alt_cp = cp_by_glyph.get(alt_glyph)
                                if alt_cp is None:
                                    unresolved.append(f"{alt_glyph}: no cmap entry ({tag} alternate)")
                                    continue
                                if alt_cp < OPTIONAL_CODEPOINT_START:
                                    skipped_core_range.append(
                                        f"{tag}: {base_name} -> U+{alt_cp:04X} (already a core glyph)"
                                    )
                                    continue
                                stylistic_alternates.append({
                                    "for": base_name,
                                    "feature": tag,
                                    "codepoint": format_cp(alt_cp),
                                })

        # LookupType 4 = Ligature Substitution: component sequence -> ligature glyph.
        elif lookup.LookupType == 4 and "liga" in tags:
            for subtable in lookup.SubTable:
                for first_glyph, ligs in subtable.ligatures.items():
                    for lig in ligs:
                        component_glyphs = [first_glyph] + list(lig.Component)
                        component_names = [
                            resolve(g, cp_by_glyph, name_by_cp, unresolved) for g in component_glyphs
                        ]
                        lig_cp = cp_by_glyph.get(lig.LigGlyph)
                        if lig_cp is None:
                            unresolved.append(f"{lig.LigGlyph}: no cmap entry (ligature)")
                            continue
                        if lig_cp < OPTIONAL_CODEPOINT_START:
                            skipped_core_range.append(
                                f"liga: {'+'.join(component_names)} -> U+{lig_cp:04X} (already a core glyph)"
                            )
                            continue
                        ligatures.append({
                            "components": component_names,
                            "codepoint": format_cp(lig_cp),
                        })

    # Deterministic ordering for a stable, reviewable diff.
    stylistic_alternates.sort(key=lambda e: (e["for"], e["feature"], e.get("index", 0)))
    ligatures.sort(key=lambda e: e["components"])

    all_optional_cps = [int(e["codepoint"][2:], 16) for e in stylistic_alternates] + \
                        [int(e["codepoint"][2:], 16) for e in ligatures]

    return {
        "stylisticAlternates": stylistic_alternates,
        "ligatures": ligatures,
    }, unresolved, skipped_core_range, all_optional_cps


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--font", required=True)
    parser.add_argument("--glyphnames", required=True)
    parser.add_argument("--extra-names", default=None,
                        help="JSON file of {\"U+XXXX\": \"name\"} for glyphs not yet in glyphnames.json")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    data, unresolved, skipped_core_range, all_optional_cps = extract(
        args.font, args.glyphnames, args.extra_names
    )

    Path(args.out).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

    print(f"Wrote {args.out}")
    print(f"  stylistic alternates: {len(data['stylisticAlternates'])}")
    print(f"  ligatures: {len(data['ligatures'])}")
    if all_optional_cps:
        print(f"  optional codepoint range in use: U+{min(all_optional_cps):04X}-U+{max(all_optional_cps):04X}")
    if skipped_core_range:
        print(f"  skipped (already core glyphs, not font-only optional): {len(skipped_core_range)}")
    if unresolved:
        print(f"\n{len(unresolved)} unresolved entries (see below) - review before treating as baseline:", file=sys.stderr)
        for line in unresolved:
            print(f"  - {line}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
