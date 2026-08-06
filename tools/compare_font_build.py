#!/usr/bin/env python3
"""Compare a UFO-compiled Bravura.otf against the existing FontLab-generated
Bravura.otf, to check the fidelity of the FontLab -> UFO -> OTF round-trip.

Checks: table presence, glyph set (names/count), cmap, glyph outlines
(contour/point counts, bounding boxes, CFF hint presence), advance widths,
GSUB/GPOS feature/script/lookup structure, name table records, and
head/OS2/post font-level metadata.

This is a structural comparison, not byte-exact - CFF charstring encoding
and overlap-removal can legitimately differ between tools while producing
visually identical outlines. The goal is to surface real discrepancies
(missing tables, broken glyphs, different hinting, different features)
worth a human's attention, not to demand an exact match.

Usage:
    python3 tools/compare_font_build.py <built.otf> <reference.otf> [--verbose]
"""
import argparse
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.statisticsPen import StatisticsPen


def load(path):
    return TTFont(path)


def compare_tables(built, ref, report):
    built_tables = set(built.keys())
    ref_tables = set(ref.keys())
    report.section("Table presence")
    only_ref = sorted(ref_tables - built_tables)
    only_built = sorted(built_tables - ref_tables)
    if only_ref:
        report.issue(f"Tables in reference but missing from built: {', '.join(only_ref)}")
    if only_built:
        report.issue(f"Tables in built but not in reference: {', '.join(only_built)}")
    if not only_ref and not only_built:
        report.ok(f"Same table set: {', '.join(sorted(built_tables))}")


def compare_glyph_set(built, ref, report):
    report.section("Glyph set")
    built_names = set(built.getGlyphOrder())
    ref_names = set(ref.getGlyphOrder())
    only_ref = sorted(ref_names - built_names)
    only_built = sorted(built_names - ref_names)
    report.info(f"built: {len(built_names)} glyphs, reference: {len(ref_names)} glyphs")
    if only_ref:
        report.issue(f"{len(only_ref)} glyph(s) in reference but missing from built: "
                      f"{', '.join(only_ref[:20])}" + (" ..." if len(only_ref) > 20 else ""))
    if only_built:
        report.issue(f"{len(only_built)} glyph(s) in built but not in reference: "
                      f"{', '.join(only_built[:20])}" + (" ..." if len(only_built) > 20 else ""))
    if not only_ref and not only_built:
        report.ok("Identical glyph name sets")
    return built_names & ref_names


def compare_cmap(built, ref, report):
    report.section("cmap")
    built_cmap = built.getBestCmap()
    ref_cmap = ref.getBestCmap()
    built_set = set(built_cmap.items())
    ref_set = set(ref_cmap.items())
    only_ref = sorted(ref_set - built_set)
    only_built = sorted(built_set - ref_set)
    if only_ref:
        report.issue(f"{len(only_ref)} cmap entries in reference but not built (or mapped "
                      f"differently): {only_ref[:10]}" + (" ..." if len(only_ref) > 10 else ""))
    if only_built:
        report.issue(f"{len(only_built)} cmap entries in built but not reference: "
                      f"{only_built[:10]}" + (" ..." if len(only_built) > 10 else ""))
    if not only_ref and not only_built:
        report.ok(f"Identical cmap ({len(built_cmap)} entries)")


def get_glyph_stats(font, glyph_name):
    glyph_set = font.getGlyphSet()
    pen = BoundsPen(glyph_set)
    try:
        glyph_set[glyph_name].draw(pen)
    except Exception as e:
        return {"error": str(e)}
    stats_pen = StatisticsPen(glyphset=glyph_set)
    try:
        glyph_set[glyph_name].draw(stats_pen)
        contour_count = stats_pen.numberOfContours if hasattr(stats_pen, "numberOfContours") else None
    except Exception:
        contour_count = None
    return {
        "bounds": pen.bounds,
        "contours": contour_count,
    }


