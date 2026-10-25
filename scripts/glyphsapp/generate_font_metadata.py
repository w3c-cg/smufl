#MenuTitle: Export SMuFL Metadata JSON
# -*- coding: utf-8 -*-
"""
Export SMuFL font-specific metadata JSON from the font currently open in
Glyphs 4.

Supported sections (written when reliable data exists):
  fontName, fontVersion, designSize, sizeRange, engravingDefaults,
  glyphAdvanceWidths, glyphsWithAnchors, glyphsWithAlternates,
  glyphBBoxes, ligatures, sets, optionalGlyphs.

The script reads (and never writes) the Glyphs font project. It extracts
font-level values and SMuFL data from one master, converts font units to
staff spaces, merges a sidecar configuration / metadataSource, validates
the result, and only then writes the output file atomically.

Run from Glyphs 4:  Script > Export SMuFL Metadata JSON
Documentation:      see README.md next to this file.

Copyright / license: the script is provided as-is for use with Glyphs.
The bundled smufl_glyphnames.json is derived from the official SMuFL
repository (https://github.com/w3c-cg/smufl) and retains its provenance.
"""

from __future__ import annotations

import json
import math
import os
import re
import site
import sys
import tempfile
import time
import traceback
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

# ---------------------------------------------------------------------------
# Constants from the current SMuFL specification
# ---------------------------------------------------------------------------

#: Human-readable snapshot marker.  The actual canonical name list lives in
#: smufl_glyphnames.json, which can be replaced with a newer official
#: metadata/glyphnames.json without editing the code.
GLYPHNAMES_FILENAME = "smufl_glyphnames.json"
OPTIONAL_REFERENCE_FILENAME = "smufl_optional_reference.json"
SETS_TEMPLATE_FILENAME = "smufl_sets_template.json"

try:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
except NameError:  # Glyphs may execute a script without defining __file__.
    SCRIPT_DIR = os.getcwd()

DEBUG_LOG_PATH = os.environ.get("SMUFL_DEBUG_LOG") or os.path.join(
    os.path.expanduser("~"), "Library", "Logs", "SMuFLMetadataExporter.log"
)


def _debug(message: str) -> None:
    """Append a diagnostic line; never let logging break the export."""
    if os.environ.get("SMUFL_DEBUG_LOG") == "0":
        return
    try:
        folder = os.path.dirname(DEBUG_LOG_PATH)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(DEBUG_LOG_PATH, "a", encoding="utf-8") as handle:
            handle.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {message}\n")
    except Exception:
        pass


_debug("module imported")
_debug(
    f"python={sys.executable}; version={sys.version.split()[0]}; "
    f"user_site={site.ENABLE_USER_SITE}; paths={sys.path}"
)

#: Anchor names that SMuFL defines as Cartesian coordinate pairs.
#:
#: stemUpNW / stemDownSW are listed here because Bravura 1.482 and the
#: official tools/generate_font_metadata.py emit them as [x, y] pairs even
#: though the specification text describes them as a scalar extension
#: amount.  See ASSUMPTIONS.md.  nominalWidth is genuinely scalar and is
#: therefore deliberately *not* read from a point anchor.
POINT_ANCHORS: frozenset = frozenset({
    "splitStemUpSE",
    "splitStemUpSW",
    "splitStemDownNE",
    "splitStemDownNW",
    "stemUpSE",
    "stemDownNW",
    "stemUpNW",
    "stemDownSW",
    "numeralTop",
    "numeralBottom",
    "cutOutNE",
    "cutOutSE",
    "cutOutSW",
    "cutOutNW",
    "graceNoteSlashSW",
    "graceNoteSlashNE",
    "graceNoteSlashNW",
    "graceNoteSlashSE",
    "repeatOffset",
    "noteheadOrigin",
    "opticalCenter",
})

#: Anchors whose specification text describes a single number.
SCALAR_ANCHORS: frozenset = frozenset({
    "nominalWidth",
})

#: Anchors for which both a pair and a scalar are tolerated in manual
#: configuration (the reference implementation uses pairs).
HYBRID_ANCHORS: frozenset = frozenset({
    "stemUpNW",
    "stemDownSW",
})

SUPPORTED_ANCHORS: frozenset = POINT_ANCHORS | SCALAR_ANCHORS

#: All documented engravingDefaults keys.  Values are in staff spaces.
ENGRAVING_NUMERIC_KEYS: frozenset = frozenset({
    "arrowShaftThickness",
    "barlineSeparation",
    "beamSpacing",
    "beamThickness",
    "bracketThickness",
    "dashedBarlineDashLength",
    "dashedBarlineGapLength",
    "dashedBarlineThickness",
    "hBarThickness",
    "hairpinThickness",
    "legerLineExtension",
    "legerLineThickness",
    "lyricLineThickness",
    "octaveLineThickness",
    "pedalLineThickness",
    "repeatBarlineDotSeparation",
    "repeatEndingLineThickness",
    "slurEndpointThickness",
    "slurMidpointThickness",
    "staffLineThickness",
    "stemThickness",
    "subBracketThickness",
    "textEnclosureThickness",
    "thickBarlineThickness",
    "thinBarlineThickness",
    "thinThickBarlineSeparation",
    "tieEndpointThickness",
    "tieMidpointThickness",
    "tupletBracketThickness",
})
ENGRAVING_TEXT_KEY = "textFontFamily"
ENGRAVING_KEYS: frozenset = ENGRAVING_NUMERIC_KEYS | {ENGRAVING_TEXT_KEY}

#: SMuFL engravingDefaults -> (target Unicode, measuring rule).
#: Ported from SMufoLib's calculateEngravingDefaults / rulers.py, adapted to
#: Glyphs 4 layer.paths nodes. All values are measured from the selected
#: master and converted to staff spaces.
ENGRAVING_DEFAULT_MAPPING: Dict[str, Tuple[str, str]] = {
    "arrowShaftThickness": ("EB60", "xStrokeWidthAtOrigin"),
    "barlineSeparation": ("E031", "xDistanceBetweenContours"),
    "beamSpacing": ("E1F9", "yDistanceBetweenContours"),
    "beamThickness": ("E1F7", "glyphBoundsHeight"),
    "bracketThickness": ("E003", "xStrokeWidthAtOrigin"),
    "dashedBarlineDashLength": ("E036", "yStrokeWidthAtMinimum"),
    "dashedBarlineGapLength": ("E036", "yDistanceBetweenContours"),
    "dashedBarlineThickness": ("E036", "glyphBoundsWidth"),
    "hairpinThickness": ("E53E", "wedgeArmStrokeWidth"),
    "hBarThickness": ("E4F0", "yStrokeWidthAtMinimum"),
    "legerLineExtension": ("E022", "glyphBoundsXMinAbs"),
    "legerLineThickness": ("E022", "glyphBoundsHeight"),
    "lyricLineThickness": ("E010", "glyphBoundsHeight"),
    "octaveLineThickness": ("E010", "glyphBoundsHeight"),
    "pedalLineThickness": ("E010", "glyphBoundsHeight"),
    "repeatBarlineDotSeparation": ("E040", "xDistanceStemToDot"),
    "repeatEndingLineThickness": ("E030", "xStrokeWidthAtOrigin"),
    "slurEndpointThickness": ("E1FD", "xStrokeWidthAtOrigin"),
    "slurMidpointThickness": ("E1FD", "yStrokeWidthAtMinimum"),
    "staffLineThickness": ("E010", "glyphBoundsHeight"),
    "stemThickness": ("E210", "glyphBoundsWidth"),
    "subBracketThickness": ("E030", "xStrokeWidthAtOrigin"),
    "textEnclosureThickness": ("E010", "glyphBoundsHeight"),
    "thickBarlineThickness": ("E034", "glyphBoundsWidth"),
    "thinBarlineThickness": ("E030", "glyphBoundsWidth"),
    "thinThickBarlineSeparation": ("E032", "xDistanceBetweenContours"),
    "tieEndpointThickness": ("E1FD", "xStrokeWidthAtOrigin"),
    "tieMidpointThickness": ("E1FD", "yStrokeWidthAtMinimum"),
    "tupletBracketThickness": ("E1FE", "xStrokeWidthAtOrigin"),
}

#: Optional glyphs are the SMuFL private-use block allocated for them.
OPTIONAL_GLYPH_MIN = 0xF400
OPTIONAL_GLYPH_MAX = 0xF8FF

#: A Glyphs glyph name that carries no SMuFL semantics.  These are the only
#: non-canonical names for which a Unicode fallback is attempted.
GENERIC_GLYPH_NAME_RE = re.compile(r"^(?:uni[0-9A-Fa-f]{4,6}|glyph[0-9]+)$")

#: Names usable as keys in optionalGlyphs / glyphsWithAnchors for optional
#: glyphs.  Kept deliberately conservative (no dots, spaces, or leading
#: digits); names that fail are reported and skipped.
OPTIONAL_GLYPH_NAME_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_+]*$")

CODEPOINT_RE = re.compile(r"^U\+[0-9A-F]{4,6}$")

#: OpenType feature tags whose single substitutions become SMuFL alternates.
ALTERNATE_FEATURE_RE = re.compile(r"^(?:salt|cv\d{2}|ss\d{2})$")
#: OpenType feature tags whose multi-glyph substitutions become SMuFL ligatures.
LIGATURE_FEATURE_TAGS = frozenset({"liga", "dlig", "clig", "rlig"})
#: SMuFL stylistic set tag.
SET_FEATURE_RE = re.compile(r"^ss\d{2}$")

#: Combined alternate name suffix used by UFO/SMuFL tooling.
ALTERNATE_SUFFIX_RE = re.compile(r"^(?P<base>.+)\.(?P<tag>salt|ss|cv)(?P<num>\d{2})$")

#: The Glyphs data table renames these two canonical SMuFL names because
#: Glyphs does not accept glyph names beginning with a digit.
#: (See GLYPHS_SAFE_NAMES in tools/smufl_common.py.)
BUILTIN_GLYPH_ALIASES: Dict[str, str] = {
    "fourStringTabClef": "4stringTabClef",
    "sixStringTabClef": "6stringTabClef",
}

TOP_LEVEL_KEYS: frozenset = frozenset({
    "fontName",
    "fontVersion",
    "designSize",
    "sizeRange",
    "engravingDefaults",
    "glyphAdvanceWidths",
    "glyphsWithAnchors",
    "glyphsWithAlternates",
    "glyphBBoxes",
    "ligatures",
    "sets",
    "optionalGlyphs",
})

#: 用户要求的固定输出顺序；同时保持嵌套字典键排序，便于 diff。
TOP_LEVEL_ORDER: Tuple[str, ...] = (
    "fontName",
    "fontVersion",
    "designSize",
    "sizeRange",
    "engravingDefaults",
    "glyphAdvanceWidths",
    "glyphsWithAnchors",
    "glyphsWithAlternates",
    "glyphBBoxes",
    "ligatures",
    "sets",
    "optionalGlyphs",
)

CONFIG_KEYS: frozenset = frozenset({
    "_comment",
    "fontName",
    "fontVersion",
    "designSize",
    "sizeRange",
    "engravingDefaults",
    "master",
    "metadataSource",
    "setsTemplate",
    "includeGlyphBBoxes",
    "includeGlyphAdvanceWidths",
    "includeGlyphsWithAlternates",
    "includeLigatures",
    "includeSets",
    "includeOptionalGlyphs",
    "includeEngravingDefaults",
    "glyphNameAliases",
    "glyphsWithAnchors",
})


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

@dataclass
class Issue:
    level: str          # "error", "warning", "info"
    code: str
    message: str


