#!/usr/bin/env python3
"""One-time bulk migration: convert the existing metadata/*.json + hand-
written mdbook/src/tables/*.md into data/ranges/*.yaml, data/ranges/
manifest.yaml.

metadata/ranges.json + glyphnames.json + classes.json are the ground truth
for each range's glyph list (name, description, alternateCodepoint,
classes) - reliable structured data, no parsing needed. The Markdown
tables are only parsed for the structure that ISN'T in the flat JSON:
supplementaryTo, stylisticAlternates, ligatures, and implementationNotes.

Usage:
    python3 tools/migrate_existing_ranges.py [--write]

Without --write, just reports what it found/parsed (dry run).
"""
import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
METADATA_DIR = ROOT / "metadata"
TABLES_DIR = ROOT / "mdbook" / "src" / "tables"
NOTES_DIR = ROOT / "mdbook" / "src" / "implementation_notes"
DATA_DIR = ROOT / "data" / "ranges"

ROW_RE = re.compile(r"^\|(.+)$")
CELL_BOLD_RE = re.compile(r"^\*\*(.+?)\*\*<br/>\*(.+?)\*<br/>(.+)$")
MAIN_BOLD_RE = re.compile(r"^U\+([0-9A-F]{4,6})(?: \(and (U\+[0-9A-F]{4,6})\))?$")
ALT_BOLD_RE = re.compile(r"^uni([0-9A-F]{4,6})\.(ss[0-9]{2}|salt[0-9]{2})$")
LIG_BOLD_RE = re.compile(r"^(uni[0-9A-F]{4,6}(?:_uni[0-9A-F]{4,6})+)$")
SUPPLEMENTARY_TO_RE = re.compile(r"^Supplementary to \[(.+)\]\((.+)\.md\)$")
INCLUDE_RE = re.compile(r"^\{\{#include \.\./implementation_notes/(.+)\}\}$")


def slugify(description):
    # Matches Django's slugify: NFKD-normalize then drop non-ASCII, so
    # e.g. "Kodály" -> "kodaly", not "kod-ly".
    ascii_desc = unicodedata.normalize("NFKD", description).encode("ascii", "ignore").decode("ascii")
    slug = ascii_desc.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


def split_row(line):
    m = ROW_RE.match(line)
    if not m:
        return None
    parts = m.group(1).split(" | ")
    if len(parts) != 4:
        raise ValueError(f"expected 4 cells, got {len(parts)}: {line!r}")
    return parts


def parse_cell(text):
    if text.strip() == "&nbsp;":
        return None
    m = CELL_BOLD_RE.match(text)
    if not m:
        raise ValueError(f"couldn't parse cell text: {text!r}")
    return m.group(1), m.group(2), m.group(3)  # bold, italic (name), description


class RangeSource:
    def __init__(self):
        self.ranges_json = json.loads((METADATA_DIR / "ranges.json").read_text())
        self.glyphnames_json = json.loads((METADATA_DIR / "glyphnames.json").read_text())
        self.classes_json = json.loads((METADATA_DIR / "classes.json").read_text())
        self.name_by_cp = {}
        for name, data in self.glyphnames_json.items():
            self.name_by_cp[int(data["codepoint"][2:], 16)] = name
        self.classes_by_glyph = {}
        for class_name, members in self.classes_json.items():
            for m in members:
                self.classes_by_glyph.setdefault(m, []).append(class_name)

    def base_name(self, hex_cp):
        cp = int(hex_cp, 16)
        name = self.name_by_cp.get(cp)
        if name is None:
            raise ValueError(f"no glyph name for U+{hex_cp}")
        return name


