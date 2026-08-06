#!/usr/bin/env python3
"""Assembles a full Bravura release - the structure found in the Bravura
repository's redist/ folder: OTF and WOFF/WOFF2 versions of both Bravura
and Bravura Text, Bravura.json, and an updated FONTLOG.txt.

Invoked via `python3 tools/generate_font.py --generate-release`, not run
directly (it needs the working UFO/build machinery from generate_font.py
and generate_bravura_text.py). SVG font export is deliberately not
included - that legacy format has been deprecated.

FONTLOG.txt: if <output-dir>/FONTLOG.txt already exists (e.g. because
--output-dir points directly at a checkout of the Bravura repo's redist/
folder), a new dated changelog entry is appended to it, in place. If it
doesn't exist, a minimal new one is created. --fixed-issues lets you list
the GitHub issues this release closes (comma-separated, e.g.
"steinbergmedia/bravura#101,w3c-cg/smufl#42"); their titles are fetched via
`gh issue view` to build the changelog bullets. Without it, a placeholder
bullet is written reminding you to fill the entry in by hand.

Usage:
    python3 tools/generate_font.py --generate-release [--output-dir PATH]
        [--fixed-issues REF,REF,...] [--author NAME]
"""
import argparse
import datetime
import subprocess
import sys
from pathlib import Path

from fontTools.ttLib import TTFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import font_version  # tools/font_version.py
import generate_bravura_text
import generate_font
import generate_font_metadata

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = ROOT / "font" / "release"

FONTLOG_HEADER = """FONTLOG for the Bravura font
============================

This file provides detailed information on the Bravura Font Software. This information should be distributed along with the Bravura fonts and any derivative works.

The Bravura Font Software is a family consisting of two fonts, Bravura and Bravura Text.


Changelog
---------
"""


def build_format_variants(otf_path, target_dir, base_name):
    """Writes <base_name>.otf/.woff/.woff2 into target_dir/{otf,woff}/."""
    otf_dir = target_dir / "otf"
    woff_dir = target_dir / "woff"
    otf_dir.mkdir(parents=True, exist_ok=True)
    woff_dir.mkdir(parents=True, exist_ok=True)

    (otf_dir / f"{base_name}.otf").write_bytes(otf_path.read_bytes())

    for flavor, ext in (("woff", "woff"), ("woff2", "woff2")):
        ttfont = TTFont(otf_path)
        ttfont.flavor = flavor
        ttfont.save(woff_dir / f"{base_name}.{ext}")

    print(f"  {base_name}: otf, woff, woff2")


def fetch_issue_title(ref):
    """ref like 'steinbergmedia/bravura#101' or 'w3c-cg/smufl#42'."""
    if "#" not in ref:
        return None
    repo, number = ref.rsplit("#", 1)
    try:
        result = subprocess.run(
            ["gh", "issue", "view", number, "--repo", repo, "--json", "title", "-q", ".title"],
            capture_output=True, text=True, check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"warning: couldn't fetch title for {ref}: {e}", file=sys.stderr)
        return None


def build_changelog_entry(version_str, author, fixed_issues):
    today = datetime.date.today().strftime("%-d %B %Y")
    lines = [f"{today} ({author}) Bravura {version_str}"]
    if fixed_issues:
        for ref in fixed_issues:
            title = fetch_issue_title(ref)
            if title:
                lines.append(f"– Fixed {title} (see {ref})")
            else:
                lines.append(f"– See {ref}")
    else:
        lines.append("– TODO: describe what changed in this release")
    return "\n".join(lines)


def update_fontlog(output_dir, entry):
    fontlog_path = output_dir / "FONTLOG.txt"
    if fontlog_path.exists():
        text = fontlog_path.read_text()
        text = text.rstrip("\n") + "\n\n" + entry + "\n"
    else:
        text = FONTLOG_HEADER + "\n" + entry + "\n"
    fontlog_path.write_text(text)
    print(f"Updated {fontlog_path}")


def build_release(output_dir, fixed_issues=None, author="Daniel Spreadbury", keep_tmp=False):
    import shutil
    import tempfile

    output_dir.mkdir(parents=True, exist_ok=True)
    _, _, version_str = font_version.format_version()

    tmp_dir = Path(tempfile.mkdtemp(prefix="bravura-release-"))
    try:
        print("Building Bravura...")
        bravura_otf = generate_font.build_otf(tmp_dir / "bravura")
        build_format_variants(bravura_otf, output_dir, "Bravura")

        print("Building Bravura Text...")
        text_tmp = tmp_dir / "bravura-text"
        text_tmp.mkdir()
        text_otf = generate_bravura_text.build_otf(text_tmp)
        build_format_variants(text_otf, output_dir, "BravuraText")

        print("Building Bravura.json...")
        # Named to match the font, per the spec's own convention
        # (font-metadata-locations.md: ".../SMuFL/Fonts/<fontname>/<fontname>.json")
        # - the redist zip previously shipped this as "bravura_metadata.json",
        # which never matched what the spec (or Dorico's own bundled copy)
        # actually expects. See steinbergmedia/bravura#85.
        metadata = generate_font_metadata.build_metadata(bravura_otf)
        metadata_path = output_dir / "Bravura.json"
        import json
        metadata_path.write_text(json.dumps(metadata, indent=4, sort_keys=True))
        print(f"  wrote {metadata_path}")

        entry = build_changelog_entry(version_str, author, fixed_issues)
        update_fontlog(output_dir, entry)

        print(f"\nRelease {version_str} written to {output_dir}")
        return 0
    finally:
        if keep_tmp:
            print(f"(kept working directory: {tmp_dir})")
        else:
            shutil.rmtree(tmp_dir, ignore_errors=True)


def add_release_args(parser):
    parser.add_argument("--generate-release", action="store_true",
                         help="build a full release (Bravura + Bravura Text, all formats, "
                              "Bravura.json, FONTLOG.txt) instead of a single font")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR,
                         help="release output directory (default: font/release/). Point this "
                              "at a checkout of the Bravura repo's redist/ folder to update it directly.")
    parser.add_argument("--fixed-issues", type=str, default="",
                         help="comma-separated issue references this release closes, "
                              "e.g. steinbergmedia/bravura#101,w3c-cg/smufl#42")
    parser.add_argument("--author", type=str, default="Daniel Spreadbury")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_release_args(parser)
    parser.add_argument("--keep-tmp", action="store_true")
    args = parser.parse_args()

    fixed_issues = [s.strip() for s in args.fixed_issues.split(",") if s.strip()]
    return build_release(args.output_dir, fixed_issues, args.author, args.keep_tmp)


if __name__ == "__main__":
    sys.exit(main())