@dataclass
class Report:
    """Collects diagnostics without aborting the first time something is odd."""

    issues: List[Issue] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)
    _seen: Set[Tuple[str, str, str]] = field(default_factory=set)

    def add(self, level: str, code: str, message: str) -> None:
        key = (level, code, message)
        if key in self._seen:
            return
        self._seen.add(key)
        self.issues.append(Issue(level, code, message))

    def error(self, code: str, message: str) -> None:
        self.add("error", code, message)

    def warn(self, code: str, message: str) -> None:
        self.add("warning", code, message)

    def info(self, code: str, message: str) -> None:
        self.add("info", code, message)

    def incr(self, key: str, amount: int = 1) -> None:
        self.stats[key] = self.stats.get(key, 0) + amount

    @property
    def errors(self) -> List[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> List[Issue]:
        return [i for i in self.issues if i.level == "warning"]

    @property
    def infos(self) -> List[Issue]:
        return [i for i in self.issues if i.level == "info"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def merge(self, other: "Report") -> None:
        for issue in other.issues:
            self.add(issue.level, issue.code, issue.message)
        for key, value in other.stats.items():
            self.incr(key, value)
        self._seen |= other._seen


# ---------------------------------------------------------------------------
# SMuFL canonical-name data
# ---------------------------------------------------------------------------

@dataclass
class GlyphNameData:
    glyphs: Dict[str, Dict[str, Any]]
    canonical_names: frozenset
    codepoint_to_names: Dict[str, Tuple[str, ...]]
    source: str

    def codepoint_of(self, name: str) -> Optional[str]:
        entry = self.glyphs.get(name)
        return entry.get("codepoint") if entry else None

    def description_of(self, name: str) -> Optional[str]:
        entry = self.glyphs.get(name)
        value = entry.get("description") if entry else None
        return value if isinstance(value, str) and value.strip() else None

    def classes_of(self, name: str) -> List[str]:
        entry = self.glyphs.get(name)
        value = entry.get("classes") if entry else None
        if isinstance(value, list):
            return [str(v) for v in value if isinstance(v, str) and v]
        return []


def _normalise_codepoint(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, int) and not isinstance(value, bool):
        if 0 <= value <= 0x10FFFF:
            return "U+%04X" % value
        return None
    if not isinstance(value, str):
        # PyObjC NSNumber / NSString-like values.
        try:
            number = int(value)
        except Exception:
            return None
        if 0 <= number <= 0x10FFFF:
            return "U+%04X" % number
        return None
    text = value.strip().upper()
    if text.startswith("U+"):
        text = text[2:]
    elif text.startswith("0X"):
        text = text[2:]
    text = text.replace(" ", "")
    if not re.fullmatch(r"[0-9A-F]{4,6}", text):
        return None
    return "U+" + text.zfill(4)


def _find_glyphnames_file(script_dir: str) -> Optional[str]:
    env_path = os.environ.get("SMUFL_GLYPHNAMES_PATH")
    candidates = []
    if env_path:
        candidates.append(env_path)
    candidates.append(os.path.join(script_dir, GLYPHNAMES_FILENAME))
    for path in candidates:
        if path and os.path.isfile(path):
            return path
    return None


def _fallback_glyphdata_xml_paths(script_dir: str, font: Any = None) -> List[str]:
    """Locations where an installed GlyphData-SMuFL.xml file may live."""
    paths: List[str] = []
    env_path = os.environ.get("SMUFL_GLYPHDATA_XML")
    if env_path:
        paths.append(env_path)
    paths.append(os.path.join(script_dir, "Info", "GlyphData-SMuFL.xml"))
    paths.append(os.path.join(
        os.path.expanduser("~"), "Library", "Application Support",
        "Glyphs 4", "Info", "GlyphData-SMuFL.xml"))
    if font is not None:
        try:
            fp = str(font.filepath or "")
        except Exception:
            fp = ""
        if fp:
            folder = os.path.dirname(fp)
            paths.append(os.path.join(folder, "Info", "GlyphData-SMuFL.xml"))
            parent = os.path.dirname(folder)
            paths.append(os.path.join(parent, "Info", "GlyphData-SMuFL.xml"))
    seen: Set[str] = set()
    return [p for p in paths if p and not (p in seen or seen.add(p))]


def _load_glyphnames_from_xml(path: str) -> Optional[GlyphNameData]:
    try:
        import xml.etree.ElementTree as ET
        root = ET.parse(path).getroot()
    except Exception:
        return None
    glyphs: Dict[str, Dict[str, Any]] = {}
    for node in root.iter("glyph"):
        name = node.get("name")
        unicode_value = node.get("unicode")
        if not name or not unicode_value:
            continue
        # A few GlyphData entries list several code points; use the first.
        codepoints = [p for p in re.split(r"[, ]+", unicode_value) if p]
        entry: Dict[str, Any] = {}
        primary = _normalise_codepoint(codepoints[0]) if codepoints else None
        if primary:
            entry["codepoint"] = primary
        if len(codepoints) > 1:
            alt = _normalise_codepoint(codepoints[1])
            if alt:
                entry["alternateCodepoint"] = alt
        if entry:
            glyphs[name] = entry
    if not glyphs:
        return None
    return _build_glyphname_data(glyphs, path + " (XML fallback)")


def _build_glyphname_data(glyphs: Dict[str, Dict[str, Any]], source: str) -> GlyphNameData:
    cp_to_names: Dict[str, List[str]] = {}
    for name, entry in glyphs.items():
        for key in ("codepoint", "alternateCodepoint"):
            cp = _normalise_codepoint(entry.get(key))
            if cp is None:
                continue
            entry[key] = cp
            cp_to_names.setdefault(cp, [])
            if name not in cp_to_names[cp]:
                cp_to_names[cp].append(name)
        description = entry.get("description")
        if isinstance(description, str) and description.strip():
            entry["description"] = description.strip()
        else:
            entry.pop("description", None)
        classes = entry.get("classes")
        if isinstance(classes, list):
            entry["classes"] = [str(c) for c in classes if isinstance(c, str) and c]
        else:
            entry.pop("classes", None)
    return GlyphNameData(
        glyphs=glyphs,
        canonical_names=frozenset(glyphs),
        codepoint_to_names={cp: tuple(names) for cp, names in cp_to_names.items()},
        source=source,
    )


def load_glyphnames(
    script_dir: str,
    font: Any = None,
    report: Optional[Report] = None,
    path_override: Optional[str] = None,
) -> Optional[GlyphNameData]:
    """Load the canonical SMuFL glyph-name list.

    Preference order:
      1. SMUFL_GLYPHNAMES_PATH / smufl_glyphnames.json next to this script
      2. a compact official metadata/glyphnames.json-shaped file
      3. GlyphData-SMuFL.xml from an installed SMuFL data package

    The XML fallback only contains SMuFL 1.5 core glyphs, so it is enough to
    validate core anchors but not optional glyphs.  It is intentionally only
    a fallback; the bundled JSON should be shipped with the script.
    """
    report = report or Report()
    path = path_override or _find_glyphnames_file(script_dir)
    if path:
        try:
            with open(path, "r", encoding="utf-8") as handle:
                raw = json.load(handle)
        except Exception as exc:
            report.error("glyphnames-load", f"Could not read {path}: {exc}")
            return None
        if isinstance(raw, dict) and isinstance(raw.get("glyphs"), dict):
            glyphs = raw["glyphs"]
        elif isinstance(raw, dict):
            # Official metadata/glyphnames.json: key -> {codepoint, ...}
            glyphs = raw
        else:
            report.error("glyphnames-shape", f"{path} is not a JSON object.")
            return None
        cleaned: Dict[str, Dict[str, Any]] = {}
        for name, entry in glyphs.items():
            if not isinstance(name, str) or not name:
                continue
            if isinstance(entry, str):
                entry = {"codepoint": entry}
            if not isinstance(entry, dict):
                continue
            item: Dict[str, Any] = {}
            cp = _normalise_codepoint(entry.get("codepoint"))
            if cp:
                item["codepoint"] = cp
            alt = _normalise_codepoint(entry.get("alternateCodepoint"))
            if alt:
                item["alternateCodepoint"] = alt
            description = entry.get("description")
            if isinstance(description, str) and description.strip():
                item["description"] = description.strip()
            classes = entry.get("classes")
            if isinstance(classes, list):
                item["classes"] = [str(c) for c in classes if isinstance(c, str) and c]
            if item:
                cleaned[name] = item
        if not cleaned:
            report.error("glyphnames-empty", f"No usable glyph names in {path}.")
            return None
        data = _build_glyphname_data(cleaned, path)
        report.info("glyphnames", f"Loaded {len(data.glyphs)} canonical names from {path}.")
        return data

    for xml_path in _fallback_glyphdata_xml_paths(script_dir, font):
        if os.path.isfile(xml_path):
            data = _load_glyphnames_from_xml(xml_path)
            if data:
                report.warn(
                    "glyphnames-fallback",
                    "Bundled smufl_glyphnames.json was not found; using "
                    f"{xml_path}. Optional-glyph validation may be incomplete. "
                    "Ship smufl_glyphnames.json next to the script for full "
                    "canonical-name coverage.",
                )
                return data

    report.error(
        "glyphnames-missing",
        "Could not find smufl_glyphnames.json next to the script (or a "
        "GlyphData-SMuFL.xml fallback). Copy smufl_glyphnames.json into the "
        "same folder as this script.",
    )
    return None


def _load_reference_json(script_dir: str, filename: str, wrapper_key: str,
                         env_var: str, report: Report) -> Dict[str, Any]:
    path = os.environ.get(env_var) or os.path.join(script_dir, filename)
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except Exception as exc:
        report.warn("reference-load", f"Could not read {path}: {exc}")
        return {}
    if isinstance(raw, dict) and isinstance(raw.get(wrapper_key), dict):
        return raw[wrapper_key]
    return raw if isinstance(raw, dict) else {}


def load_optional_reference(script_dir: str, report: Report) -> Dict[str, Dict[str, Any]]:
    """Optional name -> {codepoint, description, classes} reference data."""
    raw = _load_reference_json(
        script_dir, OPTIONAL_REFERENCE_FILENAME, "glyphs",
        "SMUFL_OPTIONAL_REFERENCE_PATH", report)
    if isinstance(raw.get("optionalGlyphs"), dict):
        raw = raw["optionalGlyphs"]
    result: Dict[str, Dict[str, Any]] = {}
    for name, entry in raw.items():
        if not isinstance(name, str) or not isinstance(entry, dict):
            continue
        item: Dict[str, Any] = {}
        cp = _normalise_codepoint(entry.get("codepoint"))
        if cp:
            item["codepoint"] = cp
        if isinstance(entry.get("description"), str) and entry["description"].strip():
            item["description"] = entry["description"].strip()
        if isinstance(entry.get("classes"), list):
            item["classes"] = [str(c) for c in entry["classes"] if isinstance(c, str) and c]
        if item:
            result[name] = item
    if result:
        report.info("optional-reference", f"Loaded {len(result)} optional-glyph reference entries.")
    return result


def load_sets_template(script_dir: str, config: Dict[str, Any], report: Report) -> Dict[str, Dict[str, str]]:
    """Set tag -> {type, description}, bundled Bravura template + config overrides."""
    raw = _load_reference_json(
        script_dir, SETS_TEMPLATE_FILENAME, "sets",
        "SMUFL_SETS_TEMPLATE_PATH", report)
    result: Dict[str, Dict[str, str]] = {}
    for tag, entry in raw.items():
        if isinstance(tag, str) and isinstance(entry, dict):
            item = {}
            for key in ("type", "description"):
                value = entry.get(key)
                if isinstance(value, str) and value.strip():
                    item[key] = value.strip()
            if item:
                result[tag] = item
    overrides = config.get("setsTemplate") or {}
    if not isinstance(overrides, dict):
        report.error("setsTemplate", "'setsTemplate' must be an object mapping ssNN tags to {type, description}.")
    else:
        for tag, entry in overrides.items():
            if not isinstance(tag, str) or not re.fullmatch(r"ss\d{2}", tag):
                report.error("setsTemplate", f"Invalid setsTemplate tag {tag!r}; expected ssNN.")
                continue
            if not isinstance(entry, dict):
                report.error("setsTemplate", f"setsTemplate.{tag} must be an object.")
                continue
            item = dict(result.get(tag, {}))
            for key in ("type", "description"):
                value = entry.get(key)
                if isinstance(value, str) and value.strip():
                    item[key] = value.strip()
            if "type" not in item or "description" not in item:
                report.error("setsTemplate", f"setsTemplate.{tag} needs non-empty type and description.")
                continue
            result[tag] = item
    if result:
        report.info("sets-template", f"Loaded {len(result)} stylistic-set templates.")
    return result


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

def default_config_path(font: Any) -> Optional[str]:
    """Return <font-stem>.smufl-config.json next to the .glyphs file."""
    try:
        filepath = str(font.filepath or "")
    except Exception:
        filepath = ""
    if not filepath:
        return None
    stem, ext = os.path.splitext(filepath)
    if ext.lower() not in (".glyphs", ".glyphspackage"):
        stem = filepath.rstrip("/\\")
    return stem + ".smufl-config.json"


def load_config(path: Optional[str], report: Report, warn_missing: bool = True) -> Dict[str, Any]:
    if not path:
        return {}
    if not os.path.isfile(path):
        if warn_missing:
            report.warn("config-missing", f"Configuration file not found: {path}")
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = json.load(handle)
    except Exception as exc:
        report.error("config-load", f"Could not read configuration {path}: {exc}")
        return {}
    if not isinstance(raw, dict):
        report.error("config-shape", f"Configuration {path} must be a JSON object.")
        return {}
    unknown = sorted(set(raw) - CONFIG_KEYS)
    if unknown:
        report.error(
            "config-keys",
            "Unknown configuration key(s): " + ", ".join(unknown) +
            ". Known keys: " + ", ".join(sorted(CONFIG_KEYS - {"_comment"})),
        )
    config = {k: v for k, v in raw.items() if k in CONFIG_KEYS and k != "_comment"}
    report.info("config", f"Using configuration {path}.")
    return config


def load_metadata_source(config: Dict[str, Any], font: Any, report: Report) -> Dict[str, Any]:
    """Load an optional previous/source metadata JSON for non-derivable values.

    Used for engravingDefaults, designSize, sizeRange and as a fallback for
    descriptions/classes.  It is never modified.
    """
    value = config.get("metadataSource")
    if value is None:
        return {}
    if not isinstance(value, str) or not value.strip():
        report.error("metadataSource", "'metadataSource' must be a path string.")
        return {}
    path = value.strip()
    if not os.path.isabs(path):
        try:
            filepath = str(font.filepath or "")
        except Exception:
            filepath = ""
        base = os.path.dirname(filepath) if filepath else os.getcwd()
        path = os.path.join(base, path)
    if not os.path.isfile(path):
        report.warn("metadataSource-missing", f"metadataSource file not found: {path}")
        return {}
    try:
        with open(path, "r", encoding="utf-8-sig") as handle:
            raw = json.load(handle)
    except Exception as exc:
        report.error("metadataSource-load", f"Could not read metadataSource {path}: {exc}")
        return {}
    if not isinstance(raw, dict):
        report.error("metadataSource-shape", f"metadataSource {path} must be a JSON object.")
        return {}
    report.info("metadataSource", f"Using source metadata {path} for fallback values.")
    return raw


# ---------------------------------------------------------------------------
# Glyphs API helpers (written to tolerate Glyphs 3/4 small differences)
# ---------------------------------------------------------------------------

def _master_list(font: Any) -> List[Any]:
    try:
        return list(font.masters)
    except Exception:
        return []


def select_master(font: Any, config: Dict[str, Any], report: Report) -> Optional[Any]:
    masters = _master_list(font)
    if not masters:
        report.error("master-none", "The font has no masters.")
        return None
    wanted = config.get("master")
    if wanted is not None:
        if not isinstance(wanted, str) or not wanted.strip():
            report.error("master-config", "'master' must be a master name or ID string.")
            return None
        wanted = wanted.strip()
        by_id = [m for m in masters if str(getattr(m, "id", "")) == wanted]
        if len(by_id) == 1:
            return by_id[0]
        by_name = [m for m in masters if str(getattr(m, "name", "")) == wanted]
        if len(by_name) == 1:
            return by_name[0]
        if len(by_name) > 1:
            report.error(
                "master-ambiguous",
                f"Master name '{wanted}' matches {len(by_name)} masters; use the master ID instead.",
            )
        else:
            report.error(
                "master-not-found",
                f"Master '{wanted}' was not found. Available masters: " +
                ", ".join(f"{getattr(m, 'name', '?')} ({getattr(m, 'id', '?')})" for m in masters),
            )
        return None
    master = masters[0]
    if len(masters) > 1:
        report.warn(
            "master-default",
            f"The font has {len(masters)} masters; anchors were read from the "
            f"first master '{getattr(master, 'name', '?')}' only. No coordinates "
            "from other masters are mixed. Set \"master\" in the configuration "
            "to choose a different master.",
        )
    return master


def _layer_for_master(glyph: Any, master: Any) -> Optional[Any]:
    master_id = getattr(master, "id", None)
    if master_id is None:
        return None
    layer_for_id = getattr(glyph, "layerForId_", None)
    if callable(layer_for_id):
        try:
            return layer_for_id(master_id)
        except Exception:
            pass
    layers = getattr(glyph, "layers", None)
    if layers is not None:
        try:
            return layers[master_id]
        except Exception:
            return None
    return None


def _anchor_items(layer: Any) -> List[Tuple[str, Any]]:
    anchors = getattr(layer, "anchors", None)
    if anchors is None:
        return []
    items_method = getattr(anchors, "items", None)
    if callable(items_method):
        try:
            return [(str(name), anchor) for name, anchor in items_method()]
        except Exception:
            pass
    result: List[Tuple[str, Any]] = []
    try:
        for anchor in anchors:
            if isinstance(anchor, str):
                try:
                    anchor = anchors[anchor]
                except Exception:
                    continue
            name = getattr(anchor, "name", None)
            if name:
                result.append((str(name), anchor))
    except Exception:
        pass
    return result


def _anchor_position(anchor: Any) -> Tuple[float, float]:
    position = getattr(anchor, "position", None)
    if position is None:
        raise ValueError("anchor has no position")
    if isinstance(position, (tuple, list)) and len(position) >= 2:
        x, y = position[0], position[1]
    else:
        x, y = getattr(position, "x", None), getattr(position, "y", None)
    if x is None or y is None:
        raise ValueError("anchor position has no x/y")
    xf, yf = float(x), float(y)
    if not (math.isfinite(xf) and math.isfinite(yf)):
        raise ValueError("non-finite anchor coordinate")
    return xf, yf


def _glyph_unicodes(glyph: Any, report: Report) -> List[Tuple[int, str]]:
    values: List[Any] = []
    unicodes = getattr(glyph, "unicodes", None)
    if unicodes:
        try:
            if isinstance(unicodes, (str, int)):
                values.append(unicodes)
            else:
                values.extend(list(unicodes))
        except Exception:
            pass
    if not values:
        value = getattr(glyph, "unicode", None)
        if value:
            values.append(value)
    result: List[Tuple[int, str]] = []
    seen: Set[str] = set()
    for value in values:
        cp = _normalise_codepoint(value)
        if cp is None:
            continue
        if cp in seen:
            continue
        seen.add(cp)
        result.append((int(cp[2:], 16), cp))
    if len(values) > 1 and not result:
        report.warn(
            "unicode-invalid",
            f"Glyph '{getattr(glyph, 'name', '?')}' has unreadable Unicode values; skipped.",
        )
    return result


def _font_name(font: Any, config: Dict[str, Any], report: Report) -> Optional[str]:
    override = config.get("fontName")
    if override is not None:
        if not isinstance(override, str) or not override.strip():
            report.error("fontName-config", "'fontName' must be a non-empty string.")
            return None
        return override.strip()
    candidates = []
    for attr in ("familyName", "fontName"):
        try:
            value = getattr(font, attr, None)
        except Exception:
            value = None
        if isinstance(value, str) and value.strip():
            candidates.append(value.strip())
    if not candidates:
        report.error(
            "fontName-missing",
            "The font has no family name. Set Font Info > Family Name in Glyphs "
            "or provide \"fontName\" in the configuration.",
        )
        return None
    return candidates[0]


def _font_version(font: Any, config: Dict[str, Any], report: Report) -> Optional[float]:
    override = config.get("fontVersion")
    if override is not None:
        if isinstance(override, bool):
            report.error("fontVersion-config", "'fontVersion' must be a number, not a boolean.")
            return None
        if isinstance(override, (int, float)):
            value = float(override)
        elif isinstance(override, str):
            try:
                value = float(override.strip())
            except ValueError:
                report.error(
                    "fontVersion-config",
                    "'fontVersion' must be a number (for example 1.234) or a numeric string.",
                )
                return None
        else:
            report.error("fontVersion-config", "'fontVersion' must be a number or numeric string.")
            return None
        if not math.isfinite(value) or value < 0:
            report.error("fontVersion-config", "'fontVersion' must be a finite non-negative number.")
            return None
        return value

    try:
        major = int(getattr(font, "versionMajor"))
        minor = int(getattr(font, "versionMinor"))
    except Exception:
        report.error(
            "fontVersion-missing",
            "The font has no readable versionMajor/versionMinor. Set the version "
            "in Font Info or provide \"fontVersion\" in the configuration.",
        )
        return None
    if major < 0 or minor < 0 or minor > 999:
        report.error(
            "fontVersion-range",
            f"Invalid Glyphs version {major}.{minor}. versionMinor must be 0–999 "
            "(it is interpreted as three decimal digits).",
        )
        return None
    # SMuFL uses a three-digit fraction: 1 + 5 -> 1.005, 1 + 482 -> 1.482.
    # Without zero-padding, minor 5 and minor 50 both become 1.5.
    try:
        value = float(f"{major}.{minor:03d}")
    except ValueError:
        report.error("fontVersion-format", f"Invalid Glyphs version {major}.{minor}.")
        return None
    if value == 0:
        report.warn("fontVersion-zero", "The font version is 0.0; confirm that this is intentional.")
    return value


def _custom_parameter(font: Any, names: Sequence[str]) -> Any:
    params = getattr(font, "customParameters", None)
    if params is None:
        return None
    for name in names:
        try:
            value = params[name]
        except Exception:
            continue
        if hasattr(value, "value"):
            value = value.value
        if value is not None and value != "":
            return value
    return None


def _parse_int(value: Any) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isfinite(value) and value.is_integer():
            return int(value)
        return None
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    try:
        return int(value)
    except Exception:
        return None


def _design_size(font: Any, config: Dict[str, Any], source: Dict[str, Any], report: Report) -> Optional[int]:
    if config.get("designSize") is not None:
        value = _parse_int(config["designSize"])
        if value is None or value <= 0:
            report.error("designSize-config", "'designSize' must be a positive integer in decipoints (1/720 inch).")
            return None
        return value
    value = _custom_parameter(font, ("SMuFL Design Size", "designSize"))
    source_value = source.get("designSize") if isinstance(source, dict) else None
    if value is None and source_value is not None:
        value = source_value
        report.info("designSize-source", "Using designSize from metadataSource.")
    if value is None:
        return None
    parsed = _parse_int(value)
    if parsed is None or parsed <= 0:
        report.warn(
            "designSize-invalid",
            f"Ignoring font custom parameter designSize={value!r}; expected a positive integer in decipoints.",
        )
        return None
    report.info("designSize-param", "Using designSize from the font's custom parameters.")
    return parsed


def _size_range(font: Any, config: Dict[str, Any], source_metadata: Dict[str, Any], report: Report) -> Optional[List[int]]:
    value: Any
    origin = ""
    if config.get("sizeRange") is not None:
        value = config["sizeRange"]
        origin = "configuration"
    else:
        value = _custom_parameter(font, ("SMuFL Size Range", "sizeRange"))
        origin = "font custom parameter"
        if value is None and isinstance(source_metadata, dict) and source_metadata.get("sizeRange") is not None:
            value = source_metadata["sizeRange"]
            origin = "metadataSource"
            report.info("sizeRange-source", "Using sizeRange from metadataSource.")
        if value is None:
            return None
    if isinstance(value, str):
        parts = [p for p in re.split(r"[,; ]+", value.strip()) if p]
    elif isinstance(value, (list, tuple)):
        parts = list(value)
    else:
        try:
            parts = list(value)
        except Exception:
            report.error("sizeRange-config", "'sizeRange' must be an array of two integers (decipoints).")
            return None
    numbers = [_parse_int(p) for p in parts]
    if len(numbers) != 2 or any(n is None or n <= 0 for n in numbers):
        report.error("sizeRange-config", "'sizeRange' must contain exactly two positive integers (decipoints).")
        return None
    first, second = int(numbers[0]), int(numbers[1])
    if first > second:
        report.error("sizeRange-order", f"'sizeRange' must be ascending; got {first}, {second}.")
        return None
    if origin == "font custom parameter":
        report.info("sizeRange-param", "Using sizeRange from the font's custom parameters.")
    return [first, second]


# ---------------------------------------------------------------------------
# Glyph identification
# ---------------------------------------------------------------------------

@dataclass
class Resolution:
    name: str
    kind: str                  # canonical | alias | unicode | optional
    codepoint: Optional[str] = None


class GlyphNameResolver:
    def __init__(self, data: GlyphNameData, config: Dict[str, Any], report: Report):
        self.data = data
        self.report = report
        self.aliases: Dict[str, str] = dict(BUILTIN_GLYPH_ALIASES)
        extra = config.get("glyphNameAliases") or {}
        if not isinstance(extra, dict):
            report.error("aliases-shape", "'glyphNameAliases' must be an object mapping Glyphs names to SMuFL names.")
            extra = {}
        for source, target in extra.items():
            if not isinstance(source, str) or not isinstance(target, str):
                report.error("aliases-shape", "Each 'glyphNameAliases' entry must map a string to a string.")
                continue
            if target not in data.canonical_names:
                report.error(
                    "aliases-target",
                    f"Glyph alias target '{target}' is not a canonical SMuFL name.",
                )
                continue
            self.aliases[source] = target
        self._cache: Dict[Tuple[str, Tuple[str, ...]], Optional[Resolution]] = {}

    def resolve(self, glyph: Any, quiet: bool = False) -> Optional[Resolution]:
        raw_name = str(getattr(glyph, "name", "") or "")
        unicodes = _glyph_unicodes(glyph, self.report)
        cache_key = (raw_name, tuple(cp for _, cp in unicodes), quiet)
        if cache_key in self._cache:
            return self._cache[cache_key]
        if quiet:
            old_report = self.report
            self.report = Report()
            try:
                resolution = self._resolve(raw_name, unicodes, glyph)
            finally:
                self.report = old_report
        else:
            resolution = self._resolve(raw_name, unicodes, glyph)
        self._cache[cache_key] = resolution
        return resolution

    def _check_codepoint(self, canonical_name: str, unicodes: List[Tuple[int, str]]) -> None:
        """Warn when a canonical glyph name disagrees with its Unicode value."""
        if not unicodes:
            return
        entry = self.data.glyphs.get(canonical_name, {})
        expected = {entry.get("codepoint"), entry.get("alternateCodepoint")}
        expected.discard(None)
        if expected and not any(cp in expected for _, cp in unicodes):
            self.report.warn(
                "glyph-codepoint-mismatch",
                f"Glyph '{canonical_name}' has Unicode "
                f"{', '.join(cp for _, cp in unicodes)}, but the canonical SMuFL "
                f"name expects {', '.join(sorted(expected))}. The canonical name "
                "is used; check the font's Unicode assignment.",
            )

    def _resolve(self, raw_name: str, unicodes: List[Tuple[int, str]], glyph: Any) -> Optional[Resolution]:
        if raw_name in self.data.canonical_names:
            self._check_codepoint(raw_name, unicodes)
            return Resolution(raw_name, "canonical")
        if raw_name in self.aliases:
            target = self.aliases[raw_name]
            self._check_codepoint(target, unicodes)
            self.report.warn(
                "glyph-alias",
                f"Glyph '{raw_name}' is mapped to canonical SMuFL name '{target}' "
                "(known Glyphs-name workaround).",
            )
            return Resolution(target, "alias")

        optional_unicodes = [u for u in unicodes if OPTIONAL_GLYPH_MIN <= u[0] <= OPTIONAL_GLYPH_MAX]
        if GENERIC_GLYPH_NAME_RE.match(raw_name) or not raw_name:
            core = [u for u in unicodes if not (OPTIONAL_GLYPH_MIN <= u[0] <= OPTIONAL_GLYPH_MAX)]
            if len(core) == 1:
                cp = core[0][1]
                names = self.data.codepoint_to_names.get(cp, ())
                if len(names) == 1:
                    self.report.warn(
                        "glyph-unicode",
                        f"Glyph '{raw_name or '(unnamed)'}' was mapped to '{names[0]}' "
                        f"by Unicode {cp}; rename the glyph to the canonical name to "
                        "make the mapping explicit.",
                    )
                    return Resolution(names[0], "unicode", cp)
                if len(names) > 1:
                    self.report.error(
                        "glyph-unicode-ambiguous",
                        f"Glyph '{raw_name}' has Unicode {cp}, which maps to several "
                        f"SMuFL names ({', '.join(names)}); not exported. Rename the glyph.",
                    )
                    return None
            if len(optional_unicodes) == 1:
                if not OPTIONAL_GLYPH_NAME_RE.match(raw_name):
                    self.report.warn(
                        "optional-name-invalid",
                        f"Optional glyph '{raw_name}' has a name that is not safe as a "
                        "SMuFL glyph key; skipped. Rename it to letters/digits/underscore/plus.",
                    )
                    return None
                return Resolution(raw_name, "optional", optional_unicodes[0][1])
            if len(unicodes) > 1:
                self.report.warn(
                    "glyph-unicode-multiple",
                    f"Glyph '{raw_name}' has multiple Unicode values; no unique SMuFL "
                    "mapping could be made.",
                )
            elif not unicodes:
                self.report.warn(
                    "glyph-no-unicode",
                    f"Glyph '{raw_name}' has no Unicode value and no canonical SMuFL "
                    "name; its metadata is not exported.",
                )
            return None

        if len(optional_unicodes) == 1:
            if not OPTIONAL_GLYPH_NAME_RE.match(raw_name):
                self.report.warn(
                    "optional-name-invalid",
                    f"Optional glyph '{raw_name}' has a name that is not safe as a "
                    "SMuFL glyph key; skipped. Rename it to letters/digits/underscore/plus.",
                )
                return None
            return Resolution(raw_name, "optional", optional_unicodes[0][1])

        # A non-generic, non-canonical core glyph: deliberately do not guess
        # from Unicode, because that could silently export an alternate as
        # the canonical character.
        if unicodes:
            cps = ", ".join(cp for _, cp in unicodes)
            self.report.warn(
                "glyph-unmapped",
                f"Glyph '{raw_name}' ({cps}) is not a canonical SMuFL name and has "
                "no configured alias; its metadata is not exported.",
            )
        else:
            self.report.warn(
                "glyph-no-unicode",
                f"Glyph '{raw_name}' has no Unicode value and no canonical SMuFL "
                "name; its metadata is not exported.",
            )
        return None


# ---------------------------------------------------------------------------
# OpenType feature parsing: alternates, ligatures and stylistic sets
# ---------------------------------------------------------------------------

@dataclass
class FeatureData:
    alternates: Dict[str, List[Tuple[str, str]]] = field(default_factory=dict)
    set_members: Dict[str, List[Tuple[str, str, str]]] = field(default_factory=dict)
    ligatures: Dict[str, Tuple[List[str], str]] = field(default_factory=dict)
    alternate_base: Dict[str, str] = field(default_factory=dict)

    def has_alternates(self) -> bool:
        return any(self.alternates.values())

    def has_ligatures(self) -> bool:
        return bool(self.ligatures)

    def has_sets(self) -> bool:
        return any(self.set_members.values())


def _feature_substitutions(code: str) -> List[Tuple[str, List[str], List[str]]]:
    """Return (kind, left, right) for simple sub statements in FDK code."""
    text = re.sub(r"#[^\n]*", "", code or "")
    results: List[Tuple[str, List[str], List[str]]] = []
    for match in re.finditer(r"\bsub\s+([^;]+?)\s*;", text, re.S):
        body = " ".join(match.group(1).split())
        if "'" in body:
            continue
        if " from " in body:
            left, right = body.split(" from ", 1)
            right = right.strip()
            if not (right.startswith("[") and right.endswith("]")):
                continue
            results.append(("from", left.split(), right[1:-1].split()))
        elif " by " in body:
            left, right = body.split(" by ", 1)
            results.append(("by", left.split(), right.split()))
    return results


def _parse_class_definitions(font: Any) -> Dict[str, List[str]]:
    classes: Dict[str, List[str]] = {}
    for cls in getattr(font, "classes", []):
        code = str(getattr(cls, "code", "") or "")
        for match in re.finditer(r"@?([A-Za-z0-9_.]+)\s*=\s*\[([^\]]*)\];", code):
            name = match.group(1)
            classes[name] = [t for t in match.group(2).split() if t]
    return classes


def _expand_tokens(tokens: List[str], classes: Dict[str, List[str]]) -> List[str]:
    result: List[str] = []
    for token in tokens:
        if token.startswith("@"):
            name = token[1:]
            result.extend(classes.get(name, []))
        elif token in classes:
            result.extend(classes[token])
        else:
            result.append(token)
    return result


def _extract_features(
    font: Any,
    resolver: "GlyphNameResolver",
    glyphnames: GlyphNameData,
    report: Report,
) -> FeatureData:
    """Parse Glyphs OpenType features into SMuFL alternates/ligatures/sets.

    Only simple substitutions are interpreted.  Contextual substitutions,
    class-based lookups that cannot be expanded, and automatic features with
    no generated code are skipped with a report entry.
    """
    data = FeatureData()
    raw_glyphs: Dict[str, Any] = {}
    for glyph in getattr(font, "glyphs", []):
        if not getattr(glyph, "export", True):
            continue
        name = str(getattr(glyph, "name", "") or "")
        if name:
            raw_glyphs[name] = glyph
    classes = _parse_class_definitions(font)
    cache: Dict[str, Optional[Tuple[Any, Optional[str], Any]]] = {}
    missing: Counter = Counter()
    ligature_conflicts: List[str] = []

    def resolve_ref(raw: str) -> Optional[Tuple[Any, Optional[str], Any]]:
        if raw in cache:
            return cache[raw]
        glyph = raw_glyphs.get(raw)
        if glyph is None:
            cache[raw] = None
            missing[raw] += 1
            return None
        resolution = resolver.resolve(glyph, quiet=True)
        if resolution is None:
            cache[raw] = None
            return None
        cp = resolution.codepoint
        if not cp:
            unicodes = _glyph_unicodes(glyph, Report())
            cp = unicodes[0][1] if unicodes else None
        result = (resolution, cp, glyph)
        cache[raw] = result
        return result

    def add_alternate(base_raw: str, alt_raw: str, tag: str) -> None:
        base = resolve_ref(base_raw)
        alt = resolve_ref(alt_raw)
        if base is None or alt is None:
            return
        base_res, _, _ = base
        alt_res, alt_cp, _ = alt
        if base_res.kind == "optional":
            report.warn(
                "alternate-base-optional",
                f"Alternate '{alt_res.name}' has optional base '{base_res.name}'; skipped.",
            )
            return
        if alt_res.name == base_res.name or not alt_cp:
            return
        existing = data.alternates.setdefault(base_res.name, [])
        if not any(name == alt_res.name for name, _ in existing):
            existing.append((alt_res.name, alt_cp))
        data.alternate_base[alt_res.name] = base_res.name
        if SET_FEATURE_RE.match(tag):
            members = data.set_members.setdefault(tag, [])
            if not any(name == alt_res.name for _, name, _ in members):
                members.append((base_res.name, alt_res.name, alt_cp))

    def add_ligature(output_raw: str, component_raws: List[str]) -> None:
        output = resolve_ref(output_raw)
        if output is None:
            return
        output_res, output_cp, _ = output
        if not output_cp:
            report.warn(
                "ligature-no-codepoint",
                f"Ligature '{output_res.name}' has no Unicode; skipped.",
            )
            return
        components: List[str] = []
        for raw in component_raws:
            comp = resolve_ref(raw)
            if comp is None:
                return
            components.append(comp[0].name)
        previous = data.ligatures.get(output_res.name)
        if previous is not None:
            if previous[0] != components:
                ligature_conflicts.append(output_res.name)
            return
        data.ligatures[output_res.name] = (components, output_cp)

    for feature in getattr(font, "features", []):
        tag = str(getattr(feature, "name", "") or "").strip()
        if not tag or not bool(getattr(feature, "active", True)):
            continue
        code = str(getattr(feature, "code", "") or "")
        if not code:
            if bool(getattr(feature, "automatic", False)):
                report.warn(
                    "feature-no-code",
                    f"Automatic feature '{tag}' has no generated code; alternates/"
                    "ligatures from it cannot be derived. Run Glyphs' feature update "
                    "or use glyph-name suffixes.",
                )
            continue
        statements = _feature_substitutions(code)
        if not statements:
            continue
        if tag in LIGATURE_FEATURE_TAGS:
            for kind, left, right in statements:
                if kind != "by" or len(left) < 2 or len(right) != 1:
                    continue
                add_ligature(right[0], _expand_tokens(left, classes))
        elif tag == "salt" or ALTERNATE_FEATURE_RE.match(tag):
            for kind, left, right in statements:
                if kind == "from":
                    bases = _expand_tokens(left, classes)
                    alts = _expand_tokens(right, classes)
                    for base in bases:
                        for alt in alts:
                            add_alternate(base, alt, tag)
                elif kind == "by" and len(right) == 1:
                    for base in _expand_tokens(left, classes):
                        add_alternate(base, right[0], tag)

    # Fallback for fonts whose OpenType features are missing/empty but whose
    # glyph names follow the Adobe/SMuFL suffix convention.
    for raw_name, glyph in raw_glyphs.items():
        match = ALTERNATE_SUFFIX_RE.match(raw_name)
        if match:
            add_alternate(match.group("base"), raw_name, match.group("tag") + match.group("num"))
        if "_" in raw_name:
            parts = raw_name.split("_")
            if len(parts) > 1 and all(part in raw_glyphs for part in parts):
                add_ligature(raw_name, parts)

    if ligature_conflicts:
        names = ", ".join(sorted(set(ligature_conflicts)))
        report.warn(
            "ligature-conflict",
            f"{len(set(ligature_conflicts))} ligature(s) have multiple component "
            f"definitions; keeping the first: {names}.",
        )
    if missing:
        names = ", ".join(f"{name} ({count})" for name, count in sorted(missing.items())[:12])
        report.info("feature-missing-refs", f"Feature references not found in the font: {names}.")
    if data.has_alternates():
        report.info("alternates", f"Derived {sum(len(v) for v in data.alternates.values())} alternates for {len(data.alternates)} base glyphs.")
    if data.has_ligatures():
        report.info("ligatures", f"Derived {len(data.ligatures)} ligatures.")
    if data.has_sets():
        report.info("sets", f"Derived {len(data.set_members)} stylistic sets.")
    return data


# ---------------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------------

def _staff_space(font: Any, report: Report) -> Optional[float]:
    try:
        upm = float(getattr(font, "upm"))
    except Exception:
        report.error("upm-missing", "The font has no readable units-per-em (UPM).")
        return None
    if not math.isfinite(upm) or upm <= 0:
        report.error("upm-invalid", f"Invalid UPM: {upm!r}.")
        return None
    staff = upm / 4.0
    if int(upm) % 4 != 0:
        report.warn(
            "upm-quarter",
            f"UPM {int(upm)} is not divisible by 4; one staff space is "
            f"{staff:g} font units. SMuFL normally uses UPM/4, so this is "
            "allowed but unusual.",
        )
    return staff


def _round(value: float) -> float:
    result = round(value, 6)
    return 0.0 if result == 0 else result


ENGRAVING_TOLERANCE = 6.0


def _layer_points(layer: Any) -> List[Tuple[int, float, float, str]]:
    points: List[Tuple[int, float, float, str]] = []
    for path_index, path in enumerate(getattr(layer, "paths", [])):
        for node in getattr(path, "nodes", []):
            try:
                points.append((
                    path_index,
                    float(node.x),
                    float(node.y),
                    str(getattr(node, "type", "") or ""),
                ))
            except Exception:
                continue
    return points


def _measure_engraving_ruler(layer: Any, ruler: str) -> Optional[float]:
    """Port of the relevant SMufoLib ruler functions to Glyphs paths."""
    try:
        measured_layer = layer.copyDecomposedLayer()
    except Exception:
        measured_layer = layer

    bounds = measured_layer.bounds
    if ruler == "glyphBoundsHeight":
        return float(bounds.size.height)
    if ruler == "glyphBoundsWidth":
        return float(bounds.size.width)
    if ruler == "glyphBoundsXMinAbs":
        return abs(float(bounds.origin.x))

    points = _layer_points(measured_layer)
    if not points:
        return None

    if ruler == "xStrokeWidthAtOrigin":
        ordered = sorted(points, key=lambda p: abs(p[1]) + abs(p[2]))
        ref = ordered[0]
        for point in ordered[1:]:
            if point[0] != ref[0] or point[1] == ref[1]:
                continue
            if abs(point[2] - ref[2]) <= ENGRAVING_TOLERANCE:
                return abs(point[1] - ref[1])

    elif ruler == "yStrokeWidthAtMinimum":
        ordered = sorted(points, key=lambda p: p[2])
        ref = ordered[0]
        for point in ordered[1:]:
            if point[0] != ref[0] or point[2] == ref[2]:
                continue
            if abs(point[1] - ref[1]) <= ENGRAVING_TOLERANCE:
                return abs(point[2] - ref[2])

    elif ruler == "xDistanceBetweenContours":
        ordered = sorted(points, key=lambda p: p[1])
        path_index = ordered[0][0]
        ref_x = max(p[1] for p in points if p[0] == path_index)
        for point in ordered:
            if point[0] != path_index:
                return abs(point[1] - ref_x)

    elif ruler == "yDistanceBetweenContours":
        ordered = sorted(points, key=lambda p: p[2])
        path_index = ordered[0][0]
        ref_y = max(p[2] for p in points if p[0] == path_index)
        for point in ordered:
            if point[0] != path_index:
                return abs(point[2] - ref_y)

    elif ruler == "xDistanceStemToDot":
        dot_points: List[Tuple[int, float, float, str]] = []
        stem_points: List[Tuple[int, float, float, str]] = []
        for path_index, path in enumerate(getattr(measured_layer, "paths", [])):
            nodes = list(getattr(path, "nodes", []))
            types = [str(getattr(node, "type", "") or "") for node in nodes]
            path_points = []
            for node in nodes:
                try:
                    path_points.append((path_index, float(node.x), float(node.y), str(getattr(node, "type", "") or "")))
                except Exception:
                    pass
            if types and all(t != "line" for t in types):
                dot_points.extend(path_points)
            stem_points.extend([p for p in path_points if p[3] == "line"])
        if not dot_points or not stem_points:
            return None
        ref = min(dot_points, key=lambda p: p[1])
        closest = max(stem_points, key=lambda p: p[1])
        if ref[1] < closest[1]:
            ref = max(dot_points, key=lambda p: p[1])
            closest = min(stem_points, key=lambda p: p[1])
        return abs(closest[1] - ref[1])

    elif ruler == "wedgeArmStrokeWidth":
        line_points = [p for p in points if p[3] == "line"]
        if not line_points:
            return None
        ref = max(line_points, key=lambda p: p[1])
        candidates = [p for p in line_points if p is not ref]
        if not candidates:
            return None
        nearest = min(
            candidates,
            key=lambda p: math.hypot(p[1] - ref[1], p[2] - ref[2]),
        )
        return math.hypot(nearest[1] - ref[1], nearest[2] - ref[2])

    return None


def _compute_engraving_defaults(font: Any, master: Any, report: Report) -> Dict[str, Any]:
    staff = _staff_space(font, report)
    if staff is None:
        return {}
    by_codepoint: Dict[int, Any] = {}
    for glyph in getattr(font, "glyphs", []):
        if not getattr(glyph, "export", True):
            continue
        for cp, _ in _glyph_unicodes(glyph, report):
            by_codepoint.setdefault(cp, glyph)

    result: Dict[str, Any] = {}
    missing: List[str] = []
    unmeasurable: List[str] = []
    for key, (codepoint, ruler) in ENGRAVING_DEFAULT_MAPPING.items():
        glyph = by_codepoint.get(int(codepoint, 16))
        if glyph is None:
            missing.append(f"{key} (U+{codepoint})")
            continue
        layer = _layer_for_master(glyph, master)
        if layer is None:
            missing.append(f"{key} (U+{codepoint})")
            continue
        try:
            value = _measure_engraving_ruler(layer, ruler)
        except Exception as exc:
            report.warn("engraving-measure", f"Could not measure {key} from U+{codepoint}: {exc}.")
            continue
        if value is None or not math.isfinite(value) or value <= 0:
            unmeasurable.append(f"{key} (U+{codepoint})")
            continue
        result[key] = _round(float(value) / staff)
        report.incr("engraving_defaults")
    if missing:
        report.info(
            "engraving-target-missing",
            "engravingDefaults targets not found: " + ", ".join(missing) + ".",
        )
    if unmeasurable:
        report.warn(
            "engraving-unmeasurable",
            "Could not measure engravingDefaults: " + ", ".join(unmeasurable) + ".",
        )
    if result:
        report.info("engraving-calculated", f"Calculated {len(result)} engravingDefaults from glyph geometry.")
    else:
        report.warn(
            "engraving-none",
            "No engravingDefaults could be measured from this master. Supply them in config/metadataSource if needed.",
        )
    return result


def _optional_glyphs(
    font: Any,
    master: Any,
    glyphnames: GlyphNameData,
    include: bool,
    report: Report,
    optional_ref: Optional[Dict[str, Dict[str, Any]]] = None,
    source: Optional[Dict[str, Any]] = None,
    alternate_base: Optional[Dict[str, str]] = None,
) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    """Return (optionalGlyphs section, name -> codepoint map)."""
    if not include:
        return {}, {}
    result: Dict[str, Dict[str, Any]] = {}
    name_to_cp: Dict[str, str] = {}
    cp_to_name: Dict[str, str] = {}
    generic_names: List[str] = []
    optional_ref = optional_ref or {}
    alternate_base = alternate_base or {}
    source_optional = {}
    if isinstance(source, dict) and isinstance(source.get("optionalGlyphs"), dict):
        source_optional = source["optionalGlyphs"]
    for glyph in getattr(font, "glyphs", []):
        if not getattr(glyph, "export", True):
            continue
        layer = _layer_for_master(glyph, master)
        if layer is None:
            continue
        unicodes = _glyph_unicodes(glyph, report)
        optional = [u for u in unicodes if OPTIONAL_GLYPH_MIN <= u[0] <= OPTIONAL_GLYPH_MAX]
        if not optional:
            continue
        if len(optional) > 1:
            report.warn(
                "optional-multiple-unicodes",
                f"Optional glyph '{getattr(glyph, 'name', '?')}' has multiple "
                "optional-range Unicode values; skipped.",
            )
            continue
        name = str(getattr(glyph, "name", "") or "")
        cp = optional[0][1]
        if not OPTIONAL_GLYPH_NAME_RE.match(name):
            report.warn(
                "optional-name-invalid",
                f"Optional glyph '{name}' ({cp}) has a name that is not safe as a "
                "SMuFL glyph key; skipped.",
            )
            continue
        if name in glyphnames.canonical_names:
            report.error(
                "optional-canonical-collision",
                f"Optional glyph '{name}' ({cp}) collides with a canonical SMuFL "
                "name; this is not valid for optionalGlyphs.",
            )
            continue
        if name in result:
            report.error(
                "optional-duplicate-name",
                f"Two optional glyphs share the name '{name}'; names must be unique.",
            )
            continue
        if cp in cp_to_name:
            report.error(
                "optional-duplicate-codepoint",
                f"Optional glyphs '{cp_to_name[cp]}' and '{name}' share codepoint {cp}.",
            )
            continue
        # Classes: reference data for the same name/codepoint, then the
        # classes of the base glyph if this optional glyph is an alternate.
        classes: List[str] = []
        ref = optional_ref.get(name)
        if isinstance(ref, dict) and ref.get("codepoint") == cp and isinstance(ref.get("classes"), list):
            classes = [str(c) for c in ref["classes"] if isinstance(c, str) and c]
        elif isinstance(source_optional.get(name), dict) and source_optional[name].get("codepoint") == cp:
            src_classes = source_optional[name].get("classes")
            if isinstance(src_classes, list):
                classes = [str(c) for c in src_classes if isinstance(c, str) and c]
        if not classes:
            base_name = alternate_base.get(name)
            if base_name:
                classes = glyphnames.classes_of(base_name)

        description: Optional[str] = None
        note = str(getattr(glyph, "note", "") or "").strip()
        if note and note != name:
            description = note
        if not description:
            description = glyphnames.description_of(name)
        if not description and isinstance(ref, dict) and ref.get("codepoint") == cp:
            value = ref.get("description")
            if isinstance(value, str) and value.strip():
                description = value.strip()
        if not description and isinstance(source_optional.get(name), dict) and source_optional[name].get("codepoint") == cp:
            value = source_optional[name].get("description")
            if isinstance(value, str) and value.strip():
                description = value.strip()

        entry: Dict[str, Any] = {"codepoint": cp, "classes": classes}
        if description:
            entry["description"] = description
        result[name] = entry
        name_to_cp[name] = cp
        cp_to_name[cp] = name
        lowered = name.lower()
        if lowered.startswith("uni") and re.fullmatch(r"uni[0-9a-f]{4,6}", lowered):
            generic_names.append(name)
    if generic_names:
        shown = ", ".join(generic_names[:20])
        if len(generic_names) > 20:
            shown += f", … ({len(generic_names) - 20} more)"
        report.warn(
            "optional-generic-names",
            f"{len(generic_names)} optional glyph(s) use generic Unicode-derived "
            f"names: {shown}. They are exported under those font-specific names; "
            "consider giving them descriptive SMuFL-style names.",
        )
    if result:
        report.info("optional-glyphs", f"Exported {len(result)} optional-glyph entries.")
    return result, name_to_cp


def _bool_config(config: Dict[str, Any], key: str, default: bool, report: Report) -> bool:
    if key not in config or config[key] is None:
        return default
    value = config[key]
    if not isinstance(value, bool):
        report.error("config-boolean", f"'{key}' must be true or false.")
        return default
    return value


def _normalise_anchor_value(name: str, value: Any, report: Report) -> Any:
    """Validate/normalise a manually configured anchor value."""
    if name in SCALAR_ANCHORS:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            report.error("anchor-config", f"Anchor '{name}' must be a number.")
            return None
        number = float(value)
        if not math.isfinite(number) or number <= 0:
            report.error("anchor-config", f"Anchor '{name}' must be a positive finite number.")
            return None
        return _round(number)
    if isinstance(value, (list, tuple)) and len(value) == 2:
        x, y = value
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in (x, y)):
            report.error("anchor-config", f"Anchor '{name}' must be [x, y] numbers.")
            return None
        xf, yf = float(x), float(y)
        if not (math.isfinite(xf) and math.isfinite(yf)):
            report.error("anchor-config", f"Anchor '{name}' has a non-finite coordinate.")
            return None
        return [_round(xf), _round(yf)]
    if name in HYBRID_ANCHORS and isinstance(value, (int, float)) and not isinstance(value, bool):
        number = float(value)
        if math.isfinite(number):
            report.warn(
                "anchor-scalar-override",
                f"Anchor '{name}' is configured as a scalar; Bravura and the "
                "official generator normally use [x, y] for this anchor.",
            )
            return _round(number)
    report.error("anchor-config", f"Anchor '{name}' must be [x, y] numbers.")
    return None


def _description_for_glyph(
    name: str,
    codepoint: Optional[str],
    optional_entries: Dict[str, Dict[str, Any]],
    glyphnames: GlyphNameData,
    optional_ref: Dict[str, Dict[str, Any]],
    source: Dict[str, Any],
) -> Optional[str]:
    entry = optional_entries.get(name)
    if isinstance(entry, dict) and isinstance(entry.get("description"), str) and entry["description"].strip():
        return entry["description"].strip()
    value = glyphnames.description_of(name)
    if value:
        return value
    ref = optional_ref.get(name)
    if isinstance(ref, dict) and ref.get("codepoint") == codepoint:
        value = ref.get("description")
        if isinstance(value, str) and value.strip():
            return value.strip()
    source_optional = source.get("optionalGlyphs") if isinstance(source, dict) else None
    if isinstance(source_optional, dict):
        src = source_optional.get(name)
        if isinstance(src, dict) and src.get("codepoint") == codepoint:
            value = src.get("description")
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


def _extract_glyph_data(
    font: Any,
    master: Any,
    glyphnames: GlyphNameData,
    config: Dict[str, Any],
    report: Report,
    optional_ref: Optional[Dict[str, Dict[str, Any]]] = None,
    source: Optional[Dict[str, Any]] = None,
    sets_template: Optional[Dict[str, Dict[str, str]]] = None,
) -> Tuple[
    Dict[str, Dict[str, Any]],
    Dict[str, Any],
    Dict[str, float],
    Dict[str, Dict[str, Any]],
    Dict[str, str],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
]:
    """Extract anchors, metrics, optional glyphs, alternates, ligatures and sets.

    Returns:
        anchors, bboxes, widths, optionalGlyphs, optional_name_to_cp,
        glyphsWithAlternates, ligatures, sets
    """
    optional_ref = optional_ref or {}
    source = source or {}
    sets_template = sets_template or {}
    staff = _staff_space(font, report)
    if staff is None:
        return {}, {}, {}, {}, {}, {}, {}, {}

    include_optional = _bool_config(config, "includeOptionalGlyphs", True, report)
    include_bboxes = _bool_config(config, "includeGlyphBBoxes", True, report)
    include_widths = _bool_config(config, "includeGlyphAdvanceWidths", True, report)
    include_alternates = _bool_config(config, "includeGlyphsWithAlternates", True, report)
    include_ligatures = _bool_config(config, "includeLigatures", True, report)
    include_sets = _bool_config(config, "includeSets", True, report)

    resolver = GlyphNameResolver(glyphnames, config, report)
    feature_data = _extract_features(font, resolver, glyphnames, report)
    optional, optional_name_to_cp = _optional_glyphs(
        font, master, glyphnames, include_optional, report,
        optional_ref=optional_ref, source=source,
        alternate_base=feature_data.alternate_base,
    )

    anchors: Dict[str, Dict[str, Any]] = {}
    bboxes: Dict[str, Any] = {}
    widths: Dict[str, float] = {}
    ignored_anchor_names: Counter = Counter()
    lower_anchor_names = {a.lower(): a for a in SUPPORTED_ANCHORS}

    for glyph in getattr(font, "glyphs", []):
        report.incr("glyphs_scanned")
        if not getattr(glyph, "export", True):
            report.incr("glyphs_not_exported")
            continue
        layer = _layer_for_master(glyph, master)
        if layer is None:
            report.incr("glyphs_without_master_layer")
            report.warn(
                "layer-missing",
                f"Glyph '{getattr(glyph, 'name', '?')}' has no layer for master "
                f"'{getattr(master, 'name', '?')}'; skipped.",
            )
            continue

        glyph_anchors: Dict[str, Any] = {}
        for anchor_name, anchor in _anchor_items(layer):
            name = str(anchor_name or getattr(anchor, "name", "") or "").strip()
            if not name:
                continue
            if name in POINT_ANCHORS:
                try:
                    x, y = _anchor_position(anchor)
                except Exception as exc:
                    report.error(
                        "anchor-position",
                        f"Glyph '{getattr(glyph, 'name', '?')}', anchor '{name}': {exc}.",
                    )
                    continue
                if name in glyph_anchors:
                    report.error(
                        "anchor-duplicate",
                        f"Glyph '{getattr(glyph, 'name', '?')}' has more than one "
                        f"anchor named '{name}'.",
                    )
                    continue
                glyph_anchors[name] = [_round(x / staff), _round(y / staff)]
            elif name in SCALAR_ANCHORS:
                report.warn(
                    "anchor-scalar",
                    f"Glyph '{getattr(glyph, 'name', '?')}' has a point anchor "
                    f"named '{name}', but SMuFL defines it as a scalar. It is not "
                    "exported; configure it manually if needed.",
                )
            else:
                ignored_anchor_names[name] += 1
                if name.lower() in lower_anchor_names and name not in SUPPORTED_ANCHORS:
                    report.warn(
                        "anchor-case",
                        f"Anchor '{name}' on glyph '{getattr(glyph, 'name', '?')}' "
                        f"differs only by case from SMuFL anchor '{lower_anchor_names[name.lower()]}'; "
                        "SMuFL anchor names are case-sensitive, so it was ignored.",
                    )

        needs_identity = bool(glyph_anchors) or include_bboxes or include_widths
        if not needs_identity:
            continue
        resolution = resolver.resolve(glyph, quiet=not bool(glyph_anchors))
        if resolution is None:
            continue
        if resolution.kind == "optional" and not include_optional:
            report.warn(
                "optional-anchor-skipped",
                f"Glyph '{resolution.name}' has SMuFL metadata but optionalGlyphs "
                "export is disabled; its metadata was skipped.",
            )
            continue
        if resolution.kind == "optional" and resolution.name not in optional_name_to_cp:
            report.warn(
                "optional-undeclared",
                f"Optional glyph '{resolution.name}' has metadata but is not in the "
                "optionalGlyphs section (invalid name/codepoint/duplicate?); its "
                "metadata was skipped.",
            )
            continue

        output_name = resolution.name
        if glyph_anchors:
            if output_name in anchors:
                report.error(
                    "glyph-duplicate",
                    f"Multiple Glyphs glyphs map to SMuFL name '{output_name}'; "
                    "the resulting JSON key would be duplicated. Rename or remove "
                    "the duplicate.",
                )
            else:
                anchors[output_name] = glyph_anchors
                report.incr("glyphs_with_anchors")
                if resolution.kind == "optional":
                    report.incr("optional_glyphs_with_anchors")

        unicodes = _glyph_unicodes(glyph, report)
        is_member = resolution.kind in ("canonical", "alias", "optional") or any(
            0xE000 <= cp <= 0xF8FF for cp, _ in unicodes
        )
        if include_bboxes and is_member:
            try:
                bounds = layer.bounds
                bx = float(bounds.origin.x)
                by = float(bounds.origin.y)
                bw = float(bounds.size.width)
                bh = float(bounds.size.height)
                if all(math.isfinite(v) for v in (bx, by, bw, bh)):
                    if output_name in bboxes:
                        report.error("bbox-duplicate", f"Duplicate glyphBBoxes key '{output_name}'.")
                    else:
                        bboxes[output_name] = {
                            "bBoxSW": [_round(bx / staff), _round(by / staff)],
                            "bBoxNE": [_round((bx + bw) / staff), _round((by + bh) / staff)],
                        }
                        report.incr("glyph_bboxes")
            except Exception as exc:
                report.warn("bbox-failed", f"Could not read bounds for '{output_name}': {exc}.")

        if include_widths and is_member:
            try:
                width = float(layer.width)
                if math.isfinite(width):
                    if output_name in widths:
                        report.error("width-duplicate", f"Duplicate glyphAdvanceWidths key '{output_name}'.")
                    else:
                        widths[output_name] = _round(width / staff)
                        report.incr("glyph_widths")
            except Exception as exc:
                report.warn("width-failed", f"Could not read advance width for '{output_name}': {exc}.")

    # Manual overrides/additions in staff spaces, merged after extraction.
    manual = config.get("glyphsWithAnchors") or {}
    if manual:
        if not isinstance(manual, dict):
            report.error("manual-anchors-shape", "'glyphsWithAnchors' in the configuration must be an object.")
        else:
            present = set(anchors)
            resolver = GlyphNameResolver(glyphnames, config, Report())
            font_output_names = set()
            for glyph in getattr(font, "glyphs", []):
                if not getattr(glyph, "export", True):
                    continue
                resolution = resolver.resolve(glyph, quiet=True)
                if resolution is not None:
                    font_output_names.add(resolution.name)
            for glyph_name, manual_anchors in manual.items():
                if not isinstance(glyph_name, str) or not glyph_name:
                    report.error("manual-anchors-name", "Manual glyph keys must be non-empty strings.")
                    continue
                allowed = glyph_name in glyphnames.canonical_names or glyph_name in optional_name_to_cp
                if not allowed:
                    report.error(
                        "manual-anchors-name",
                        f"Manual glyph '{glyph_name}' is neither a canonical SMuFL name "
                        "nor a declared optional glyph; not merged.",
                    )
                    continue
                if glyph_name not in present and glyph_name not in font_output_names:
                    report.error(
                        "manual-anchors-missing",
                        f"Manual anchors were configured for '{glyph_name}', but no "
                        "glyph with that SMuFL identity exists in the font.",
                    )
                    continue
                if not isinstance(manual_anchors, dict):
                    report.error("manual-anchors-shape", f"Manual anchors for '{glyph_name}' must be an object.")
                    continue
                for anchor_name, value in manual_anchors.items():
                    if anchor_name not in SUPPORTED_ANCHORS:
                        report.error(
                            "manual-anchor-unsupported",
                            f"Manual anchor '{anchor_name}' on '{glyph_name}' is not a "
                            "documented SMuFL anchor name.",
                        )
                        continue
                    normalised = _normalise_anchor_value(anchor_name, value, report)
                    if normalised is None:
                        continue
                    anchors.setdefault(glyph_name, {})[anchor_name] = normalised
                    report.info(
                        "manual-anchor",
                        f"Manual anchor '{anchor_name}' on '{glyph_name}' overrides/adds the extracted value.",
                    )

    if ignored_anchor_names:
        names = ", ".join(f"{name} ({count})" for name, count in sorted(ignored_anchor_names.items()))
        report.info("ignored-anchors", f"Ignored non-SMuFL anchors: {names}.")
    if anchors:
        report.info("anchors-extracted", f"Extracted anchors for {len(anchors)} glyphs.")
    else:
        report.warn("anchors-none", "No supported SMuFL anchors were found in the selected master.")

    # --- glyphsWithAlternates ---
    alternates_section: Dict[str, Any] = {}
    if include_alternates:
        for base, alts in feature_data.alternates.items():
            if base not in glyphnames.canonical_names:
                continue
            entries = []
            for alt_name, alt_cp in sorted(alts, key=lambda item: item[1]):
                if alt_name not in optional_name_to_cp and alt_name not in glyphnames.canonical_names:
                    continue
                entries.append({"codepoint": alt_cp, "name": alt_name})
            if entries:
                alternates_section[base] = {"alternates": entries}
        if not alternates_section and isinstance(source.get("glyphsWithAlternates"), dict):
            alternates_section = source["glyphsWithAlternates"]
            if alternates_section:
                report.warn("source-fallback", "Using glyphsWithAlternates from metadataSource (feature parsing produced none).")
        if alternates_section:
            report.incr("alternate_bases", len(alternates_section))
            report.info("alternates-section", f"Building glyphsWithAlternates for {len(alternates_section)} base glyphs.")

    # --- ligatures ---
    ligatures_section: Dict[str, Any] = {}
    if include_ligatures:
        for name, (components, cp) in feature_data.ligatures.items():
            if not components:
                continue
            if name not in glyphnames.canonical_names and name not in optional_name_to_cp:
                continue
            if any(c not in glyphnames.canonical_names and c not in optional_name_to_cp for c in components):
                continue
            item: Dict[str, Any] = {"codepoint": cp, "componentGlyphs": components}
            description = _description_for_glyph(name, cp, optional, glyphnames, optional_ref, source)
            if description:
                item["description"] = description
            ligatures_section[name] = item
        if not ligatures_section and isinstance(source.get("ligatures"), dict):
            ligatures_section = source["ligatures"]
            if ligatures_section:
                report.warn("source-fallback", "Using ligatures from metadataSource (feature parsing produced none).")
        if ligatures_section:
            report.incr("ligatures", len(ligatures_section))
            report.info("ligatures-section", f"Building {len(ligatures_section)} ligatures.")

    # --- sets ---
    sets_section: Dict[str, Any] = {}
    if include_sets:
        for tag, members in feature_data.set_members.items():
            template = sets_template.get(tag)
            if template is None and isinstance(source.get("sets"), dict):
                source_set = source["sets"].get(tag)
                if isinstance(source_set, dict) and isinstance(source_set.get("type"), str) and isinstance(source_set.get("description"), str):
                    template = {"type": source_set["type"], "description": source_set["description"]}
            if not template:
                report.warn(
                    "set-template-missing",
                    f"No type/description template for stylistic set '{tag}'; "
                    "alternates are still exported, but the set entry is omitted. "
                    "Add setsTemplate in the config to supply one.",
                )
                continue
            glyphs = []
            for base, alt_name, alt_cp in sorted(members, key=lambda item: item[2]):
                if alt_name not in optional_name_to_cp and alt_name not in glyphnames.canonical_names:
                    continue
                item: Dict[str, Any] = {
                    "alternateFor": base,
                    "codepoint": alt_cp,
                    "name": alt_name,
                }
                description = _description_for_glyph(alt_name, alt_cp, optional, glyphnames, optional_ref, source)
                if description:
                    item["description"] = description
                glyphs.append(item)
            if glyphs:
                sets_section[tag] = {
                    "type": template["type"],
                    "description": template["description"],
                    "glyphs": glyphs,
                }
        if not sets_section and isinstance(source.get("sets"), dict):
            sets_section = source["sets"]
            if sets_section:
                report.warn("source-fallback", "Using sets from metadataSource (feature parsing produced none).")
        if sets_section:
            report.incr("sets", len(sets_section))
            report.info("sets-section", f"Building {len(sets_section)} stylistic sets.")

    return (anchors, bboxes, widths, optional, optional_name_to_cp,
            alternates_section, ligatures_section, sets_section)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _is_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
    )


