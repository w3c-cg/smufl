# Glyphs 4: SMuFL metadata exporter

`generate_font_metadata.py` writes the SMuFL font-specific metadata JSON for
the font currently open in Glyphs 4.

## Requirements

- Glyphs 4 on macOS.
- Python 3 with PyObjC. Glyphs 2 used Python 2.7; Glyphs 3 moved its scripting
  environment to Python 3, and Glyphs 4 continues on Python 3. The `objc` and
  `AppKit` modules are normally available in the Python that Glyphs uses. If
  the script reports that they are missing, install PyObjC for that Python and
  restart Glyphs.

## Installation

Copy these files into:

```
~/Library/Application Support/Glyphs 4/Scripts/
```

- `generate_font_metadata.py`
- `smufl_glyphnames.json`
- `smufl_optional_reference.json`
- `smufl_sets_template.json`

Then open Glyphs and choose **Script > Export SMuFL Metadata JSON**. If the
entry does not appear, hold Option and choose **Script → Reload Scripts**
(Cmd-Opt-Shift-Y), or restart Glyphs.

## Usage

1. Open a `.glyphs` project.
2. Run **Script > Export SMuFL Metadata JSON**.
3. Choose where to save the JSON. The default is `<font name>.json` next to the
   project.

The script never modifies the project. Fields without values are omitted.

## Configuration

The script works without configuration. There are two optional ways to override
values:

- **Glyphs custom parameters**: add `SMuFL Design Size` or `SMuFL Size Range` in
  Font Info → Font → Custom Parameters. Both use decipoints (1/720 inch):
  `120` = 12 pt, `80, 480` = 8–48 pt.
- **A config file**: copy `smufl-config.example.json` to
  `<project file name>.smufl-config.json` next to the `.glyphs` file. The name
  comes from the project file, not the family name; `null` means "do not
  override".

The config file can also override `engravingDefaults`, choose a `master`,
supply `glyphNameAliases` or manual `glyphsWithAnchors`, point at a
`metadataSource`, and switch sections with the `include*` flags. When both are
set, the config file wins over the custom parameters.

See `smufl-config.example.json` for all keys and units.

## Glyph names

The script does not rename glyphs. For the compiled font, Glyphs derives the
production name from the glyph's Unicode value (`uniE050`), so make sure every
SMuFL glyph has its Unicode set before the final font export. If your workflow
relies on glyph names matching codepoints, run your usual rename step before
exporting.

## Files

- `generate_font_metadata.py` — the script.
- `smufl_glyphnames.json` — glyph names, codepoints, descriptions and classes,
  generated from this repository's metadata.
- `smufl_optional_reference.json` — descriptions and classes for optional
  glyphs, derived from Bravura.
- `smufl_sets_template.json` — stylistic set template, derived from Bravura.
- `smufl-config.example.json` — optional configuration example.

## Previous scripts

The scripts previously in this folder were written by Ben Timms (Steinberg
Media Technologies GmbH, 2018) for Glyphs 2 and Python 2. They are replaced by
this Glyphs 4 version. The original attribution is kept here.

A companion Glyphs plugin and SMuFL sidebar package are maintained at:
https://github.com/Shinianqi/SMuFL-Glyphs4

## License

The script may be used, distributed and edited as you wish, like the scripts
it replaces. The Bravura-derived files (`smufl_optional_reference.json`,
`smufl_sets_template.json`) are under the SIL Open Font License 1.1; see
`LICENSE-OFL-1.1.txt`.
