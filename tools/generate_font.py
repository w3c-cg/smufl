#!/usr/bin/env python3
"""Compile Bravura.otf from font/Bravura.ufo - the validated open-source
pipeline: fontmake (UFO -> CFF OTF) followed by otfautohint (AFDKO's
standalone CFF autohinter, operating directly on the compiled OTF).

Bravura.ufo (FontLab's own export) carries the design - outlines, kerning,
SMuFL anchors, salt/ssNN substitution features - but not the GDEF glyph
classification ufo2ft needs to emit ligature caret/class info, since that's
derived data rather than something a font designer hand-authors. This script
injects public.openTypeCategories (ligature glyphs only - see
tools/generate.py's build_font_glyph_index) into a throwaway copy of the UFO
before compiling, so the committed Bravura.ufo never needs to carry it.

Also adds a dummy (zero-signature) DSIG table after compiling - see
tools/font_build_common.py - matching what previous FontLab-built releases
carried.

Usage:
    python3 tools/generate_font.py [--output PATH] [--no-hint] [--keep-tmp]
"""
import argparse
import datetime
import json
import plistlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate  # tools/generate.py
import generate_font_metadata  # tools/generate_font_metadata.py
import font_version  # tools/font_version.py
import font_build_common  # tools/font_build_common.py

from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
UFO_DIR = ROOT / "font" / "Bravura.ufo"
DEFAULT_OUTPUT = ROOT / "font" / "Bravura.otf"
DEFAULT_METADATA_OUTPUT = ROOT / "font" / "Bravura.json"


def ligature_glyph_names():
    sources = generate.Sources()
    merged_glyphnames, _, _ = generate.merge_metadata(sources)
    index = generate.build_font_glyph_index(sources, merged_glyphnames)
    return [name for name, info in index.items() if info["category"] == "ligature"]


def prepare_ufo(tmp_dir):
    """Copies Bravura.ufo into tmp_dir and injects GDEF categorisation.
    Returns the path to the working copy."""
    working_ufo = tmp_dir / "Bravura.ufo"
    shutil.copytree(UFO_DIR, working_ufo)

    lig_names = ligature_glyph_names()
    ufo_glyph_names = set()
    contents = (working_ufo / "glyphs" / "contents.plist").read_bytes()
    ufo_glyph_names = set(plistlib.loads(contents).keys())
    missing = [n for n in lig_names if n not in ufo_glyph_names]
    if missing:
        print(f"warning: {len(missing)} ligature glyph(s) from the spec are not in "
              f"Bravura.ufo yet (run tools/sync_ufo_glyphs.py): {missing[:5]}"
              + (" ..." if len(missing) > 5 else ""))

    lib_path = working_ufo / "lib.plist"
    lib = plistlib.loads(lib_path.read_bytes()) if lib_path.exists() else {}
    lib["public.openTypeCategories"] = {
        n: "ligature" for n in lig_names if n in ufo_glyph_names
    }
    lib_path.write_bytes(plistlib.dumps(lib))

    print(f"Classified {len(lib['public.openTypeCategories'])} ligature glyph(s) for GDEF")

    fontinfo_path = working_ufo / "fontinfo.plist"
    font_version.set_fontinfo_plist_version(fontinfo_path)
    font_version.set_fontinfo_plist_copyright_year(fontinfo_path)
    _, _, version = font_version.format_version()
    print(f"Set font version to {version}, copyright year to {datetime.date.today().year}")

    return working_ufo


def run(cmd, **kwargs):
    print(f"$ {' '.join(str(c) for c in cmd)}")
    subprocess.run(cmd, check=True, **kwargs)


def relpath(path):
    return path.relative_to(ROOT) if path.is_relative_to(ROOT) else path


def build_otf(tmp_dir, no_hint=False):
    """Compiles Bravura.otf into tmp_dir and returns its path. Doesn't
    manage tmp_dir's lifecycle - the caller owns cleanup, since
    tools/generate_release.py needs the working directory (and the UFO
    inside it) to stick around afterwards to derive SVG/WOFF/WOFF2 from
    the same compile without redoing it."""
    working_ufo = prepare_ufo(tmp_dir)

    unhinted_otf = tmp_dir / "Bravura-unhinted.otf"
    run([
        "fontmake", "-u", str(working_ufo), "-o", "otf",
        "--output-path", str(unhinted_otf), "--no-subroutinize",
    ])

    if no_hint:
        final_otf = unhinted_otf
    else:
        final_otf = tmp_dir / "Bravura.otf"
        run(["otfautohint", "-o", str(final_otf), str(unhinted_otf)])

    ttfont = TTFont(final_otf)
    font_build_common.add_dummy_dsig(ttfont)
    ttfont.save(final_otf)
    print("Added DSIG table")

    return final_otf


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--metadata-output", type=Path, default=DEFAULT_METADATA_OUTPUT)
    parser.add_argument("--no-metadata", action="store_true", help="skip generating Bravura.json")
    parser.add_argument("--no-hint", action="store_true", help="skip the otfautohint pass")
    parser.add_argument("--keep-tmp", action="store_true", help="don't delete the working directory (for debugging)")

    import generate_release  # tools/generate_release.py
    generate_release.add_release_args(parser)

    args = parser.parse_args()

    if not UFO_DIR.exists():
        print(f"error: {UFO_DIR} not found", file=sys.stderr)
        return 1

    if args.generate_release:
        fixed_issues = [s.strip() for s in args.fixed_issues.split(",") if s.strip()]
        return generate_release.build_release(args.output_dir, fixed_issues, args.author, args.keep_tmp)

    tmp_dir = Path(tempfile.mkdtemp(prefix="bravura-build-"))
    try:
        otf_path = build_otf(tmp_dir, no_hint=args.no_hint)

        args.output.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(otf_path, args.output)
        print(f"\nWrote {relpath(args.output)}")

        if not args.no_metadata:
            metadata = generate_font_metadata.build_metadata(args.output)
            args.metadata_output.parent.mkdir(parents=True, exist_ok=True)
            args.metadata_output.write_text(json.dumps(metadata, indent=4, sort_keys=True))
            print(f"Wrote {relpath(args.metadata_output)}")

        return 0
    finally:
        if args.keep_tmp:
            print(f"(kept working directory: {tmp_dir})")
        else:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