def _is_int(value: Any) -> bool:
    return not isinstance(value, bool) and isinstance(value, int)


def _validate_point(value: Any, where: str, report: Report) -> bool:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        report.error("schema-point", f"{where} must be an array of two numbers.")
        return False
    for component in value:
        if not _is_number(component):
            report.error("schema-point", f"{where} contains a non-finite or non-numeric coordinate.")
            return False
    return True


def validate_metadata(
    metadata: Dict[str, Any],
    glyphnames: GlyphNameData,
    optional_names: Set[str],
    report: Report,
) -> bool:
    """Structurally validate the generated metadata against the specification."""
    before = len(report.errors)
    if not isinstance(metadata, dict):
        report.error("schema-root", "The metadata root must be a JSON object.")
        return False

    unknown = sorted(set(metadata) - TOP_LEVEL_KEYS)
    if unknown:
        report.error("schema-keys", "Unsupported top-level key(s): " + ", ".join(unknown))

    # fontName
    font_name = metadata.get("fontName")
    if not isinstance(font_name, str) or not font_name.strip():
        report.error("schema-fontName", "fontName is required and must be a non-empty string.")
    elif font_name != font_name.strip():
        report.warn("schema-fontName-space", "fontName has leading/trailing whitespace.")

    # fontVersion
    version = metadata.get("fontVersion")
    if not _is_number(version):
        report.error("schema-fontVersion", "fontVersion is required and must be a finite number.")
    elif float(version) < 0:
        report.error("schema-fontVersion", "fontVersion must be non-negative.")

    # designSize
    if "designSize" in metadata:
        design = metadata["designSize"]
        if not _is_int(design) or design <= 0:
            report.error("schema-designSize", "designSize must be a positive integer (decipoints).")

    # sizeRange
    if "sizeRange" in metadata:
        size_range = metadata["sizeRange"]
        if not isinstance(size_range, (list, tuple)) or len(size_range) != 2:
            report.error("schema-sizeRange", "sizeRange must be an array of two integers.")
        elif not all(_is_int(v) and v > 0 for v in size_range):
            report.error("schema-sizeRange", "sizeRange values must be positive integers.")
        elif size_range[0] > size_range[1]:
            report.error("schema-sizeRange", "sizeRange must be ascending.")

    # engravingDefaults
    if "engravingDefaults" in metadata:
        defaults = metadata["engravingDefaults"]
        if not isinstance(defaults, dict):
            report.error("schema-engravingDefaults", "engravingDefaults must be an object.")
        else:
            for key, value in defaults.items():
                if key not in ENGRAVING_KEYS:
                    report.error("schema-engraving-key", f"Unsupported engravingDefaults key '{key}'.")
                    continue
                if key == ENGRAVING_TEXT_KEY:
                    if not isinstance(value, list):
                        report.error("schema-textFontFamily", "textFontFamily must be an array of strings.")
                    elif not all(isinstance(v, str) and v.strip() for v in value):
                        report.error("schema-textFontFamily", "textFontFamily entries must be non-empty strings.")
                    elif not value:
                        report.warn("schema-textFontFamily-empty", "textFontFamily is empty.")
                    elif len(set(value)) != len(value):
                        report.warn("schema-textFontFamily-dup", "textFontFamily contains duplicate entries.")
                elif not _is_number(value) or float(value) <= 0:
                    report.error(
                        "schema-engraving-value",
                        f"engravingDefaults.{key} must be a positive finite number in staff spaces.",
                    )

    # optionalGlyphs (validate before glyphsWithAnchors so cross-checks work)
    optional_declared: Dict[str, str] = {}
    if "optionalGlyphs" in metadata:
        optional = metadata["optionalGlyphs"]
        if not isinstance(optional, dict):
            report.error("schema-optionalGlyphs", "optionalGlyphs must be an object.")
            optional = {}
        seen_cp: Dict[str, str] = {}
        for name, entry in optional.items():
            if not isinstance(name, str) or not OPTIONAL_GLYPH_NAME_RE.match(name):
                report.error("schema-optional-name", f"Invalid optional glyph name {name!r}.")
                continue
            if name in glyphnames.canonical_names:
                report.error("schema-optional-name", f"Optional glyph name '{name}' is also a canonical SMuFL name.")
            if not isinstance(entry, dict):
                report.error("schema-optional-entry", f"optionalGlyphs.{name} must be an object.")
                continue
            extra = set(entry) - {"codepoint", "classes", "description"}
            if extra:
                report.error("schema-optional-entry", f"optionalGlyphs.{name} has unsupported key(s): {', '.join(sorted(extra))}.")
            cp = entry.get("codepoint")
            if not isinstance(cp, str) or not CODEPOINT_RE.match(cp):
                report.error("schema-optional-codepoint", f"optionalGlyphs.{name}.codepoint must look like U+E000.")
                continue
            value = int(cp[2:], 16)
            if not (OPTIONAL_GLYPH_MIN <= value <= OPTIONAL_GLYPH_MAX):
                report.error(
                    "schema-optional-range",
                    f"optionalGlyphs.{name}.codepoint {cp} is outside U+F400–U+F8FF.",
                )
            if cp in seen_cp:
                report.error("schema-optional-duplicate", f"Optional codepoint {cp} is used by '{seen_cp[cp]}' and '{name}'.")
            seen_cp[cp] = name
            optional_declared[name] = cp
            classes = entry.get("classes")
            if classes is not None and (
                not isinstance(classes, list) or not all(isinstance(c, str) and c for c in classes)
            ):
                report.error("schema-optional-classes", f"optionalGlyphs.{name}.classes must be an array of strings.")
            description = entry.get("description")
            if description is not None and not isinstance(description, str):
                report.error("schema-optional-description", f"optionalGlyphs.{name}.description must be a string.")
        if optional_names:
            missing = set(optional_names) - set(optional_declared)
            extra = set(optional_declared) - set(optional_names)
            if missing or extra:
                report.error(
                    "schema-optional-crosscheck",
                    "Internal optionalGlyphs mismatch (extraction vs validation): "
                    f"missing={sorted(missing)}, extra={sorted(extra)}.",
                )
    elif optional_names:
        report.error(
            "schema-optional-missing",
            "Optional glyphs were extracted but the optionalGlyphs section is missing.",
        )

    # glyphsWithAnchors
    anchors = metadata.get("glyphsWithAnchors", {})
    if "glyphsWithAnchors" in metadata:
        if not isinstance(anchors, dict):
            report.error("schema-glyphsWithAnchors", "glyphsWithAnchors must be an object.")
            anchors = {}
        elif not anchors:
            report.warn("schema-glyphsWithAnchors-empty", "glyphsWithAnchors is empty.")
        for glyph_name, glyph_anchors in anchors.items():
            if not isinstance(glyph_name, str) or not glyph_name:
                report.error("schema-glyph-name", "glyphsWithAnchors keys must be non-empty strings.")
                continue
            if glyph_name not in glyphnames.canonical_names and glyph_name not in optional_declared:
                report.error(
                    "schema-glyph-name",
                    f"glyphsWithAnchors key '{glyph_name}' is neither a canonical SMuFL "
                    "name nor a declared optional glyph.",
                )
            if not isinstance(glyph_anchors, dict) or not glyph_anchors:
                report.error("schema-glyph-anchors", f"glyphsWithAnchors.{glyph_name} must be a non-empty object.")
                continue
            for anchor_name, value in glyph_anchors.items():
                where = f"glyphsWithAnchors.{glyph_name}.{anchor_name}"
                if anchor_name not in SUPPORTED_ANCHORS:
                    report.error("schema-anchor-name", f"{where}: unsupported SMuFL anchor name.")
                    continue
                if anchor_name in SCALAR_ANCHORS:
                    if not _is_number(value) or float(value) <= 0:
                        report.error("schema-anchor-value", f"{where} must be a positive number.")
                elif anchor_name in HYBRID_ANCHORS and _is_number(value):
                    report.warn(
                        "schema-anchor-hybrid",
                        f"{where} is a scalar; the reference Bravura data uses [x, y] for this anchor.",
                    )
                else:
                    _validate_point(value, where, report)

    # glyphBBoxes
    if "glyphBBoxes" in metadata:
        boxes = metadata["glyphBBoxes"]
        if not isinstance(boxes, dict):
            report.error("schema-glyphBBoxes", "glyphBBoxes must be an object.")
        else:
            for glyph_name, box in boxes.items():
                if glyph_name not in glyphnames.canonical_names and glyph_name not in optional_declared:
                    report.error("schema-bbox-name", f"glyphBBoxes key '{glyph_name}' is not an allowed glyph name.")
                if not isinstance(box, dict) or set(box) != {"bBoxSW", "bBoxNE"}:
                    report.error("schema-bbox", f"glyphBBoxes.{glyph_name} must contain exactly bBoxSW and bBoxNE.")
                    continue
                ok_sw = _validate_point(box["bBoxSW"], f"glyphBBoxes.{glyph_name}.bBoxSW", report)
                ok_ne = _validate_point(box["bBoxNE"], f"glyphBBoxes.{glyph_name}.bBoxNE", report)
                if ok_sw and ok_ne:
                    sw, ne = box["bBoxSW"], box["bBoxNE"]
                    if sw[0] > ne[0] or sw[1] > ne[1]:
                        report.error("schema-bbox-order", f"glyphBBoxes.{glyph_name}: bBoxSW must be southwest of bBoxNE.")

    # glyphAdvanceWidths
    if "glyphAdvanceWidths" in metadata:
        widths = metadata["glyphAdvanceWidths"]
        if not isinstance(widths, dict):
            report.error("schema-glyphAdvanceWidths", "glyphAdvanceWidths must be an object.")
        else:
            for glyph_name, width in widths.items():
                if glyph_name not in glyphnames.canonical_names and glyph_name not in optional_declared:
                    report.error("schema-width-name", f"glyphAdvanceWidths key '{glyph_name}' is not an allowed glyph name.")
                if not _is_number(width):
                    report.error("schema-width", f"glyphAdvanceWidths.{glyph_name} must be a finite number.")
                elif float(width) < 0:
                    report.warn("schema-width-negative", f"glyphAdvanceWidths.{glyph_name} is negative.")

    # glyphsWithAlternates
    if "glyphsWithAlternates" in metadata:
        alternates = metadata["glyphsWithAlternates"]
        if not isinstance(alternates, dict):
            report.error("schema-glyphsWithAlternates", "glyphsWithAlternates must be an object.")
        else:
            for base_name, entry in alternates.items():
                if base_name not in glyphnames.canonical_names:
                    report.error("schema-alternate-base", f"glyphsWithAlternates base '{base_name}' is not a canonical SMuFL name.")
                if not isinstance(entry, dict) or set(entry) != {"alternates"}:
                    report.error("schema-alternate-entry", f"glyphsWithAlternates.{base_name} must contain exactly 'alternates'.")
                    continue
                items = entry.get("alternates")
                if not isinstance(items, list) or not items:
                    report.error("schema-alternates", f"glyphsWithAlternates.{base_name}.alternates must be a non-empty array.")
                    continue
                seen = set()
                for item in items:
                    if not isinstance(item, dict) or set(item) != {"codepoint", "name"}:
                        report.error("schema-alternate-item", f"glyphsWithAlternates.{base_name} entries must contain codepoint and name.")
                        continue
                    cp = item.get("codepoint")
                    name = item.get("name")
                    if not isinstance(cp, str) or not CODEPOINT_RE.match(cp):
                        report.error("schema-alternate-codepoint", f"Invalid alternate codepoint in '{base_name}'.")
                    else:
                        value = int(cp[2:], 16)
                        if not (0xE000 <= value <= 0xF8FF):
                            report.error("schema-alternate-codepoint", f"Alternate codepoint {cp} is outside the SMuFL range U+E000–U+F8FF.")
                        elif not (OPTIONAL_GLYPH_MIN <= value <= OPTIONAL_GLYPH_MAX):
                            report.warn("schema-alternate-range", f"Alternate codepoint {cp} is outside the usual optional range U+F400–U+F8FF.")
                    if not isinstance(name, str) or not name:
                        report.error("schema-alternate-name", f"Invalid alternate name in '{base_name}'.")
                    elif name not in glyphnames.canonical_names and name not in optional_declared:
                        report.error("schema-alternate-name", f"Alternate '{name}' is not a declared optional or canonical glyph.")
                    if name in seen:
                        report.error("schema-alternate-duplicate", f"Duplicate alternate '{name}' on '{base_name}'.")
                    seen.add(name)

    # ligatures
    if "ligatures" in metadata:
        ligatures = metadata["ligatures"]
        if not isinstance(ligatures, dict):
            report.error("schema-ligatures", "ligatures must be an object.")
        else:
            for name, entry in ligatures.items():
                if name not in glyphnames.canonical_names and name not in optional_declared:
                    report.error("schema-ligature-name", f"Ligature '{name}' is not a declared optional or canonical glyph.")
                if not isinstance(entry, dict):
                    report.error("schema-ligature-entry", f"ligatures.{name} must be an object.")
                    continue
                extra = set(entry) - {"codepoint", "componentGlyphs", "description"}
                if extra:
                    report.error("schema-ligature-entry", f"ligatures.{name} has unsupported key(s): {', '.join(sorted(extra))}.")
                cp = entry.get("codepoint")
                if not isinstance(cp, str) or not CODEPOINT_RE.match(cp):
                    report.error("schema-ligature-codepoint", f"ligatures.{name}.codepoint must look like U+F5D5.")
                else:
                    value = int(cp[2:], 16)
                    if not (0xE000 <= value <= 0xF8FF):
                        report.error("schema-ligature-codepoint", f"ligatures.{name}.codepoint {cp} is outside the SMuFL range U+E000–U+F8FF.")
                components = entry.get("componentGlyphs")
                if not isinstance(components, list) or not components or not all(isinstance(c, str) and c for c in components):
                    report.error("schema-ligature-components", f"ligatures.{name}.componentGlyphs must be a non-empty array of names.")
                else:
                    for component in components:
                        if component not in glyphnames.canonical_names and component not in optional_declared:
                            report.error("schema-ligature-component", f"Ligature component '{component}' in '{name}' is not a declared glyph.")
                description = entry.get("description")
                if description is not None and not isinstance(description, str):
                    report.error("schema-ligature-description", f"ligatures.{name}.description must be a string.")

    # sets
    if "sets" in metadata:
        sets = metadata["sets"]
        if not isinstance(sets, dict):
            report.error("schema-sets", "sets must be an object.")
        else:
            for tag, entry in sets.items():
                if not isinstance(tag, str) or not re.fullmatch(r"ss\d{2}", tag):
                    report.error("schema-set-tag", f"Invalid set tag {tag!r}; expected ssNN.")
                if not isinstance(entry, dict):
                    report.error("schema-set-entry", f"sets.{tag} must be an object.")
                    continue
                extra = set(entry) - {"type", "description", "glyphs"}
                if extra:
                    report.error("schema-set-entry", f"sets.{tag} has unsupported key(s): {', '.join(sorted(extra))}.")
                for key in ("type", "description"):
                    value = entry.get(key)
                    if not isinstance(value, str) or not value.strip():
                        report.error("schema-set-string", f"sets.{tag}.{key} must be a non-empty string.")
                glyphs = entry.get("glyphs")
                if not isinstance(glyphs, list) or not glyphs:
                    report.error("schema-set-glyphs", f"sets.{tag}.glyphs must be a non-empty array.")
                    continue
                seen = set()
                for item in glyphs:
                    if not isinstance(item, dict):
                        report.error("schema-set-glyph", f"sets.{tag}.glyphs entries must be objects.")
                        continue
                    extra = set(item) - {"alternateFor", "codepoint", "name", "description"}
                    if extra:
                        report.error("schema-set-glyph", f"sets.{tag} glyph has unsupported key(s): {', '.join(sorted(extra))}.")
                    base = item.get("alternateFor")
                    if not isinstance(base, str) or base not in glyphnames.canonical_names:
                        report.error("schema-set-alternateFor", f"sets.{tag} alternateFor must be a canonical SMuFL name.")
                    cp = item.get("codepoint")
                    if not isinstance(cp, str) or not CODEPOINT_RE.match(cp):
                        report.error("schema-set-codepoint", f"sets.{tag} has an invalid codepoint.")
                    else:
                        value = int(cp[2:], 16)
                        if not (0xE000 <= value <= 0xF8FF):
                            report.error("schema-set-codepoint", f"sets.{tag} codepoint {cp} is outside the SMuFL range U+E000–U+F8FF.")
                        elif not (OPTIONAL_GLYPH_MIN <= value <= OPTIONAL_GLYPH_MAX):
                            report.warn("schema-set-range", f"sets.{tag} codepoint {cp} is outside the usual optional range U+F400–U+F8FF.")
                    name = item.get("name")
                    if not isinstance(name, str) or not name:
                        report.error("schema-set-name", f"sets.{tag} has an invalid glyph name.")
                    elif name not in glyphnames.canonical_names and name not in optional_declared:
                        report.error("schema-set-name", f"sets.{tag} glyph '{name}' is not a declared optional or canonical glyph.")
                    if name in seen:
                        report.error("schema-set-duplicate", f"sets.{tag} contains duplicate glyph '{name}'.")
                    seen.add(name)
                    description = item.get("description")
                    if description is not None and not isinstance(description, str):
                        report.error("schema-set-description", f"sets.{tag} glyph description must be a string.")

    # JSON serialisability, including NaN/Infinity rejection.
    try:
        json.dumps(metadata, allow_nan=False, ensure_ascii=False)
    except (TypeError, ValueError) as exc:
        report.error("schema-json", f"The metadata cannot be serialised as strict JSON: {exc}")

    return len(report.errors) == before


