#!/usr/bin/env python3
"""Generate metadata/*.json and mdbook/src/tables/*.md from data/ranges/*.yaml.

Only ranges listed in data/ranges/manifest.yaml are touched - this is a
gradual migration, so everything else in metadata/*.json and
mdbook/src/tables/*.md (for ranges not yet migrated) is left exactly as-is.

Usage:
    python3 tools/generate.py [--check]

    --check   don't write anything; exit non-zero if generated output
              would differ from what's currently on disk (for CI)
"""
import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "ranges"
METADATA_DIR = ROOT / "metadata"
TABLES_DIR = ROOT / "mdbook" / "src" / "tables"
OPTIONAL_CODEPOINT_START = 0xF400


def load_yaml(path):
    return yaml.safe_load(path.read_text())


def cp_int(cp_str):
    return int(cp_str[2:], 16)


def cp_str(cp_int_val):
    return f"U+{cp_int_val:04X}"


def slugify(description):
    slug = description.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


class Sources:
    def __init__(self):
        self.manifest = load_yaml(DATA_DIR / "manifest.yaml")["ranges"]
        self.ranges = {slug: load_yaml(DATA_DIR / f"{slug}.yaml") for slug in self.manifest}
        self.stylistic_sets = {
            s["id"]: s["opentype"]
            for s in load_yaml(ROOT / "data" / "stylistic-sets.yaml")["sets"]
        }
        self.font_baseline = json.loads((METADATA_DIR / "font-optional-codepoints.json").read_text())
        self.existing_glyphnames = json.loads((METADATA_DIR / "glyphnames.json").read_text())
        self.existing_ranges = json.loads((METADATA_DIR / "ranges.json").read_text())
        self.existing_classes = json.loads((METADATA_DIR / "classes.json").read_text())

    def parent_lookup(self, range_name_or_slug):
        """Look up a parent range's description + file slug, whether or not
        it's been migrated to the new YAML format yet."""
        for slug, data in self.ranges.items():
            if slug == range_name_or_slug or data["name"] == range_name_or_slug:
                return data["description"], slug
        # Fall back to the existing (not-yet-migrated) flat metadata.
        for name, data in self.existing_ranges.items():
            if name == range_name_or_slug:
                return data["description"], slugify(data["description"])
        raise KeyError(f"parent range not found: {range_name_or_slug}")

    def base_glyph_codepoint(self, name, merged_glyphnames):
        entry = merged_glyphnames.get(name)
        if entry is None:
            raise KeyError(f"base glyph not found: {name}")
        return cp_int(entry["codepoint"])


def assign_codepoints(range_data):
    start = cp_int(range_data["codepointRangeStart"])
    end = cp_int(range_data["codepointRangeEnd"])
    glyphs = range_data["glyphs"]
    if start + len(glyphs) - 1 > end:
        raise ValueError(
            f"{range_data['name']}: {len(glyphs)} glyphs don't fit in "
            f"{range_data['codepointRangeStart']}-{range_data['codepointRangeEnd']}"
        )
    return {g["name"]: start + i for i, g in enumerate(glyphs)}


def build_metadata_fragments(sources):
    """Returns (glyphnames_fragment, ranges_fragment, classes_additions) for
    all migrated ranges - the "official" published metadata. Stylistic
    alternates and ligatures are NOT part of this; they've never been
    published in glyphnames.json and stay that way (see
    metadata/font-optional-codepoints.json instead)."""
    glyphnames_fragment = {}
    ranges_fragment = {}
    classes_additions = {}  # class name -> set of glyph names

    for slug, range_data in sources.ranges.items():
        codepoints = assign_codepoints(range_data)
        glyph_names = []
        for g in range_data["glyphs"]:
            entry = {
                "codepoint": cp_str(codepoints[g["name"]]),
                "description": g["description"],
            }
            if "alternateCodepoint" in g:
                entry["alternateCodepoint"] = g["alternateCodepoint"]
            glyphnames_fragment[g["name"]] = entry
            glyph_names.append(g["name"])
            for class_name in g.get("classes", []):
                classes_additions.setdefault(class_name, set()).add(g["name"])

        ranges_fragment[range_data["name"]] = {
            "description": range_data["description"],
            "range_start": range_data["codepointRangeStart"],
            "range_end": range_data["codepointRangeEnd"],
            "glyphs": glyph_names,
        }

    return glyphnames_fragment, ranges_fragment, classes_additions


