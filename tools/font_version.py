#!/usr/bin/env python3
"""Shared helpers for the Bravura/Bravura Text build version - see
data/font-version.yaml for the scheme - and for the copyright year, which
both live here since both are build-time overrides applied to a working
UFO copy in place of whatever FontLab last wrote. Used by
tools/generate_font.py, tools/generate_bravura_text.py,
tools/generate_font_metadata.py, and tools/check_font_version.py.
"""
import datetime
import hashlib
import plistlib
import re
from pathlib import Path

import ufoLib2
import yaml

COPYRIGHT_YEAR_RE = re.compile(r"(Copyright © )\d{4}")
COPYRIGHT_FONTINFO_KEYS = ("copyright", "openTypeNameDescription", "openTypeNameLicense")

ROOT = Path(__file__).resolve().parent.parent
VERSION_PATH = ROOT / "data" / "font-version.yaml"
UFO_DIR = ROOT / "font" / "Bravura.ufo"

# Everything that materially affects the compiled fonts. font/Bravura.ufo's
# own fontinfo.plist is deliberately excluded - its version fields are
# overwritten at build time (see set_ufo_version below) and the rest of it
# is FontLab-managed metadata that isn't SMuFL-meaningful.
HASH_INPUTS = [
    ROOT / "data" / "engraving-defaults.yaml",
    ROOT / "data" / "bravura-text-transforms.yaml",
    ROOT / "data" / "ranges" / "combining-staff-positions.yaml",
    ROOT / "metadata" / "glyphnames.json",
    ROOT / "metadata" / "classes.json",
    ROOT / "metadata" / "font-optional-codepoints.json",
]


def load():
    return yaml.safe_load(VERSION_PATH.read_text())


def save(data):
    # Preserve simple, hand-editable formatting rather than round-tripping
    # through a generic YAML dumper (which would reflow the file's own
    # explanatory comments away).
    text = VERSION_PATH.read_text()
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        for key in ("stem", "build", "inputsHash"):
            if line.startswith(f"{key}:"):
                value = data[key]
                formatted = f'"{value}"' if isinstance(value, str) else str(value)
                lines[i] = f"{key}: {formatted}\n"
    VERSION_PATH.write_text("".join(lines))


def format_version(version_data=None):
    """Returns (versionMajor, versionMinor, version_str) e.g. (1, 480, "1.480").
    version_str is a string, not a float, deliberately - a float would
    silently drop a trailing zero for some build values (float("1.480")
    == 1.48). That's harmless for THIS scheme's 3-digit fraction (1.48
    and 1.480 are the same number, and no other valid build value
    collides with it), but keeping this as a string avoids relying on
    that being true - see data/font-version.yaml and
    steinbergmedia/bravura#102 for why the fraction is 3 digits, not 4."""
    data = version_data or load()
    major_str, minor_stem = data["stem"].split(".")
    minor_str = f"{minor_stem}{data['build']:02d}"
    return int(major_str), int(minor_str), f"{major_str}.{minor_str}"


def compute_inputs_hash():
    """A glyph that's empty (no contours, no components - i.e. a fresh
    placeholder tools/sync_ufo_glyphs.py just added for a new spec entry)
    is deliberately excluded: adding one isn't a material change to the
    font's output, only actually drawing something in it is. Its unicode/
    note/width would otherwise change the hash the moment sync_ufo_glyphs
    runs, forcing an unwanted version bump for a glyph nobody's designed
    yet."""
    hasher = hashlib.sha256()
    font = ufoLib2.Font.open(UFO_DIR)
    for glyph_name in sorted(font.keys()):
        glyph = font[glyph_name]
        if not glyph.contours and not glyph.components:
            continue
        hasher.update(glyph_name.encode())
        hasher.update(repr(glyph.width).encode())
        hasher.update(repr(sorted(glyph.unicodes)).encode())
        for contour in glyph.contours:
            hasher.update(repr([(p.x, p.y, p.type, p.smooth) for p in contour.points]).encode())
        for component in glyph.components:
            hasher.update(repr((component.baseGlyph, tuple(component.transformation))).encode())
        for anchor in sorted(glyph.anchors, key=lambda a: (a.name or "", a.x, a.y)):
            hasher.update(repr((anchor.name, anchor.x, anchor.y)).encode())
    hasher.update(font.features.text.encode())
    hasher.update(repr(sorted(font.kerning.items())).encode())
    hasher.update(repr(sorted((k, sorted(v)) for k, v in font.groups.items())).encode())

    for f in HASH_INPUTS:
        hasher.update(str(f.relative_to(ROOT)).encode())
        hasher.update(f.read_bytes())
    return hasher.hexdigest()


def set_ufo_version(font):
    """Overwrites an open UFO's version fields (ufoLib2 Font object) with
    the recorded data/font-version.yaml value, regardless of whatever
    FontLab last wrote there. openTypeNameVersion is what actually ends up
    in the compiled font's name-table "Version" string (nameID 5) -
    ufo2ft uses it directly rather than deriving it from versionMajor/
    versionMinor, so both need setting."""
    major, minor, version_str = format_version()
    font.info.versionMajor = major
    font.info.versionMinor = minor
    font.info.openTypeNameVersion = f"Version {version_str}"


def set_fontinfo_plist_version(fontinfo_path):
    """Same as set_ufo_version, but for a working copy manipulated at the
    plist-file level (plistlib) rather than through ufoLib2 - see
    tools/generate_font.py."""
    major, minor, version_str = format_version()
    fontinfo = plistlib.loads(fontinfo_path.read_bytes())
    fontinfo["versionMajor"] = major
    fontinfo["versionMinor"] = minor
    fontinfo["openTypeNameVersion"] = f"Version {version_str}"
    fontinfo_path.write_bytes(plistlib.dumps(fontinfo))


def set_ufo_copyright_year(font, year=None):
    """Updates the year in an open UFO's copyright-bearing fontinfo
    fields (ufoLib2 Font object) to the current year (or `year`), leaving
    everything else in each string untouched."""
    year = year or datetime.date.today().year
    for key in COPYRIGHT_FONTINFO_KEYS:
        value = getattr(font.info, key, None)
        if value:
            setattr(font.info, key, COPYRIGHT_YEAR_RE.sub(rf"\g<1>{year}", value, count=1))


def set_fontinfo_plist_copyright_year(fontinfo_path, year=None):
    """Same as set_ufo_copyright_year, but for a working copy manipulated
    at the plist-file level (plistlib) rather than through ufoLib2."""
    year = year or datetime.date.today().year
    fontinfo = plistlib.loads(fontinfo_path.read_bytes())
    for key in COPYRIGHT_FONTINFO_KEYS:
        value = fontinfo.get(key)
        if value:
            fontinfo[key] = COPYRIGHT_YEAR_RE.sub(rf"\g<1>{year}", value, count=1)
    fontinfo_path.write_bytes(plistlib.dumps(fontinfo))