def parse_table_file(path, source):
    """Returns dict with keys: supplementaryTo, stylisticAlternates,
    ligatures, implementationNotesInline (raw text) or
    implementationNotesFile (referenced filename)."""
    lines = path.read_text().splitlines()
    result = {
        "supplementaryTo": None,
        "stylisticAlternates": [],
        "ligatures": [],
        "implementationNotesFile": None,
        "implementationNotesInline": None,
    }

    # "Supplementary to [X](x.md)" appears right after the heading, if present.
    for line in lines[:6]:
        m = SUPPLEMENTARY_TO_RE.match(line.strip())
        if m:
            result["supplementaryTo"] = m.group(2)  # parent's file slug
            break

    section = None  # None | 'alternates' | 'ligatures' | 'notes'
    notes_lines = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped == "Recommended stylistic alternates":
            section = "alternates"
            continue
        if stripped == "Recommended ligatures":
            section = "ligatures"
            continue
        if stripped == "Supplementary Groups":
            section = "supplementary_groups"  # skip content, it's derived
            continue
        if stripped == "Implementation notes":
            section = "notes"
            continue
        if section == "notes":
            if stripped.startswith("----"):
                continue
            m = INCLUDE_RE.match(stripped)
            if m:
                result["implementationNotesFile"] = m.group(1)
            else:
                notes_lines.append(line)
            continue
        if section == "alternates" and line.startswith("|"):
            if line.startswith("| **Glyph**") or line.startswith("| :"):
                continue
            cells = split_row(line)
            if cells is None:
                continue
            for idx in (0, 2):
                span, text = cells[idx], cells[idx + 1]
                parsed = parse_cell(text)
                if parsed is None:
                    continue
                bold, name, description = parsed
                m = ALT_BOLD_RE.match(bold)
                if not m:
                    raise ValueError(f"{path.name}: bad alternate bold label {bold!r}")
                base_hex, feature = m.groups()
                entry = {
                    "for": source.base_name(base_hex),
                    "name": name,
                    "description": description,
                }
                if feature.startswith("ss"):
                    entry["_opentype"] = feature  # resolved to a set id later
                result["stylisticAlternates"].append(entry)
        if section == "ligatures" and line.startswith("|"):
            if line.startswith("| **Glyph**") or line.startswith("| :"):
                continue
            cells = split_row(line)
            if cells is None:
                continue
            for idx in (0, 2):
                span, text = cells[idx], cells[idx + 1]
                parsed = parse_cell(text)
                if parsed is None:
                    continue
                bold, name, description = parsed
                m = LIG_BOLD_RE.match(bold)
                if not m:
                    raise ValueError(f"{path.name}: bad ligature bold label {bold!r}")
                component_hexes = [part[3:] for part in bold.split("_")]
                result["ligatures"].append({
                    "name": name,
                    "description": description,
                    "components": [source.base_name(h) for h in component_hexes],
                })

    if notes_lines:
        # Trim leading/trailing blank lines.
        while notes_lines and not notes_lines[0].strip():
            notes_lines.pop(0)
        while notes_lines and not notes_lines[-1].strip():
            notes_lines.pop()
        if notes_lines:
            result["implementationNotesInline"] = "\n".join(notes_lines) + "\n"

    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    source = RangeSource()
    registry = yaml.safe_load((ROOT / "data" / "stylistic-sets.yaml").read_text())["sets"]
    # ss05 is a known historical duplicate of ss08 ("oversized") - see the
    # note in data/stylistic-sets.yaml. Fold it into the same registry id.
    id_by_opentype = {s["opentype"]: s["id"] for s in registry}
    id_by_opentype["ss05"] = id_by_opentype["ss08"]

    # slug -> table file, derived the same way admin.py did: slugify(description)
    slug_by_range_name = {}
    for range_name, data in source.ranges_json.items():
        slug = slugify(data["description"])
        slug_by_range_name[range_name] = slug

    already_migrated = set()
    manifest_path = DATA_DIR / "manifest.yaml"
    if manifest_path.exists():
        already_migrated = set(yaml.safe_load(manifest_path.read_text())["ranges"])

    all_parsed = []
    parsed_by_range = {}
    errors = []
    for range_name, slug in slug_by_range_name.items():
        table_path = TABLES_DIR / f"{slug}.md"
        if not table_path.exists():
            errors.append(f"{range_name}: no table file at {table_path.name}")
            continue
        try:
            parsed = parse_table_file(table_path, source)
        except ValueError as e:
            errors.append(f"{range_name} ({slug}): {e}")
            continue
        parsed_by_range[range_name] = (slug, parsed)
        all_parsed.append(parsed)

    if errors:
        print(f"{len(errors)} ranges failed to parse:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)

    all_tags = sorted({alt["_opentype"] for p in all_parsed for alt in p["stylisticAlternates"] if "_opentype" in alt})
    print(f"\nParsed {len(parsed_by_range)}/{len(slug_by_range_name)} ranges successfully")
    print(f"ssNN tags in use: {', '.join(all_tags)} -> resolved via data/stylistic-sets.yaml registry")

    if not args.write:
        print("\nDry run - pass --write to generate files")
        return 1 if errors else 0

    # --- write data/ranges/<slug>.yaml for each range ---
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    written_slugs = []
    for range_name, (slug, parsed) in parsed_by_range.items():
        range_json = source.ranges_json[range_name]
        glyphs_out = []
        for glyph_name in range_json["glyphs"]:
            gn = source.glyphnames_json[glyph_name]
            g = {"name": glyph_name, "description": gn["description"]}
            if "alternateCodepoint" in gn:
                g["alternateCodepoint"] = gn["alternateCodepoint"]
            classes = sorted(source.classes_by_glyph.get(glyph_name, []))
            if classes:
                g["classes"] = classes
            glyphs_out.append(g)

        doc = {
            "name": range_name,
            "description": range_json["description"],
            "firstPublishedIn": "1.4",  # all currently-migrated ranges predate this workflow
        }
        if parsed["implementationNotesFile"]:
            doc["implementationNotes"] = f"implementation_notes/{parsed['implementationNotesFile']}"
        elif parsed["implementationNotesInline"]:
            notes_filename = f"{slug}.md"
            notes_path = NOTES_DIR / notes_filename
            if not notes_path.exists():
                notes_path.write_text(parsed["implementationNotesInline"])
            doc["implementationNotes"] = f"implementation_notes/{notes_filename}"

        doc["codepointRangeStart"] = range_json["range_start"]
        doc["codepointRangeEnd"] = range_json["range_end"]
        doc["hidden"] = False
        if parsed["supplementaryTo"]:
            doc["supplementaryTo"] = parsed["supplementaryTo"]

        doc["glyphs"] = glyphs_out

        if parsed["stylisticAlternates"]:
            alts_out = []
            for alt in parsed["stylisticAlternates"]:
                entry = {"for": alt["for"], "name": alt["name"], "description": alt["description"]}
                if "_opentype" in alt:
                    entry["set"] = id_by_opentype[alt["_opentype"]]
                alts_out.append(entry)
            doc["stylisticAlternates"] = alts_out

        if parsed["ligatures"]:
            doc["ligatures"] = parsed["ligatures"]

        yaml_text = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True, width=100)
        (DATA_DIR / f"{slug}.yaml").write_text(yaml_text)
        written_slugs.append(slug)

    # --- write manifest.yaml, in current SUMMARY.md Tables order ---
    summary_path = ROOT / "mdbook" / "src" / "SUMMARY.md"
    summary_lines = summary_path.read_text().splitlines()
    slug_to_written = set(written_slugs)
    ordered_slugs = []
    table_ref_re = re.compile(r"\./tables/([a-z0-9-]+)\.md")
    for line in summary_lines:
        m = table_ref_re.search(line)
        if m and m.group(1) in slug_to_written:
            ordered_slugs.append(m.group(1))
    missing_from_summary = slug_to_written - set(ordered_slugs)
    for s in sorted(missing_from_summary):
        ordered_slugs.append(s)  # append anything not found in SUMMARY.md, e.g. brand new ranges

    (DATA_DIR / "manifest.yaml").write_text(
        "# Order in which ranges appear in the specification's \"Tables\" section.\n"
        "# Each entry is a slug with a corresponding data/ranges/<slug>.yaml file.\n"
        + yaml.safe_dump({"ranges": ordered_slugs}, sort_keys=False, allow_unicode=True)
    )

    print(f"\nWrote {len(written_slugs)} range files, manifest.yaml")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
