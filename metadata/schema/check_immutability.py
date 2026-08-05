#!/usr/bin/env python3
"""Enforce SMuFL's core invariant: once a glyph's codepoint (or a range's
codepoint bounds) was published in a formal release, it never moves again.
A glyph's description can change; its name and codepoint cannot.

The baseline is the last formally published version (the v1.4 git tag),
not a rolling "whatever was there before this PR" comparison. While the
next version is under development, codepoints may still be reassigned
freely as long as they don't collide with anything that was already in
v1.4 - only a formal release freezes them for good. v1.4 is used because
there's no per-release metadata/*.json snapshot checked into
releases/<version>/ to compare against instead (only the built spec is
archived there), but the v1.4 tag does have metadata/*.json in the
working tree at that point in history.

Usage:
    python3 metadata/schema/check_immutability.py [--baseline-ref v1.4]
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
METADATA_DIR = ROOT / "metadata"


def git_show(ref, path):
    """Returns the file's content at the given ref, or None if it didn't
    exist there (e.g. a file introduced in the current change)."""
    result = subprocess.run(
        ["git", "show", f"{ref}:{path}"],
        cwd=ROOT, capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def load_json_at_ref(ref, relative_path):
    content = git_show(ref, relative_path)
    if content is None:
        return None
    return json.loads(content)


def check_glyphnames(baseline, current, errors):
    if baseline is None:
        print("(no baseline glyphnames.json - skipping, nothing published yet)")
        return
    codepoint_to_baseline_name = {}
    for name, data in baseline.items():
        codepoint_to_baseline_name.setdefault(data["codepoint"], name)

    for name, base_data in baseline.items():
        cur_data = current.get(name)
        if cur_data is None:
            errors.append(f"glyphnames.json: '{name}' (U+{base_data['codepoint'][2:]}) was removed")
            continue
        if cur_data["codepoint"] != base_data["codepoint"]:
            errors.append(
                f"glyphnames.json: '{name}' codepoint changed from "
                f"{base_data['codepoint']} to {cur_data['codepoint']}"
            )

    for name, cur_data in current.items():
        cp = cur_data["codepoint"]
        prior_name = codepoint_to_baseline_name.get(cp)
        if prior_name is not None and prior_name != name:
            errors.append(
                f"glyphnames.json: {cp} was '{prior_name}', now claimed by "
                f"'{name}' - codepoints cannot be reassigned to a different name"
            )


def check_ranges(baseline, current, errors):
    if baseline is None:
        print("(no baseline ranges.json - skipping, nothing published yet)")
        return
    for name, base_data in baseline.items():
        cur_data = current.get(name)
        if cur_data is None:
            errors.append(f"ranges.json: '{name}' was removed")
            continue
        if cur_data["range_start"] != base_data["range_start"]:
            errors.append(
                f"ranges.json: '{name}' range_start changed from "
                f"{base_data['range_start']} to {cur_data['range_start']}"
            )
        if cur_data["range_end"] != base_data["range_end"]:
            errors.append(
                f"ranges.json: '{name}' range_end changed from "
                f"{base_data['range_end']} to {cur_data['range_end']} "
                f"(if the range is full, create a '-supplement' range instead "
                f"of extending this one)"
            )


def check_font_optional_codepoints(baseline, current, errors):
    if baseline is None:
        print("(no baseline font-optional-codepoints.json - skipping, nothing published yet)")
        return

    def alt_key(e):
        return (e["for"], e["feature"], e.get("index"))

    baseline_alts = {alt_key(e): e["codepoint"] for e in baseline["stylisticAlternates"]}
    current_alts = {alt_key(e): e["codepoint"] for e in current["stylisticAlternates"]}
    for key, base_cp in baseline_alts.items():
        cur_cp = current_alts.get(key)
        if cur_cp is None:
            errors.append(f"font-optional-codepoints.json: stylistic alternate {key} was removed")
        elif cur_cp != base_cp:
            errors.append(
                f"font-optional-codepoints.json: stylistic alternate {key} "
                f"codepoint changed from {base_cp} to {cur_cp}"
            )

    def lig_key(e):
        return tuple(e["components"])

    baseline_ligs = {lig_key(e): e["codepoint"] for e in baseline["ligatures"]}
    current_ligs = {lig_key(e): e["codepoint"] for e in current["ligatures"]}
    for key, base_cp in baseline_ligs.items():
        cur_cp = current_ligs.get(key)
        if cur_cp is None:
            errors.append(f"font-optional-codepoints.json: ligature {'+'.join(key)} was removed")
        elif cur_cp != base_cp:
            errors.append(
                f"font-optional-codepoints.json: ligature {'+'.join(key)} "
                f"codepoint changed from {base_cp} to {cur_cp}"
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ref", default="v1.4")
    args = parser.parse_args()

    errors = []

    baseline_glyphnames = load_json_at_ref(args.baseline_ref, "metadata/glyphnames.json")
    current_glyphnames = json.loads((METADATA_DIR / "glyphnames.json").read_text())
    check_glyphnames(baseline_glyphnames, current_glyphnames, errors)

    baseline_ranges = load_json_at_ref(args.baseline_ref, "metadata/ranges.json")
    current_ranges = json.loads((METADATA_DIR / "ranges.json").read_text())
    check_ranges(baseline_ranges, current_ranges, errors)

    baseline_optional = load_json_at_ref(args.baseline_ref, "metadata/font-optional-codepoints.json")
    optional_path = METADATA_DIR / "font-optional-codepoints.json"
    if optional_path.exists():
        current_optional = json.loads(optional_path.read_text())
        check_font_optional_codepoints(baseline_optional, current_optional, errors)

    if errors:
        print(f"\n{len(errors)} immutability violation(s) against {args.baseline_ref}:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        return 1

    print(f"ok -- no immutability violations against {args.baseline_ref}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