def merge_metadata(sources):
    glyphnames_fragment, ranges_fragment, classes_additions = build_metadata_fragments(sources)

    merged_glyphnames = dict(sources.existing_glyphnames)
    merged_ranges = dict(sources.existing_ranges)

    # Remove stale glyphs from any migrated range's previous incarnation
    # (handles a glyph being renamed/removed within an already-migrated range).
    for range_data in sources.ranges.values():
        old_range = sources.existing_ranges.get(range_data["name"])
        if old_range:
            new_names = {g["name"] for g in range_data["glyphs"]}
            for old_name in old_range["glyphs"]:
                if old_name not in new_names:
                    merged_glyphnames.pop(old_name, None)

    merged_glyphnames.update(glyphnames_fragment)
    merged_ranges.update(ranges_fragment)

    migrated_glyph_names = {g["name"] for r in sources.ranges.values() for g in r["glyphs"]}
    all_class_names = set(sources.existing_classes) | set(classes_additions)
    merged_classes = {}
    for class_name in all_class_names:
        existing_members = sources.existing_classes.get(class_name, [])
        new_set = {m for m in existing_members if m not in migrated_glyph_names} | classes_additions.get(class_name, set())
        if new_set == set(existing_members):
            # Membership unchanged - preserve the original order verbatim
            # rather than recomputing it (there's no reliable ordering
            # signal for brand-new members relative to existing ones).
            merged_classes[class_name] = list(existing_members)
        else:
            retained = [m for m in existing_members if m in new_set]
            added = sorted(new_set - set(retained))
            merged_classes[class_name] = retained + added
    merged_classes = {k: v for k, v in merged_classes.items() if v}

    return merged_glyphnames, merged_ranges, merged_classes


def resolve_alternate(alt, base_cp, sources, next_free_codepoint, position_by_base, salt_occurrence_by_base):
    """position_by_base counts EVERY alternate (named-set or salt) seen so
    far for this base glyph, in YAML order - this reconstructs Bravura's
    original salt numbering, which is the alternate's position among ALL
    of that base's alternates (named-set ones consume a position without
    using a salt number, e.g. salt01 then ss01 then salt03).
    salt_occurrence_by_base counts only the salt-type ones, for matching
    against font-optional-codepoints.json's own per-base salt index."""
    base = alt["for"]
    position_by_base[base] = position_by_base.get(base, 0) + 1

    opentype = sources.stylistic_sets.get(alt["set"]) if "set" in alt else None
    if opentype:
        for entry in sources.font_baseline["stylisticAlternates"]:
            if entry["for"] == base and entry["feature"] == opentype:
                return cp_int(entry["codepoint"]), f"uni{base_cp:04X}.{opentype}"
        # Not yet in the font - assign the next free optional codepoint.
        cp = next_free_codepoint()
        return cp, f"uni{base_cp:04X}.{opentype}"
    else:
        salt_occurrence_by_base[base] = salt_occurrence_by_base.get(base, 0) + 1
        nth = salt_occurrence_by_base[base]
        existing = sorted(
            (e for e in sources.font_baseline["stylisticAlternates"]
             if e["for"] == base and e["feature"] == "salt"),
            key=lambda e: e["index"],
        )
        if nth <= len(existing):
            cp = cp_int(existing[nth - 1]["codepoint"])
        else:
            cp = next_free_codepoint()
        label_index = position_by_base[base]
        return cp, f"uni{base_cp:04X}.salt{label_index:02d}"


def resolve_ligature(lig, merged_glyphnames, sources, next_free_codepoint):
    component_cps = [sources.base_glyph_codepoint(c, merged_glyphnames) for c in lig["components"]]
    label = "_".join(f"uni{cp:04X}" for cp in component_cps)
    for entry in sources.font_baseline["ligatures"]:
        entry_components = entry["components"]
        if entry_components == lig["components"]:
            return cp_int(entry["codepoint"]), label
    return next_free_codepoint(), label