# ---------------------------------------------------------------------------
# Building and writing
# ---------------------------------------------------------------------------

def _merge_engraving_defaults(
    automatic: Dict[str, Any],
    config: Dict[str, Any],
    source: Dict[str, Any],
    report: Report,
) -> Optional[Dict[str, Any]]:
    config_value = config.get("engravingDefaults")
    source_value = source.get("engravingDefaults") if isinstance(source, dict) else None
    if not automatic and config_value is None and source_value is None:
        return None
    if config_value is not None and not isinstance(config_value, dict):
        report.error("engraving-config", "'engravingDefaults' must be an object.")
        return None
    if source_value is not None and not isinstance(source_value, dict):
        report.warn("engraving-source", "metadataSource.engravingDefaults is not an object; ignored.")
        source_value = None
    merged: Dict[str, Any] = dict(source_value or {})
    # Values measured from the current font take precedence over a stale
    # metadataSource, while explicit config values still override them.
    merged.update(automatic or {})
    if isinstance(config_value, dict):
        merged.update(config_value)
    if not merged:
        return None
    if automatic:
        report.info(
            "engraving-merge",
            f"engravingDefaults: {len(automatic)} measured from glyph geometry"
            + (", config overrides applied." if config_value else ", metadataSource fills missing keys."),
        )
    elif source_value:
        report.info("engraving-source", "Using engravingDefaults from metadataSource.")
    tff = merged.get("textFontFamily")
    if isinstance(tff, str):
        merged["textFontFamily"] = [tff] if tff.strip() else []
    elif tff is None:
        merged.pop("textFontFamily", None)
    return merged