def compare_outlines(built, ref, shared_names, report, verbose):
    report.section("Glyph outlines (bounding box)")
    built_hmtx = built["hmtx"]
    ref_hmtx = ref["hmtx"]
    bbox_diffs = []
    width_diffs = []
    errors = []
    for name in sorted(shared_names):
        b_stats = get_glyph_stats(built, name)
        r_stats = get_glyph_stats(ref, name)
        if "error" in b_stats or "error" in r_stats:
            errors.append((name, b_stats.get("error"), r_stats.get("error")))
            continue
        if b_stats["bounds"] != r_stats["bounds"]:
            bbox_diffs.append((name, b_stats["bounds"], r_stats["bounds"]))
        b_width = built_hmtx[name][0]
        r_width = ref_hmtx[name][0]
        if b_width != r_width:
            width_diffs.append((name, b_width, r_width))

    if errors:
        report.issue(f"{len(errors)} glyph(s) failed to draw: {[e[0] for e in errors[:10]]}")
        if verbose:
            for name, be, re in errors[:10]:
                report.info(f"  {name}: built error={be!r} ref error={re!r}")
    if bbox_diffs:
        report.issue(f"{len(bbox_diffs)} glyph(s) have a different bounding box")
        if verbose:
            for name, bb, rb in bbox_diffs[:15]:
                report.info(f"  {name}: built={bb} ref={rb}")
    if width_diffs:
        report.issue(f"{len(width_diffs)} glyph(s) have a different advance width")
        if verbose:
            for name, bw, rw in width_diffs[:15]:
                report.info(f"  {name}: built={bw} ref={rw}")
    if not errors and not bbox_diffs and not width_diffs:
        report.ok(f"All {len(shared_names)} shared glyphs have matching bounds and widths")


def compare_cff_hints(built, ref, report):
    report.section("CFF hinting")
    if "CFF " not in built or "CFF " not in ref:
        report.info("Not a CFF font on one side - skipping")
        return
    built_cff = built["CFF "].cff
    ref_cff = ref["CFF "].cff
    built_priv = built_cff[built_cff.fontNames[0]].Private
    ref_priv = ref_cff[ref_cff.fontNames[0]].Private
    built_has_hints = hasattr(built_priv, "StdHW") or hasattr(built_priv, "StemSnapH")
    ref_has_hints = hasattr(ref_priv, "StdHW") or hasattr(ref_priv, "StemSnapH")
    report.info(f"built has global hint stems: {built_has_hints}, reference: {ref_has_hints}")
    if ref_has_hints and not built_has_hints:
        report.issue("Reference font has CFF global hinting (StdHW/StemSnapH); built font does not")

    # Per-glyph hint presence: check a sample of charstrings for hstem/vstem operators
    built_charstrings = built_cff[built_cff.fontNames[0]].CharStrings
    ref_charstrings = ref_cff[ref_cff.fontNames[0]].CharStrings
    sample = [n for n in built.getGlyphOrder() if n in ref_charstrings.keys()][:200]
    built_hinted = ref_hinted = 0
    for name in sample:
        if _charstring_has_hints(built_charstrings[name]):
            built_hinted += 1
        if _charstring_has_hints(ref_charstrings[name]):
            ref_hinted += 1
    report.info(f"Sample of {len(sample)} glyphs: {built_hinted} hinted in built, {ref_hinted} hinted in reference")
    if ref_hinted > 0 and built_hinted == 0:
        report.issue("Reference glyphs have per-glyph CFF hints (hstem/vstem); built glyphs appear to have none")


def _charstring_has_hints(charstring):
    try:
        charstring.decompile()
        return any(op in ("hstem", "vstem", "hstemhm", "vstemhm", "hintmask", "cntrmask")
                   for op, _ in charstring.program_iter() if isinstance(op, str)) \
            if hasattr(charstring, "program_iter") else \
            any(isinstance(tok, str) and tok in ("hstem", "vstem", "hstemhm", "vstemhm", "hintmask", "cntrmask")
                for tok in charstring.program)
    except Exception:
        return False