def build_font_glyph_index(sources, merged_glyphnames):
    """Returns {ufo_glyph_name: {...}} for every glyph the spec defines:
    base glyphs, stylistic alternates, and ligatures. Mirrors
    generate_markdown's own resolution loop exactly (same shared allocator,
    same per-range reset of the position/salt counters, same range
    iteration order) so codepoints assigned here always agree with what's
    already published in font-optional-codepoints.json and
    mdbook/src/tables/*.md.

    Common fields: "codepoint" (int), "name" (SMuFL semantic name, e.g.
    "timeSig0Small"), "description" (prose), "category" ("base"|
    "alternate"|"ligature"). Category-specific: alternates additionally
    have "for" (base glyph's SMuFL name) and "set" (opentype stylistic-set
    tag, or None for a plain salt alternate); ligatures additionally have
    "components" (list of component glyphs' SMuFL names).

    Consumers: tools/sync_ufo_glyphs.py (placeholder glyphs),
    tools/generate_font.py (GDEF ligature classification),
    tools/generate_font_metadata.py (Bravura.json)."""
    allocate = make_codepoint_allocator(sources)
    index = {}

    for name, entry in merged_glyphnames.items():
        index[f"uni{cp_int(entry['codepoint']):04X}"] = {
            "codepoint": cp_int(entry["codepoint"]),
            "name": name,
            "description": entry["description"],
            "category": "base",
        }

    for range_data in sources.ranges.values():
        position_by_base = {}
        salt_occurrence_by_base = {}
        for alt in range_data.get("stylisticAlternates", []):
            base_cp = sources.base_glyph_codepoint(alt["for"], merged_glyphnames)
            alt_cp, label = resolve_alternate(
                alt, base_cp, sources, allocate, position_by_base, salt_occurrence_by_base
            )
            index[label] = {
                "codepoint": alt_cp,
                "name": alt["name"],
                "description": alt["description"],
                "category": "alternate",
                "for": alt["for"],
                "set": sources.stylistic_sets.get(alt["set"]) if "set" in alt else None,
            }
        for lig in range_data.get("ligatures", []):
            lig_cp, label = resolve_ligature(lig, merged_glyphnames, sources, allocate)
            index[label] = {
                "codepoint": lig_cp,
                "name": lig["name"],
                "description": lig["description"],
                "category": "ligature",
                "components": lig["components"],
            }

    return index


def make_codepoint_allocator(sources):
    all_used = (
        [cp_int(e["codepoint"]) for e in sources.font_baseline["stylisticAlternates"]]
        + [cp_int(e["codepoint"]) for e in sources.font_baseline["ligatures"]]
    )
    counter = [max(all_used) if all_used else OPTIONAL_CODEPOINT_START - 1]

    def allocate():
        counter[0] += 1
        return counter[0]

    return allocate


def two_column_rows(cells):
    rows = []
    for i in range(0, len(cells), 2):
        left = cells[i]
        right = cells[i + 1] if i + 1 < len(cells) else "&nbsp; | &nbsp;"
        rows.append(f"|{left} | {right}")
    return rows


def glyph_cell(cp, bold_label, name, description, suffix=""):
    return (
        f'<span class="bravura_large">&#x{cp:04x};</span> | '
        f"**{bold_label}**{suffix}<br/>*{name}*<br/>{description}"
    )