def build_metadata(
    font: Any,
    config: Dict[str, Any],
    glyphnames: GlyphNameData,
    report: Report,
    optional_ref: Optional[Dict[str, Dict[str, Any]]] = None,
    source: Optional[Dict[str, Any]] = None,
    sets_template: Optional[Dict[str, Dict[str, str]]] = None,
) -> Tuple[Optional[Dict[str, Any]], Optional[str], Set[str]]:
    optional_ref = optional_ref or {}
    source = source or {}
    sets_template = sets_template or {}
    font_name = _font_name(font, config, report)
    version = _font_version(font, config, report)
    master = select_master(font, config, report)

    metadata: Dict[str, Any] = {}
    if font_name is not None:
        metadata["fontName"] = font_name
    if version is not None:
        metadata["fontVersion"] = version

    design = _design_size(font, config, source, report)
    if design is not None:
        metadata["designSize"] = design
    else:
        report.info("designSize-absent", "designSize is not configured; the optional field is omitted.")
    size_range = _size_range(font, config, source, report)
    if size_range is not None:
        metadata["sizeRange"] = size_range
    else:
        report.info("sizeRange-absent", "sizeRange is not configured; the optional field is omitted.")

    include_engraving = _bool_config(config, "includeEngravingDefaults", True, report)
    automatic_engraving: Dict[str, Any] = {}
    if include_engraving and master is not None:
        automatic_engraving = _compute_engraving_defaults(font, master, report)
    engraving = _merge_engraving_defaults(automatic_engraving, config, source, report) if include_engraving else None
    if engraving:
        metadata["engravingDefaults"] = engraving
    elif include_engraving:
        report.warn(
            "engraving-missing",
            "engravingDefaults could not be measured from this master and no "
            "config/metadataSource values were supplied; the optional field is omitted.",
        )

    optional: Dict[str, Dict[str, Any]] = {}
    optional_names: Set[str] = set()
    if master is not None:
        (anchors, bboxes, widths, optional, optional_name_to_cp,
         alternates_section, ligatures_section, sets_section) = _extract_glyph_data(
            font, master, glyphnames, config, report,
            optional_ref=optional_ref, source=source, sets_template=sets_template,
        )
        optional_names = set(optional_name_to_cp)
        if optional:
            metadata["optionalGlyphs"] = optional
        if widths:
            metadata["glyphAdvanceWidths"] = widths
        if anchors:
            metadata["glyphsWithAnchors"] = anchors
        if alternates_section:
            metadata["glyphsWithAlternates"] = alternates_section
        if bboxes:
            metadata["glyphBBoxes"] = bboxes
        if ligatures_section:
            metadata["ligatures"] = ligatures_section
        if sets_section:
            metadata["sets"] = sets_section
        staff = _staff_space(font, Report())
        report.info(
            "master-used",
            f"Anchor source master: '{getattr(master, 'name', '?')}' "
            f"(id {getattr(master, 'id', '?')}); staff space = "
            f"{staff:g} font units." if staff is not None else
            f"Anchor source master: '{getattr(master, 'name', '?')}' "
            f"(id {getattr(master, 'id', '?')}).",
        )
    return metadata, (str(getattr(master, "name", "")) if master is not None else None), optional_names

