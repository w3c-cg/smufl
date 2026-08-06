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

Usage:
    python3 tools/generate_font.py [--output PATH] [--no-hint] [--keep-tmp]
"""
import argparse
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
    return working_ufo


def run(cmd, **kwargs):
    print(f"$ {' '.join(str(c) for c in cmd)}")
    subprocess.run(cmd, check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--metadata-output", type=Path, default=DEFAULT_METADATA_OUTPUT)
    parser.add_argument("--no-metadata", action="store_true", help="skip generating Bravura.json")
    parser.add_argument("--no-hint", action="store_true", help="skip the otfautohint pass")
    parser.add_argument("--keep-tmp", action="store_true", help="don't delete the working directory (for debugging)")
    args = parser.parse_args()

    if not UFO_DIR.exists():
        print(f"error: {UFO_DIR} not found", file=sys.stderr)
        return 1

    tmp_dir = Path(tempfile.mkdtemp(prefix="bravura-build-"))
    try:
        working_ufo = prepare_ufo(tmp_dir)

        unhinted_otf = tmp_dir / "Bravura-unhinted.otf"
        run([
            "fontmake", "-u", str(working_ufo), "-o", "otf",
            "--output-path", str(unhinted_otf), "--no-subroutinize",
        ])

        args.output.parent.mkdir(parents=True, exist_ok=True)
        if args.no_hint:
            shutil.copy(unhinted_otf, args.output)
        else:
            run(["otfautohint", "-o", str(args.output), str(unhinted_otf)])

        print(f"\nWrote {args.output.relative_to(ROOT) if args.output.is_relative_to(ROOT) else args.output}")

        if not args.no_metadata:
            metadata = generate_font_metadata.build_metadata(args.output)
            args.metadata_output.parent.mkdir(parents=True, exist_ok=True)
            args.metadata_output.write_text(json.dumps(metadata, indent=4, sort_keys=True))
            print(f"Wrote {args.metadata_output.relative_to(ROOT) if args.metadata_output.is_relative_to(ROOT) else args.metadata_output}")

        return 0
    finally:
        if args.keep_tmp:
            print(f"(kept working directory: {tmp_dir})")
        else:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