def generate_markdown(slug, range_data, merged_glyphnames, sources, allocate):
    codepoints = assign_codepoints(range_data)
    start = range_data["codepointRangeStart"]
    end = range_data["codepointRangeEnd"]
    heading = f"{range_data['description']} ({start}–{end})"
    lines = [heading, "=" * len(heading), ""]

    if range_data.get("supplementaryTo"):
        parent_desc, parent_slug = sources.parent_lookup(range_data["supplementaryTo"])
        lines += [f"Supplementary to [{parent_desc}]({parent_slug}.md)", ""]

    if range_data["glyphs"]:
        cells = []
        for g in range_data["glyphs"]:
            cp = codepoints[g["name"]]
            bold = f"U+{cp:04X}"
            suffix = f" (and {g['alternateCodepoint']})" if "alternateCodepoint" in g else ""
            cells.append(glyph_cell(cp, bold, g["name"], g["description"], suffix))
        lines += ["| **Glyph** | **Description** | **Glyph** | **Description**",
                  "| :-------: | --------------- | :-------: | ---------------"]
        lines += two_column_rows(cells)
        lines.append("")
    else:
        lines += ["*Reserved for future use.*", ""]

    if range_data.get("stylisticAlternates"):
        heading2 = "Recommended stylistic alternates"
        lines += [heading2, "-" * len(heading2),
                  "| **Glyph** | **Description** | **Glyph** | **Description**",
                  "| :-------: | --------------- | :-------: | ---------------"]
        cells = []
        position_by_base = {}
        salt_occurrence_by_base = {}
        for alt in range_data["stylisticAlternates"]:
            base_cp = sources.base_glyph_codepoint(alt["for"], merged_glyphnames)
            alt_cp, bold = resolve_alternate(alt, base_cp, sources, allocate, position_by_base, salt_occurrence_by_base)
            cells.append(glyph_cell(alt_cp, bold, alt["name"], alt["description"]))
        lines += two_column_rows(cells)
        lines.append("")

    if range_data.get("ligatures"):
        heading3 = "Recommended ligatures"
        lines += [heading3, "-" * len(heading3),
                  "| **Glyph** | **Description** | **Glyph** | **Description**",
                  "| :-------: | --------------- | :-------: | ---------------"]
        cells = []
        for lig in range_data["ligatures"]:
            lig_cp, bold = resolve_ligature(lig, merged_glyphnames, sources, allocate)
            cells.append(glyph_cell(lig_cp, bold, lig["name"], lig["description"]))
        lines += two_column_rows(cells)
        lines.append("")

    supplementary_groups = [
        (s, r) for s, r in sources.ranges.items() if r.get("supplementaryTo") == slug
    ]
    if supplementary_groups:
        # 21 dashes, not len("Supplementary Groups")==20 - matches all 14
        # existing instances of this heading exactly (a pre-existing quirk
        # in the hand-authored corpus, not derivable from the text itself).
        lines += ["Supplementary Groups", "-" * 21]
        for s, r in supplementary_groups:
            lines.append(f"[{r['description']}]({s}.md)")
        lines.append("")

    if range_data.get("implementationNotes"):
        notes_name = Path(range_data["implementationNotes"]).name
        # 21 dashes, not len("Implementation notes")==20 - same quirk, matches
        # 45/46 existing instances (the lone exception was our own earlier
        # generated output, before this was noticed).
        lines += ["Implementation notes", "-" * 21, "",
                  f"{{{{#include ../implementation_notes/{notes_name}}}}}"]

    return "\n".join(lines).rstrip("\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    sources = Sources()
    merged_glyphnames, merged_ranges, merged_classes = merge_metadata(sources)
    allocate = make_codepoint_allocator(sources)

    def dump(d):
        return json.dumps(d, indent=4, sort_keys=True).replace("    ", "\t")

    outputs = {
        METADATA_DIR / "glyphnames.json": dump(merged_glyphnames),
        METADATA_DIR / "ranges.json": dump(merged_ranges),
        METADATA_DIR / "classes.json": dump(merged_classes),
    }
    for slug, range_data in sources.ranges.items():
        outputs[TABLES_DIR / f"{slug}.md"] = generate_markdown(slug, range_data, merged_glyphnames, sources, allocate)

    if args.check:
        failed = False
        for path, content in outputs.items():
            current = path.read_text() if path.exists() else None
            if current != content:
                print(f"DIFFERS: {path.relative_to(ROOT)}")
                failed = True
        if failed:
            return 1
        print("OK - generated output matches what's on disk")
        return 0

    for path, content in outputs.items():
        path.write_text(content)
        print(f"Wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