def _sort_nested(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sort_nested(value[key]) for key in sorted(value)}
    if isinstance(value, list):
        return [_sort_nested(item) for item in value]
    return value


def order_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Fixed top-level order, deterministic nested key order."""
    ordered: Dict[str, Any] = {}
    for key in TOP_LEVEL_ORDER:
        if key in metadata:
            ordered[key] = _sort_nested(metadata[key])
    for key in sorted(set(metadata) - set(TOP_LEVEL_ORDER)):
        ordered[key] = _sort_nested(metadata[key])
    return ordered


def write_json_atomic(path: str, metadata: Dict[str, Any]) -> int:
    text = json.dumps(
        order_metadata(metadata), indent=2, sort_keys=False,
        ensure_ascii=False, allow_nan=False,
    ) + "\n"
    payload = text.encode("utf-8")
    directory = os.path.dirname(os.path.abspath(path)) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(prefix=".smufl-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise
    return len(payload)


@dataclass
class ExportResult:
    metadata: Optional[Dict[str, Any]]
    output_path: Optional[str]
    report: Report
    master_name: Optional[str] = None
    written_bytes: int = 0

    @property
    def ok(self) -> bool:
        return self.report.ok and self.output_path is not None


def run_export(
    font: Any,
    output_path: Optional[str],
    config_path: Optional[str] = None,
    script_dir: Optional[str] = None,
    glyphnames_path: Optional[str] = None,
    report: Optional[Report] = None,
    write: bool = True,
) -> ExportResult:
    """Run the whole export without showing UI.

    This is the function used by the tests and by the Glyphs menu entry point.
    It only reads the font object; it never calls a mutating Glyphs API.
    """
    report = report or Report()
    script_dir = script_dir or SCRIPT_DIR

    auto_config_path = default_config_path(font)
    env_config_path = os.environ.get("SMUFL_CONFIG_PATH")
    if config_path is None:
        config_path = env_config_path or auto_config_path
    explicit_config = bool(env_config_path)
    if config_path is not None and not explicit_config:
        if auto_config_path is None:
            explicit_config = True
        else:
            explicit_config = os.path.abspath(config_path) != os.path.abspath(auto_config_path)
    config = load_config(config_path, report, warn_missing=explicit_config)

    glyphnames = load_glyphnames(script_dir, font, report, path_override=glyphnames_path)
    if glyphnames is None:
        return ExportResult(None, None, report)

    optional_ref = load_optional_reference(script_dir, report)
    sets_template = load_sets_template(script_dir, config, report)
    source = load_metadata_source(config, font, report)

    metadata, master_name, optional_names = build_metadata(
        font, config, glyphnames, report,
        optional_ref=optional_ref, source=source, sets_template=sets_template,
    )
    if metadata is None:
        return ExportResult(None, None, report, master_name)

    validate_metadata(metadata, glyphnames, optional_names, report)
    if report.errors:
        report.error(
            "export-aborted",
            "Validation failed; no output file was written. Fix the errors above and run again.",
        )
        return ExportResult(metadata, None, report, master_name)

    written = 0
    if write:
        if not output_path:
            report.error("output-missing", "No output path was selected; no file was written.")
            return ExportResult(metadata, None, report, master_name)
        if os.path.isfile(output_path):
            try:
                with open(output_path, "r", encoding="utf-8") as handle:
                    previous = json.load(handle)
            except Exception as exc:
                report.warn(
                    "overwrite-invalid",
                    f"Existing output {output_path} is not readable JSON ({exc}); it will be replaced.",
                )
            else:
                if previous != metadata:
                    report.warn(
                        "overwrite-diff",
                        f"Existing output {output_path} differs from the regenerated "
                        "metadata and will be replaced. Manual values must be kept in "
                        "the sidecar configuration; edits made directly to the JSON "
                        "are not merged.",
                    )
        try:
            written = write_json_atomic(output_path, metadata)
        except Exception as exc:
            report.error("write-failed", f"Could not write {output_path}: {exc}")
            return ExportResult(metadata, None, report, master_name)
        report.info("written", f"Wrote {output_path} ({written} bytes, UTF-8, strict JSON).")

    return ExportResult(metadata, output_path if write else None, report, master_name, written)


# ---------------------------------------------------------------------------
# Glyphs UI
# ---------------------------------------------------------------------------

def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[/\\:\x00-\x1f]", "_", name).strip()
    return cleaned or "SMuFLMetadata"


def _default_output_directory(font: Any) -> str:
    try:
        filepath = str(font.filepath or "")
    except Exception:
        filepath = ""
    if filepath:
        directory = os.path.dirname(filepath)
        if directory and os.path.isdir(directory):
            return directory
    return os.path.join(os.path.expanduser("~"), "Desktop")


def _choose_output_path(font: Any, report: Report) -> Optional[str]:
    env_path = os.environ.get("SMUFL_OUTPUT_PATH")
    if env_path:
        return env_path
    try:
        from AppKit import NSSavePanel, NSModalResponseOK
        from Foundation import NSURL
    except Exception:
        report.error(
            "save-panel-unavailable",
            "The save panel is unavailable outside Glyphs. Set SMUFL_OUTPUT_PATH "
            "to an explicit output path for headless use.",
        )
        return None

    font_name = _font_name(font, {}, Report()) or "SMuFLMetadata"
    panel = NSSavePanel.savePanel()
    panel.setTitle_("Export SMuFL Metadata")
    panel.setNameFieldStringValue_(_safe_filename(font_name) + ".json")
    panel.setAllowedFileTypes_(["json"])
    panel.setCanCreateDirectories_(True)
    directory = _default_output_directory(font)
    try:
        panel.setDirectoryURL_(NSURL.fileURLWithPath_(directory))
    except Exception:
        pass
    panel.setMessage_("Font-specific SMuFL metadata JSON for the currently open font.")
    if panel.runModal() != NSModalResponseOK:
        return None
    url = panel.URL()
    if url is None:
        return None
    return str(url.path())


def _show_alert(title: str, message: str, style: str = "info") -> None:
    try:
        from AppKit import (
            NSAlert,
            NSInformationalAlertStyle,
            NSWarningAlertStyle,
            NSCriticalAlertStyle,
        )
    except Exception:
        print(f"{title}: {message}")
        return
    alert = NSAlert.alloc().init()
    alert.setMessageText_(title)
    alert.setInformativeText_(message)
    if style == "error":
        alert.setAlertStyle_(NSCriticalAlertStyle)
    elif style == "warning":
        alert.setAlertStyle_(NSWarningAlertStyle)
    else:
        alert.setAlertStyle_(NSInformationalAlertStyle)
    alert.addButtonWithTitle_("OK")
    alert.runModal()


def format_report(result: ExportResult) -> str:
    report = result.report
    lines: List[str] = []
    lines.append("SMuFL metadata export")
    lines.append("=" * 60)
    if result.metadata:
        name = result.metadata.get("fontName", "?")
        version = result.metadata.get("fontVersion", "?")
        lines.append(f"Font: {name}  version {version}")
    if result.master_name:
        lines.append(f"Master: {result.master_name}")
    stats = report.stats
    if stats:
        keys = [
            ("glyphs_scanned", "glyphs scanned"),
            ("glyphs_with_anchors", "glyphs with anchors"),
            ("optional_glyphs_with_anchors", "optional glyphs with anchors"),
            ("glyph_bboxes", "glyph bboxes"),
            ("glyph_widths", "advance widths"),
            ("alternate_bases", "alternate base glyphs"),
            ("ligatures", "ligatures"),
            ("sets", "stylistic sets"),
            ("glyphs_without_master_layer", "glyphs without master layer"),
            ("glyphs_not_exported", "non-exporting glyphs skipped"),
        ]
        parts = [f"{label}: {stats[key]}" for key, label in keys if key in stats]
        if parts:
            lines.append("; ".join(parts))
    if result.metadata:
        lines.append("Fields: " + ", ".join(sorted(result.metadata.keys())))
    lines.append("")
    for issue in report.errors:
        lines.append(f"ERROR   [{issue.code}] {issue.message}")
    for issue in report.warnings:
        lines.append(f"WARNING [{issue.code}] {issue.message}")
    for issue in report.infos:
        lines.append(f"INFO    [{issue.code}] {issue.message}")
    lines.append("")
    if report.ok:
        lines.append(
            f"Validation passed: 0 errors, {len(report.warnings)} warning(s)."
        )
    else:
        lines.append(
            f"Validation FAILED: {len(report.errors)} error(s), "
            f"{len(report.warnings)} warning(s). No file was written."
        )
    if result.output_path and report.ok:
        lines.append(f"Output: {result.output_path}")
    return "\n".join(lines)


def _fallback_dialog(title: str, message: str) -> None:
    """Show a native dialog without PyObjC (osascript), for missing objc."""
    try:
        import subprocess
        safe_message = " ".join(str(message).splitlines())
        script = (
            f'display dialog {json.dumps(safe_message, ensure_ascii=False)} '
            f'with title {json.dumps(title, ensure_ascii=False)} '
            'buttons {"OK"} default button "OK" with icon caution'
        )
        subprocess.run(["osascript", "-e", script], check=False, capture_output=True)
    except Exception as exc:
        _debug(f"osascript fallback failed: {exc!r}")


def main() -> None:
    _debug("main() entered")
    glyphs_app = globals().get("Glyphs")
    if glyphs_app is not None and hasattr(glyphs_app, "font"):
        _debug("using injected Glyphs runtime object")
    else:
        glyphs_app = None
        try:
            # Glyphs 4 的标准方式是 GlyphsApp.Glyphs（GSApplication 实例）。
            # 某些环境也会注入名为 Glyphs 的模块；两种都兼容。
            from GlyphsApp import Glyphs as glyphs_app  # type: ignore
            _debug("imported GlyphsApp.Glyphs")
        except Exception as exc:
            _debug(f"GlyphsApp import failed: {exc!r}")
            try:
                import Glyphs as glyphs_app  # type: ignore
                _debug("imported Glyphs module")
            except Exception as exc2:
                _debug(f"Glyphs import failed: {exc2!r}")
                print("This script must be run from inside Glyphs 4 (Script menu).")
                python_path = sys.executable or "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3"
                message = (
                    "Glyphs 4 当前使用的 Python 缺少 PyObjC (objc)，因此无法访问 "
                    "Glyphs API。\n\n请在“终端”运行：\n"
                    f"{python_path} -m pip install --user pyobjc-framework-Cocoa\n\n"
                    "安装完成后完全退出并重新打开 Glyphs 4，再运行本脚本。\n\n"
                    f"诊断日志：{DEBUG_LOG_PATH}"
                )
                _show_alert("Glyphs 运行环境缺少 PyObjC", message, "error")
                _fallback_dialog("Glyphs 运行环境缺少 PyObjC", message)
                return

    try:
        font = getattr(glyphs_app, "font", None)
    except Exception as exc:
        _debug(f"reading Glyphs.font failed: {exc!r}")
        font = None
    _debug(f"font={font!r}")
    if font is None:
        _show_alert(
            "No font is open",
            "Open a Glyphs 4 font project before running Export SMuFL Metadata JSON.",
            "warning",
        )
        return

    report = Report()
    try:
        config_path = os.environ.get("SMUFL_CONFIG_PATH") or default_config_path(font)
        _debug(f"config_path={config_path!r}")
        output_path = _choose_output_path(font, report)
        _debug(f"output_path={output_path!r}")
        if output_path is None:
            if report.errors:
                _show_alert("Export cancelled", "\n".join(i.message for i in report.errors), "error")
            return
        result = run_export(
            font,
            output_path,
            config_path=config_path,
            script_dir=SCRIPT_DIR,
            report=report,
        )
        _debug(f"run_export done: ok={result.report.ok} errors={len(result.report.errors)}")
        text = format_report(result)
        print(text)
        if not result.report.ok:
            errors = [i.message for i in result.report.errors]
            more = "" if len(errors) <= 6 else f"\n… and {len(errors) - 6} more (see Macro Window)."
            _show_alert(
                "SMuFL export failed",
                "\n".join(errors[:6]) + more,
                "error",
            )
        # Success is intentionally silent apart from the Macro Window report:
        # one native save panel, no extra modal dialog.
    except Exception:
        _debug("main() traceback:\n" + traceback.format_exc())
        traceback.print_exc()
        _show_alert(
            "SMuFL export failed",
            "An unexpected error occurred. See the Macro Window for the traceback.",
            "error",
        )


# Glyphs executes script files rather than importing them, and may not set
# __name__ to "__main__".  Run the entry point unconditionally; set
# SMUFL_EXPORTER_NO_MAIN=1 when importing this file as a library or test.
if not os.environ.get("SMUFL_EXPORTER_NO_MAIN"):
    _debug("entry point: calling main()")
    main()
