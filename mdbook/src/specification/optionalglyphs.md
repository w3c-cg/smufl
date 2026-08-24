### optionalGlyphs

The "optionalGlyphs" structure contains a list of all the optional glyphs
(those in the range of code points U+F400–U+F8FF) contained within the font.
Applications that cannot use advanced OpenType features can use this structure
to identify the presence of stylistic alternates (though the
"glyphsWithAlternates" and "sets" structures also specify the original glyphs
for each alternate by name).

However, a font designer may choose to include some characters in his
font that are neither recommended characters in the core SMuFL ranges
nor alternates for any of those characters, i.e. completely private to
the particular font. This structure provides a direct way for a
consuming application to identify the name, code point, and optional
class (or classes) for each optional glyph in the font.

Below is an excerpt from a dummy font metadata file for Bravura, with a
section of the "optionalGlyphs" structure filled in:

```
{
  ...
  "optionalGlyphs": {
    "accdnPushAlt": {
      "classes": [],
      "codepoint": "U+F45B"
    },
    "accidentalDoubleFlatJoinedStems": {
      "classes": [
        "accidentals",
        "accidentalsSagittalMixed",
        "accidentalsStandard",
        "combiningStaffPositions"
      ],
      "codepoint": "U+F4A1"
    },
    "accidentalDoubleFlatParens": {
      "codepoint": "U+F566"
    },
    ...
  },
  ...
}
```

The structure uses the name of each optional glyph as the key, and the
values include the code point and an optional list of classes to which
the glyph belongs. (The class names should be taken from the
classes.json SMuFL metadata file where possible, though font designers
can define new classes as required.)