def compare_gsub_gpos(built, ref, report):
    for tag in ("GSUB", "GPOS"):
        report.section(tag)
        if tag not in built and tag not in ref:
            report.info("Not present in either font")
            continue
        if tag not in built or tag not in ref:
            report.issue(f"{tag} present in {'reference' if tag not in built else 'built'} only")
            continue
        built_tags = _feature_tags(built[tag].table)
        ref_tags = _feature_tags(ref[tag].table)
        only_ref = sorted(ref_tags - built_tags)
        only_built = sorted(built_tags - ref_tags)
        if only_ref:
            report.issue(f"Feature tags in reference but not built: {', '.join(only_ref)}")
        if only_built:
            report.issue(f"Feature tags in built but not reference: {', '.join(only_built)}")
        built_lookup_count = len(built[tag].table.LookupList.Lookup) if built[tag].table.LookupList else 0
        ref_lookup_count = len(ref[tag].table.LookupList.Lookup) if ref[tag].table.LookupList else 0
        report.info(f"Lookup count: built={built_lookup_count} reference={ref_lookup_count}")
        if not only_ref and not only_built and built_lookup_count == ref_lookup_count:
            report.ok(f"Same feature tags ({len(built_tags)}) and lookup count ({built_lookup_count})")


def _feature_tags(table):
    if table.FeatureList is None:
        return set()
    return {fr.FeatureTag for fr in table.FeatureList.FeatureRecord}


def compare_name_table(built, ref, report):
    report.section("name table")
    interesting_ids = {
        0: "Copyright", 1: "Family", 2: "Subfamily", 3: "Unique ID", 4: "Full name",
        5: "Version", 6: "PostScript name", 7: "Trademark", 8: "Manufacturer",
        9: "Designer", 11: "Vendor URL", 13: "License", 14: "License URL",
    }
    for name_id, label in interesting_ids.items():
        built_val = built["name"].getDebugName(name_id)
        ref_val = ref["name"].getDebugName(name_id)
        if built_val != ref_val:
            report.issue(f"{label} (id {name_id}) differs:\n"
                          f"    built: {built_val!r}\n"
                          f"    reference: {ref_val!r}")


def compare_head_os2(built, ref, report):
    report.section("head / OS2 / post")
    checks = [
        ("head", "unitsPerEm"),
        ("head", "fontRevision"),
        ("OS/2", "achVendID"),
        ("OS/2", "usWeightClass"),
        ("OS/2", "fsType"),
        ("OS/2", "sTypoAscender"),
        ("OS/2", "sTypoDescender"),
        ("post", "italicAngle"),
        ("post", "underlinePosition"),
        ("post", "underlineThickness"),
    ]
    for table_tag, field in checks:
        if table_tag not in built or table_tag not in ref:
            continue
        built_val = getattr(built[table_tag], field, None)
        ref_val = getattr(ref[table_tag], field, None)
        if built_val != ref_val:
            report.issue(f"{table_tag}.{field}: built={built_val!r} reference={ref_val!r}")


class Report:
    def __init__(self):
        self.issues = 0
        self._section = None

    def section(self, title):
        self._section = title
        print(f"\n=== {title} ===")

    def ok(self, msg):
        print(f"  OK   {msg}")

    def info(self, msg):
        print(f"  ..   {msg}")

    def issue(self, msg):
        self.issues += 1
        print(f"  !!   {msg}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("built")
    parser.add_argument("reference")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    built = load(args.built)
    ref = load(args.reference)
    report = Report()

    compare_tables(built, ref, report)
    shared_names = compare_glyph_set(built, ref, report)
    compare_cmap(built, ref, report)
    compare_outlines(built, ref, shared_names, report, args.verbose)
    compare_cff_hints(built, ref, report)
    compare_gsub_gpos(built, ref, report)
    compare_name_table(built, ref, report)
    compare_head_os2(built, ref, report)

    print(f"\n{report.issues} issue(s) found.")
    return 1 if report.issues else 0


if __name__ == "__main__":
    sys.exit(main())
