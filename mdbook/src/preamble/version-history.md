Version history
===============

Version 1.50 (2022):

-   Added `timeSigOpenChinese` (U+EC87) to [Time signatures supplement](../tables/time-signatures-supplement.md) range ([#172](https://github.com/w3c/smufl/issues/172))

Version 1.40 (2021-03-15):

-   Added new font metadata values for font design size, barline separation, H-bar thickness, and preferred text fonts to accompany music fonts ([#95](https://github.com/w3c/smufl/issues/95), [#102](https://github.com/w3c/smufl/issues/102), [#124](https://github.com/w3c/smufl/issues/124), [#131](https://github.com/w3c/smufl/issues/131))
-   Added clarification for registration of glyphs in the [Rests](../tables/rests.md) range ([#100](https://github.com/w3c/smufl/issues/100))
-   Added `fingeringQLower` (U+ED8E) and `fingeringSLower` (U+ED8F) glyphs in the [Fingering supplement](../tables/fingering-supplement.md) range
-   Added `figbassTripleFlat` (U+ECC1) and `figbassTripleSharp` (U+ECC2) in the [Figured bass supplement](../tables/figured-bass-supplement.md) range
-   Added headless notes (U+E204–U+E20A) to [Beamed groups of notes](../tables/beamed-groups-of-notes.md) range ([#77](https://github.com/w3c/smufl/issues/77))
-   Added glyphs to new [Scale degrees](../tables/scale-degrees.md) range (U+EF00–U+EF07) ([#64](https://github.com/w3c/smufl/issues/64))
-   Added glyphs in new [Note name noteheads supplement](../tables/note-name-noteheads-supplement.md) range (U+EEE0–U+EEFF) ([#82](https://github.com/w3c/smufl/issues/82))
-   Added `mensuralWhiteSemibrevis` (U+E962) to [Medieval and Renaissance individual notes](../tables/medieval-and-renaissance-individual-notes.md) range
-   Added `guitarString10`, `guitarString11`, `guitarString12`, `guitarString13` (U+E84A–U+E84D) to [Guitar](../tables/guitar.md) range ([#81](https://github.com/w3c/smufl/issues/81))
-   Added glyphs in [Medieval and Renaissance prolations supplement](../tables/medieval-and-renaissance-prolations-supplement.md) (U+EE90–U+EE94) ([#88](https://github.com/w3c/smufl/issues/88))
-   Added Cowell's noteheads for irrational durations (U+EEA1–U+EEB5) to [Noteheads supplement](../tables/noteheads-supplement.md) range ([#93](https://github.com/w3c/smufl/issues/93))
-   Added `noteheadNancarrowSine` (U+EEA0) in [Noteheads supplement](../tables/noteheads-supplement.md) range ([#92](https://github.com/w3c/smufl/issues/92))
-   Added `arpeggiato` (U+E63C) to [Plucked techniques](../tables/plucked-techniques.md) range ([#97](https://github.com/w3c/smufl/issues/97))
-   Added `caesuraSingleStroke` (U+E4D7) to the [Holds and pauses](../tables/holds-and-pauses.md) range ([#108](https://github.com/w3c/smufl/issues/108))
-   Added Alois Hába's set of accidentals for 24-EDO quarter-tones (U+EE63–U+EE69) to the [Other accidentals supplement](../tables/other-accidentals.supplement.md) range ([#109](https://github.com/w3c/smufl/issues/109))
-   Added [Chop (percussive bowing) notation](../tables/chop-percussive-bowing-notation.md) range (U+EE80–U+EE8F) ([#115](https://github.com/w3c/smufl/issues/115))
-   Added `swissRudimentsNoteheadBlackFlam` (U+EE70), `swissRudimentsNoteheadHalfFlam` (U+EE71), `swissRudimentsNoteheadBlackDouble` (U+EE72), `swissRudimentsNoteheadHalfDouble` (U+EE73) to the new [Techniques noteheads](../tables/techniques-noteheads.md) range ([#118](https://github.com/w3c/smufl/issues/118))
-   Changed registration of `fretboardFilledCircle` (U+E858), `fretboardX` (U+E859) and `fretboardO` (U+E85A) so that they are centred vertically and horizontally around the origin ([#117](https://github.com/w3c/smufl/issues/117))
-   Added ups and downs accidentals (U+EE60–U+EE63) to new [Other accidentals supplement](../tables/other-accidentals-supplement.md) range ([#124](https://github.com/w3c/smufl/issues/124))
-   Added recommended stylistic alternates for U+E4A0 and U+E4A1, Rossini accent above and below ([#134](https://github.com/w3c/smufl/issues/134))
-   Added [Extended Helmholtz-Ellis accidentals (just intonation) supplement](../tables/extended-helmholtz-ellis-accidentals-just-intonation-supplement.md) range (U+EE50–U+EE5F); revised appearance of `accidentalCombiningLower31Schisma` (U+E2EC) and `accidentalCombiningRaise31Schisma` (U+E2ED) ([#126](https://github.com/w3c/smufl/issues/126))
-   Added glyphs to the [Olympian Sagittal extension (extreme precision) accidental diacritics](../tables/olympian-sagittal-extension-extreme-precision-accidental-diacritics.md) (U+E3F4–U+E3F7) and [Magrathean Sagittal extension (insane precision) accidental diacritics](../tables/magrathean-sagittal-extension-insane-precision-accidental-diacritics.md) (U+E3F8–U+E41F) ranges of Sagittal accidentals ([#156](https://github.com/w3c/smufl/issues/156))
-   Added clarification to the [Beamed groups of notes](../tables/beamed-groups-of-notes.md), [Metronome marks](../tables/metronome-marks.md) and [Standard accidentals for chord symbols](../tables/standard-accidentals-for-chord-symbols.md) ranges that these glyphs should all follow the guidelines for text-based applications, even in fonts primarily intended for use with scoring applications ([#178](https://github.com/w3c/smufl/issues/178))

Version 1.30 (2019-01-14):

-   This specification is now published under the terms of the W3C Community Final Specification Agreement (FSA) ([#38](https://github.com/w3c/smufl/issues/38))
-	Added `dynamicCombinedSeparatorSlash` (U+E549)
-	Added `keyboardPedalParensLeft` (U+E676) and `keyboardPedalParensRight` (U+E677)
-	Added new [Chord symbol accidentals](../tables/standard-accidentals-for-chord-symbols.md) range (U+ED60-U+ED66)
-	Added new glyphs to the [Fingering](../tables/fingering.md) range, with digits between 6 and 9, parentheses, brackets, and middle dot separator
-	Added new [Kahnotation](../tables/kahnotation.md) range, with thanks to Matthew Dougherty, Sam Katz and Sam Weber (U+EDA0–U+EDF1) ([#58](https://github.com/w3c/smufl/issues/58))
-	Added new [German organ tablature](../tables/german-organ-tablature.md) range, with thanks to John McKean (U+EE00–U+EE3F) ([#72](https://github.com/w3c/smufl/issues/72))
-	Added new [Clefs supplement](../tables/clefs-supplement.md) range, including new universal Indian drum notation clef (U+ED70)
-	Added new [Fingering supplement](../tables/fingering-supplement.md) range, with italic fingering digits, parentheses and brackets (U+ED80-U+ED8D)
-	Added more separators for brass fingering (U+ED2D–U+ED2E) to [Fingering](../tables/fingering.md) range
-	Added `pictBeaterMalletDown` (U+E7EC), `pictBeaterBrassMalletsRight` (U+E7ED), `pictBeaterBrassMalletsLeft` (U+E7EE), `pictTriangleBeaterPlain` (U+E7EF) to [Beaters pictograms](../tables/beaters-pictograms.md) range ([#73](https://github.com/w3c/smufl/issues/73), [#66](https://github.com/w3c/smufl/issues/66))
-	Added `vocalHalbGesungen` (semi-sprechgesang) to [Vocal techniques](../tables/vocal-techniques.md) range (U+E64B) ([#68](https://github.com/w3c/smufl/issues/68))
-	Added separate glyphs for upper dot, lower dot and central slash (U+E503–U+E505) to [Bar repeats](../tables/bar-repeats.md) range, to allow construction of bar repeats for arbitrary number of bars ([#62](https://github.com/w3c/smufl/issues/62))
-	Added `lyricsTextRepeat` glyph (U+E555) to [Lyrics](../tables/lyrics.md) range ([#61](https://github.com/w3c/smufl/issues/61))
-	Added one-handed roll (U+E233) and double lateral roll (U+E234) for mallet percussion, popularised by Leigh Howard Stevens, to [Tremolos](../tables/tremolos.md) range ([#56](https://github.com/w3c/smufl/issues/56))
-   Clarified `legerLineExtension` engraving default scales according to notehead size ([#70](https://github.com/w3c/smufl/issues/70))
-   Clarified that bounding box cut-out coordinates are relative to the glyph origin, i.e. its bottom left-hand corner ([#90](https://github.com/w3c/smufl/issues/90))
-	Added recommended optional glyphs for tuplet digits in lighter weight to the [Tuplets](../tables/tuplets.md) range
-   Added recommended optional glyphs for optical variants for some chord symbols glyphs, e.g. +/- for augmented/diminished chord quality for the [Chord symbols](../tables/chord-symbols.md) range
-   Added recommended optional glyphs for optical variants for chord symbol accidentals shown at smaller sizes for the new [Chord symbol accidentals](../tables/standard-accidentals-for-chord-symbols.md) range
-   Added recommended optional glyphs for oversized versions of the [Slash notehead](../tables/slash-noteheads.md) range
-   Added recommended optional glyphs for new large, narrow bold serif time signatures in [Time signatures](../tables/time-signatures.md) and [Time signatures supplement](../tables/time-signatures-supplement.md) ranges
-   Expanded range of recommended optional glyphs for large, narrow sans serif time signatures to complete [Time signatures](../tables/time-signatures.md) and [Time signatures supplement](../tables/time-signatures-supplement.md) ranges

Version 1.20 (2016-04-25):

-	Added double whole note slash notehead (U+E10A) ([#19](https://github.com/w3c/smufl/issues/19)).
-	Added double-slashed black and white round noteheads, often used to denote striking piano strings (U+E11C, U+E11D) ([#22](https://github.com/w3c/smufl/issues/22)).
-	Added irregular tremolo mark, used by Stockhausen (U+E232) ([#48](https://github.com/w3c/smufl/issues/48))
-	Added square brackets for editorial accidentals (U+E26C, U+E26D) ([#10](https://github.com/w3c/smufl/issues/10))
-	Added equal-tempered quarter-tone flat and quarter-tone sharp, combining glyphs to raise and lower by a 53-limit comma, and tilde and equals characters to indicate enharmonic equivalence, to the [Extended Helmholtz-Ellis accidentals (just intonation)](../tables/extended-helmholtz-ellis-accidentals-just-intonation.md) range (U+E2F5-U+E2FB) ([#24](https://github.com/w3c/smufl/issues/24))
-	Added quarter-tone sharp and flat accidentals, used by Ferneyhough (U+E48E, U+E48F) ([#23](https://github.com/w3c/smufl/issues/23))
-	Added parentheses and brackets for hairpins (U+E542–U+E545) ([#42](https://github.com/w3c/smufl/issues/42))
-	Added hyphen, colon, and space separators for use in combined dynamics, e.g. **p-mp** (U+E546–U+E548) ([#43](https://github.com/w3c/smufl/issues/43))
-	Added brass valve trill to [Brass techniques](../tables/brass-techniques.md) range (U+E5EF) ([#25](https://github.com/w3c/smufl/issues/25))
-	Added wind mouthpiece pop and rim only to [Wind techniques](../tables/wind-techniques.md) range (U+E60A, U+E60B) ([#25](https://github.com/w3c/smufl/issues/25))
-	Added bow behind bridge on one, two, three, or four strings to [String techniques](../tables/string-techniques.md) range (U+E627–U+E62A) ([#26](https://github.com/w3c/smufl/issues/26))
-	Added nasal voice ([#27](https://github.com/w3c/smufl/issues/27)), tongue click, finger click, and tongue and finger click (as used by Stockhausen) to [Vocal techniques](../tables/vocal-techniques.md) range (U+E648–U+E64A) ([#49](https://github.com/w3c/smufl/issues/49))
-	Added L and reversed-L hooks used instead of Ped. to start and stop sustain pedal indications to [Keyboard techniques](../tables/keyboard-techniques.md) range (U+E672, U+E673) ([#17](https://github.com/w3c/smufl/issues/17))
-	Added pedal-to-heel and heel-to-pedal transitions to [Keyboard techniques](../tables/keyboard-techniques.md) range (U+E674, U+E675) ([#28](https://github.com/w3c/smufl/issues/28))
-	Added damp low strings, damp with both hands, damp below, damp above, metallic sounds on a single string, isolated sounds, and snare drum techniques as used by Salzedo to 'Harp techniques' range (U+E697–U+E69D) ([#29](https://github.com/w3c/smufl/issues/29))
-	Added clockwise variant of scrape around rim to 'Percussion playing technique pictograms' range (U+E80E) ([#30](https://github.com/w3c/smufl/issues/30))
-	Added full barré and half-barré to [Guitar](../tables/guitar.md) range (U+E848, U+E849), plus recommended stylistic alternate with horizontal fraction slash for half-barré ([#14](https://github.com/w3c/smufl/issues/14))
-	Added unconducted/free passages to [Conductor symbols](../tables/conductor-symbols.md) range (U+E89A) ([#31](https://github.com/w3c/smufl/issues/31))
-	Added upper case F, I, K, L, and lower case i, k, l, glyphs to existing [Function theory symbols](../tables/function-theory-symbols.md) range (U+EA99–U+EA9F), plus a new [Function theory symbols supplement](../tables/function-theory-symbols-supplement.md) range including upper case M and N, and lower case m and r (U+ED00–U+ED03) ([#32](https://github.com/w3c/smufl/issues/32))
-	Added "cut 3" to [Time signatures supplement](../tables/time-signatures-supplement.md) range (U+EC86) ([#16](https://github.com/w3c/smufl/issues/16))
-	Added diminished 7 to new [Figured bass supplement](../tables/figured-bass-supplement.md) range (U+ECC0) ([#9](https://github.com/w3c/smufl/issues/9))
-	Added new [Shape note noteheads supplement](../tables/shape-note-noteheads-supplement.md) range containing double whole note versions of all of the different notehead shapes in the existing 'Shape note noteheads' range (U+ECD0–U+ECDD) ([#18](https://github.com/w3c/smufl/issues/18))
-	Added turned time signature digits, common time and cut common time (U+ECE0–U+ECEB) ([#21](https://github.com/w3c/smufl/issues/21))
-	Added reversed time signature digits, common time and cut common time (U+ECF0–U+ECFB) ([#21](https://github.com/w3c/smufl/issues/21))
-	Added new [Fingering](../tables/fingering.md) range, containing digits bold 0–5 suitable for keyboard fingering, and a variety of symbols used in guitar fingering (U+ED10–U+ED23) ([#34](https://github.com/w3c/smufl/issues/34))
-	Added new [Arabic accidentals](../tables/arabic-accidentals.md) range (U+ED30–U+ED38) ([#44](https://github.com/w3c/smufl/issues/44))
-	Added new [Articulation supplement](../tables/articulation-supplement.md) range containing so-called "soft accent", plus combinations with staccato and tenuto (U+ED40–U+ED47) ([#35](https://github.com/w3c/smufl/issues/35))
-	Added new [Stockhausen accidentals (24-EDO)](../tables/stockhausen-accidentals-24-edo.md) range (U+ED50–U+ED5E) ([#51](https://github.com/w3c/smufl/issues/51))
-	Added stylistic alternates for cClef and cClefChange in the style of 20th century French publishers ([#11](https://github.com/w3c/smufl/issues/11))
-	Added stylistic alternates for 15/22 octave markings using 16/24, as used by some 20th century French publishers ([#20](https://github.com/w3c/smufl/issues/20))
-	Added stylistic alternates for `wiggleArpeggiatoUpSwash` and `wiggleArpeggiatoDownSwash` based on Couperin's *L'Art de Toucher Le Clavecin* ([#33](https://github.com/w3c/smufl/issues/33))
-	Changed the appearance of `clefBridge` (U+E078) to match the design used by Lachenmann in *...zwei Gefühle...* and added a stylistic alternate with the previous design ([#8](https://github.com/w3c/smufl/issues/8))
-   Changed specification for font metadata locations on Linux to match the
    recommendations of the XDG Base Directory Specification
    ([#39](https://github.com/w3c/smufl/issues/39)).
-   Converted license for SMuFL specification from MIT License to W3C
    Community Contributor License Agreement (CLA) Deed
    ([#37](https://github.com/w3c/smufl/issues/37)).
-	Fixed the appearance of figBassRaised5 to have a forward slash rather than a backward slash, the correct appearance for a diminished fifth (U+EA5A) ([#9](https://github.com/w3c/smufl/issues/9))

Version 1.19 (2015-08-07):

-   Corrected implementation notes to clarify how brace glyphs should be
    handled by consuming applications: rather than scaling them only in
    the vertical dimension to fit the height of the staves being braced,
    they should be scaled proportionally.

Version 1.18 (2015-05-18):

-   Added specification of locations for font-specific metadata to be
    installed on Windows, OS X, and Linux, to aid consuming applications
    in the identification of SMuFL-compliant fonts.

-   Added recommendation that characters in ranges that will typically
    be drawn using runs of text (e.g. time signature digits, octave line
    labels, figured bass, and function theory symbols) should have
    appropriate non-zero side bearings.

-   Reworked the triangular clefs in the **Clefs** range between U+E06F
    and U+E072 to match the descriptions given of their use by Schäffer
    in Karkoschka’s book. This involved changing the names and
    descriptions of these glyphs as follows: U+E06F was cClefTriangular,
    now schaefferClef; U+E070 was fClefTriangular, now
    schaefferPreviousClef; U+E071 was cClefTriangularToFClef, now
    schaefferGClefToFClef; U+E072 was fClefTriangularToCClef,
    now schaefferFClefToGClef.

-   Added z-style quarter (crotchet) rest to the **Rests** range.

Version 1.17 (2015-04-29):

-   Added specification of new optionalGlyphs structure for
    font-specific metadata to provide information about non-core glyphs
    included in fonts.

-   Added specification of the name of the glyph for which the glyph in
    a stylistic set is an alternate to the sets structure in
    font-specific metadata.

-   Added new implementation notes concerning noteWholeEmpty,
    noteHalfEmpty, and noteBlackEmpty in the **Note name
    noteheads** range.

-   Added new **Metronome marks** range, with stem up and stem down
    notes intended to be proportioned for setting in line with
    characters from a regular text font; specifically, it is recommended
    that stems are shortened by 0.75 spaces from their default length.

-   Clarified role of **Individual notes** range, which is that notes in
    this range are intended for drawing on a stave, and as such should
    have the default stem length (3.5 spaces minimum).

-   Added baseline and superscript italic *a*, *b*, *m*, and *v*
    characters to the **Octaves supplement** range, to allow the
    creation of arbitrary octave line markers beyond those included in
    the **Octaves** range.

-   Added marcato-tenuto above/below composites to the
    **Articulation** range.

-   Added alternative “raised 6” character to the **Figured
    bass** range.

Version 1.12 (2015-01-07):

-   Added specification of new noteheadOrigin anchor points for the
    glyphsWithAnchors structure to help with the correct alignment of
    noteheads that have left-hand side bearings with those that do not.

-   Added specification of new opticalCenter anchor points for the
    glyphsWithAnchors structure to help with the correct balancing of
    glyphs that should be centered on noteheads and stems (e.g.
    dynamics)

-   Added new **Time signatures supplement** range, with square brackets
    for the whole time signature and numerator only, the slash separator
    sometimes used for interchangeable time signatures, and new
    timeSig2Cut glyph, used by Bach and other composers of that period
    as an alternative to the normal cut common (*alla breve*) symbol.

-   Added new **Octaves supplement** range, with *loco*
    text (octaveLoco). Revised the existing **Octaves** range,
    correcting the recommended appearance of the *ottava bassa*,
    *quindicesima bassa*, and *ventiduesima bassa* glyphs, and adding
    new glyphs for commonly-used but incorrect abbreviations for
    these glyphs.

-   Added missing stem down noteheads for smnSharp and smnSharpWhite in
    the **Simplified Music Notation** range.

-   Added Salzedo’s symbols for ascending and descending Aeolian chords
    to the **Harp techniques** range.

-   Added short, medium, and long smooth lifts to the **Brass techniques**
    range.

-   Added *Hauptrhythmus* and *Choralmelodie*, as used by Alban Berg, to
    the **Analytics** range.

Version 1.0 (2014-06-16):

-   Now that SMuFL has reached 1.0, the code points and glyph names for
    all current glyphs will not change in future revisions.

-   Added specification for new splitStemUpSE, splitStemUpSW,
    splitStemDownNW and splitStemDownNE anchors in font-specific
    metadata to define stem connection points for altered unisons.

-   Added punctum deminutum (chantPunctumDeminutum) glyph to **Medieval
    and Renaissance plainchant single-note forms** range.

Version 0.99 (2014-06-02):

-   Modified the specification of the glyphsWithBBoxes structure in the
    font-specific JSON metadata such that the glyph’s name is the
    primary key, rather than the value of a name key, which makes it
    easier to consume this data.

-   Added an optional description key to the sets structure in the
    font-specific JSON metadata, to contain a human-readable description
    of a stylistic set.

-   Added a new fourth value to the type key for the sets structure, for
    large time signature digits intended for drawing outside the staff.

-   Added specification of new graceNoteSlashSW, graceNoteSlashNE,
    graceNoteSlashNW and graceNoteSlashSE anchor points for the
    glyphsWithAnchors structure to help with the correct positioning of
    slashes on stem up and stem down flags of unbeamed grace notes.

-   Added specification of new repeatOffset anchor point for the
    glyphsWithAnchors structure to help with the correct registration of
    tessellating glyphs.

-   Added clarifications in the glyph registration guidelines for fonts
    intended for use in scoring applications that parentheses glyphs may
    have negative side bearings to improve default kerning of these
    glyphs with the symbols they are intended to bracket; likewise,
    tessellating glyphs (such as the wiggle that follows the  symbol)
    may have negative side bearings to produce correct tessellation when
    set in a single run of text.

-   Added 8 and 15 digits scaled correctly for positioning on G and
    F clefs.

-   Added recommended stylistic alternates for common time, cut time
    and + intended for use as large time signatures printed above
    the staff.

-   Added a set of noteheads enclosed in large circles, used by
    some drummers.

-   Added an ornate X notehead contained within an ellipse.

-   Added Couperin’s *pincé* and *tremblement appuyé* ornaments.

-   Redesigned the thumb position string technique glyph to more closely
    resemble a zero digit, and added a turned version.

-   Added a zero-width rectangle intended to enclose single percussion
    beaters inside a box.

-   Added strum direction arrows for guitar, and a stylistic alternate
    for the golpe glyph as used by Antonis Vounelakos.

-   Added an additional raised 7 digit for figured bass.

-   Added left- and right-pointing arrows for use in metric modulations.

-   Added recommended ligatures for combining Johnston accidentals with
    standard sharp and flat accidentals.

-   Removed the ranges of glyphs for wind instrument fingering charts.

Version 0.9 (2014-04-17):

-   Expanded the specification of font-specific metadata to include new
    structures to describe stylistic alternates, stylistic sets and
    ligatures present in fonts for applications that cannot access
    advanced font features.

-   Defined new values for the “glyphs” structure in font-specific
    metadata to describe cut-outs from the four corners of a glyph’s
    bounding box, in order to allow better kerning or interlocking of
    glyphs in some circumstances, e.g. when stacking accidentals; also
    renamed this structure to “glyphsWithAnchors” to clarify
    its purpose.

-   Defined specification for new ranges.json file, which provides
    information about the ranges of glyphs described in this
    specification in a machine-readable fashion.

-   Added initial glyph registration and font metrics guidelines for
    fonts intended for use in text-based applications.

-   Added new range for Kodály solfège hand signs.

-   Added new range for Peter Hayes George’s Simplified Music Notation.

-   Added narrow and wide versions of the sine wave, square wave and
    sawtooth wavy lines in the **Multi-segment lines** range.

-   Added wide versions of the black and white diamond noteheads, as
    used in some handbells music.

-   Added turned (i.e. inverted) versions of up bow and down bow marks.

-   Added *oriscus liquescens* to the **Medieval and Renaissance
    plainchant single-note forms** range, and moved *punctum auctum
    inclinatum* and *punctum auctum diminutum* to this range.

-   Added *strophicus liquescens* (for intervals of a second up to
    a fifth) to the **Medieval and Renaissance plainchant multiple-note
    forms** range.

-   Added oblique ligature forms for mensural notes describing intervals
    of a second up to a fifth for black, void, black and void, and white
    noteheads to a new **Medieval and Renaissance oblique forms** range.

-   Added single glyph for right and left repeat barlines to the
    **Repeats** range, and a recommended stylistic alternate using
    thick-thick rather than thin-thick-thin barlines.

-   Added reversed versions of brackets to denote play with right/left
    hand in the **Keyboard techniques** range, to allow the demarcation
    of the end of a passage to be played with the other hand.

-   Added more recommended stylistic alternates for display on smaller
    staff sizes: time signature digits; G, C and F clef; black, half,
    whole and double whole noteheads; standard articulations; dynamics
    letter forms.

-   Added recommended ligatures for standard noteheads and accidentals
    in parentheses.

-   Added open arrowheads and arrows.

-   Added Kievan half note on space, and Kievan beam.

-   Added new percussion pictograms from the books by Sevsay and
    Peinkofer/Tannigel, plus new combining glyphs for stems showing the
    “crush” rudiment, “dead” notes, and to instruct the performer to
    turn the instrument.

-   Added five further mensural proportion signs, from Apel’s book.

-   Added 12 new pre-composed trills and mordents, based on Bach’s
    ornamentation chart and ornaments found in the Emmentaler font.

-   Added restHBarMiddle glyph, for text-based applications to construct
    H-bar multirests of variable width.

-   Added noteheadWholeFilled and noteheadHalfFilled, for modern
    transcriptions of coloration in Medieval and Renaissance music.

-   Consolidated breath marks into a single range, and added a new
    upbow-like breath mark (as used in music from Russia).

-   Added range of glyphs for lyrics, including three lengths of elision
    undertie, and baseline hyphen (as used in music from Russia).

-   Added a wider slash notehead, for whole note (semibreve) duration.

-   Added more shape note noteheads to support the 7-shape conventions
    of Joseph Funk and William Walker.

-   Added maxima rest, and double whole (breve) rest with leger lines
    above and below.

-   Added curved caesura.

-   Added separate glyphs for the ‘e’, ‘d’ and dot in keyboard pedal
    marks, plus a curved hyphen to be used along with the ‘P’ to show
    start/end pedal in some editions.

-   Added new mensural C clef, plus variations of the Petrucci C clef
    for different staff positions.

-   Added different custos for different staff positions.

-   Added stylistic alternates for the Medieval and Renaissance “soft b”
    flat accidental.

-   Added dedicated glyphs for C, G, and F clef changes, plus new
    combining clef change character to produce other clef change glyphs
    by way of glyph substitution.

-   Added one- and two-third tones sharp and flat accidentals as used by
    Brian Ferneyhough.

-   Added “just air” open diamond notehead as used by Brian Ferneyhough.

-   Added white and wide white diamond noteheads.

-   Added a range of glyphs for denoting accel./rit. beam lines above
    the staff.

-   Added normal, wide and narrow leger line glyphs.

Version 0.85 (2014-03-09):

-   Updated glyph registration guidelines for articulations, such that
    articulations above the note should be positioned sitting on the
    baseline, and articulations below the note should be positioned
    hanging from the baseline.

-   Quite a few changes to canonical glyph names, especially for
    accidentals, with the aim of making the names clarify the actual
    interval represented by each accidental (where that is unambiguous)
    in terms of fractions of a tone.

-   Added whole and half rests with leger lines, i.e. as if displayed
    outside the staff.

-   Added clef for diatonic accordion.

-   Added recommended stylistic alternates for C and F clef forms used
    in 18th century French music, and for an F clef form used in 19th
    century music across Europe.

-   Added recommended ligature for G clef with ligated 8 above.

-   Added half-brackets for keyboard notation to show notes that should
    be played by the other hand.

-   Moved staff divide arrows from the **Miscellaneous symbols** range
    to the (now renamed) **Staff brackets and dividers** range.

-   Moved the percussion swish arrow from the **Miscellaneous symbols**
    range to the **Percussion playing techniques pictograms** range.

-   Moved all the glyphs from the **Quartertone accidentals (24-EDO)**
    range to the (now renamed) **Other accidentals** range, eliminating
    the former range and moving the latter to the very end of all of the
    ranges of accidentals.

-   Further revisions to the plainchant ranges, including adding
    reversed *virga*, smaller version of *punctum inclinatum*, moving
    the *punctum mora* to the plainchant articulations range, and
    eliminating the precomposed *podatus* and *clivis* glyphs in favour
    of individual components that provide the means to construct these
    easily for any interval. Also added *strophicus*, *strophicus
    auctus*, *punctum inclinatum auctum* to the single-note forms range.

-   Added new range for Kievan square notation, as used for liturgical
    chant in the Russian Orthodox Church.

-   Added new glyphs for tabling one handbell and tabling a pair
    of handbells.

-   Added alternative pedal heel glyph and pedal heel or toe glyph to
    **Keyboard techniques** range.

-   Added recommended stylistic alternates for braces designed for use
    across different sizes of gaps, designed to be scaled uniformly
    rather than simply stretched vertically.

-   Added many new electronic music pictograms, including speaker
    configurations, more transport controls, additional hardware
    devices, and so on.

-   Added guitar fade in, fade out and swell glyphs.

-   Added the glyphs used in the Corpus Monodicum project to the
    **Medieval and Renaissance plainchant in CMN** range.

-   Added notes on the currently-defined classes in the JSON metadata
    file to the **Notes for implementers** section.

Version 0.8 (2014-02-03):

-   Based on community feedback, added clarification that code points
    for glyphs may change until SMuFL reaches version 1.0, after which
    point existing code points will become immutable.

-   Glyphs in SMuFL encoded in the primary range of U+E000–U+F3FF are no
    longer considered “mandatory”, but rather they are “recommended”: in
    order to be considered SMuFL-compliant, a font need not implement
    every recommended glyph, just as a text font need not implement
    every Unicode code point in order to be
    considered Unicode-compliant. Fonts need only implement those glyphs
    that are appropriate for their intended use at the correct SMuFL
    code points in order to be considered SMuFL-compliant.

-   Changed guidelines for metrics of text-like glyphs (e.g.
    dynamics, D.C./D.S. markings in repeats) in fonts intended for use
    in scoring applications, such that it is recommended that the
    x-height of such glyphs is around 1 staff space (0.25 em).

-   Added Ivan Wyschnegradsky’s system of 72-EDO accidentals.

-   Added Bosanquet’s comma up/down.

-   Dispersed the glyphs formerly in the Sagittal-compatible accidentals
    range to other ranges, and revised the canonical glyph names for
    Sagittal accidentals that describe specific ratios in order to make
    those ratios clearer.

-   Added slashed sharp/flat accidentals used by John Tavener in his
    Byzantine-inspired choral works.

-   Added left/right parentheses for accidentals.

-   Added new ranges for Renaissance lute tablature, covering
    French/English, Italian/Spanish and German conventions.

-   Added new ranges for fingering charts for flute, oboe, clarinet,
    bassoon, saxophone and recorder, as used in educational materials
    such as instructional or method books.

-   Added Britten’s curlew sign for a pause of an indeterminate length.

-   Added push/pull signs for accordion.

-   Added separate noteheads for white mensural notation.

-   Added inverted signum congruentiae.

-   Added combined tenuto-accent articulation.

-   Added quasi-random wiggly lines (wiggleRandom1, wiggleRandom2,
    wiggleRandom3, wiggleRandom4) to multi-segment lines range.

-   Added flipped and large versions of constant circular motion
    (wiggleCircularConstantFlipped,
    wiggleCircularConstantLarge, wiggleCircularConstantFlippedLarge) to
    multi-segment lines range.

-   Added combining top/middle/bottom segments for black and white
    rectangular note clusters.

-   Added 2, 3, 4 and 6-dot divisi indicators for measured tremolos
    (tremoloDivisiDots2, tremoloDivisiDots3, etc.) to tremolos range.

-   Added clavichord bebung glyphs for 2, 3, and 4 finger movements
    (keyboardBebung2DotsAbove, keyboardBebung3DotsBelow, etc.) to the
    keyboard techniques range.

-   Added double-height parentheses and brackets (csymParensLeftTall,
    csymParensRightTall, csymBracketLeftTall, csymBracketRightTall) to
    the chord symbols range.

-   Added recommendation for stylistic alternates for time signature
    digits 0–9 suitable for use as large time signatures shown
    above/between staves (timeSig0Large through timeSig9Large).

-   Added *sfzp* (sforzato-piano) dynamic and ligature.

-   Added Penderecki’s quarter-flat and Bussotti’s three-quarter
    sharp accidentals.

-   Added six further accordion coupler diagrams for right-hand
    three-rank accordions, and accordion ricochet glyphs.

Version 0.7 (2013-11-27):

-   Introduced canonical names for every recommended glyph, which are
    intended to be immutable. Code points, on the other hand, may change
    as required to accommodate insertions or deletions of glyphs.

-   New **Notes for implementers** section with expanded guidelines for
    glyph registration, with changes for precomposed stems and stem
    decorations (which should now be centered around x=0) and flags
    (which should be positioned vertically relative to the end of a stem
    of normal length at y=0).

-   Added specification for JSON metadata files for SMuFL and for
    SMuFL-compliant fonts, developed in conjunction with Joe Berkovitz.

-   Significantly expanded the repertoire of glyphs for Medieval and
    Renaissance notation, with new ranges for clefs, accidentals and
    ligatures, plus considerable reworking of the notes and prolations
    ranges, expansion of the repertoire of glyphs for plainchant
    notation (with new ranges for staves, divisions, clefs and
    articulations, and a wider range of neumes).

-   Added range for Daseian notation, as found in the ninth century
    treatises *Musica enchiriadis* and *Scolica enchiriadis*.

-   Added new range of control characters for adjusting the staff
    position of staff-relative glyphs, intended for fonts designed for
    text-based applications.

-   Added narrow and wide staff line glyphs, intended for fonts designed
    for text-based applications.

-   Added C clef *ottava bassa*, and recommended stylistic alternate for
    G clef *ottava bassa* with parentheses around the 8.

-   Added control characters for time signature digits to allow digits
    to be stacked vertically, intended for fonts designed for
    text-based applications.

-   Added square double whole note (breve) notehead.

-   Added new combining harp string noise for stem glyph, and
    corresponding precomposed stem glyph.

-   Added four further quarter-tone accidental symbols to “other
    microtonal accidentals” group.

-   Added some percussion playing technique symbols from Dante
    Agostini’s method books.

-   Added a *golpe* (tap the pick guard) glyph from Claude Worm’s
    flamenco guitar method book.

-   Added short and long fermata glyphs as used by Henze.

-   Added combining glyphs for accordion couplers, allowing the creation
    of any coupler diagram not explicitly encoded.

-   Added “pf” dynamic.

Version 0.6 (2013-07-29):

-   Added opening parenthesis and closing parenthesis for noteheads,
    circled slash notehead, heavy X and heavy X with hat noteheads, as
    used in Dante Agostini’s drum method.

-   Added muted slash noteheads.

-   Added “si” note name noteheads for French solfège, and H sharp note
    name noteheads for German.

-   Added combining rim shot stem.

-   Added “sharp sharp” accidental for compatibility with MusicXML.

-   Added extended Stein-Zimmermann accidentals with arrows.

-   Added one-third-tone sharp and two-third-tones sharp accidentals as
    used by Xenakis.

-   Significant revision to the ornaments range, including splitting
    into separate ranges (common ornaments, other baroque ornaments,
    combining strokes for trills/mordents, precomposed trills/mordents).
    A small number of glyphs from previous versions of SMuFL have been
    removed to make way for symbols drawn from Frederick Neumann’s
    authoritative book on baroque ornamentation.

-   Added left hand pizzicato.

-   Added recommended stylistic alternates for Bartok
    pizzicato above/below.

-   Added recommended stylistic alternates for ‘Ped.’ and ‘Sost.’ that do
    not include terminal dots.

-   Added choke cymbal glyph from Weinberg.

-   Added open, half-open and closed wah/volume pedals, left- and
    right-hand tapping glyphs for guitar.

-   Added new range for arrows and arrowheads, including moving the
    up/down/right/left arrows from the vocal techniques into this
    new range.

Version 0.5 (2013-07-08):

-   Many existing code points have been changed, as a result of hundreds
    of new glyphs being added, plus a number of new ranges.

-   Added long and very long system dividers for very large scores.

-   Added heavy, double heavy and dotted barlines.

-   Added square coda and small repeat signs for repeats within bars.

-   Added recommended stylistic alternates for segno and coda for the
    appearance preferred by Japanese publishers.

-   Added quindicesima bassa G clef and F clef, G clef combined with C
    clef, G clefs designed to be ligated with numbers below and above to
    show the transposition of an instrument, plus recommended ligatures
    for G and F clefs with numbers above and below; also added G, C and
    F clefs with arrows up and down, which may be used either as
    alternatives for octave clefs or to represent the extremes of
    register on an instrument, and semi-pitched percussion clefs, plus a
    bridge clef.

-   Removed “tall” versions of 6- and 4-string tab clefs, and instead
    made them recommended stylistic alternates, together with versions
    that use letterforms with serifs.

-   Added +, -, X (multiply), comma, parentheses glyphs for time
    signatures, plus basic fractions, and Penderecki-style open
    time signature.

-   Added specific noteheads for double whole note and whole note to the
    noteheads range rather than relying on the glyphs in the
    pre-composed notes range.

-   Added shaped noteheads for specific note values (double whole note,
    whole note, half note, and quarter note and shorter); also added
    large up- and down-pointing triangles for highest/lowest notes
    played by an instrument.

-   Added large slashed circular noteheads as used by Stockhausen for
    notating gong/tam-tam hits.

-   Added combining glyphs for note clusters of specific note values.

-   Added noteheads with *solfège* and chromatic note names embedded
    within them, as seen in “EZ-Play” educational scores.

-   Added specific range of noteheads for sacred harp shape
    note singing.

-   Added pre-composed 1024th notes, tails and rest.

-   Added range for typing simple beamed groups of notes in text-based
    applications, designed to be used in conjunction with pre-composed
    notes, and allowing beamed groups with rhythmic values between 8th
    notes and 64th notes, plus ties and triplets.

-   Added combining stems for multiphonics, damp, sussurando, Saunders
    vibrato pulse accent.

-   Added four- and five-stroke tremolos plus Wieniawski-style
    unmeasured tremolo glyphs.

-   Added stylistic alternates for flags: straight flags; and shorter
    stem-up flags to avoid collisions with augmentation dots.

-   Separated accidentals into several discrete ranges based around the
    various accidental systems, including 12-EDO, 24-EDO, the system of
    up- and down-pointing arrows favoured by Gould, Stein-Zimmermann
    (also known as Tartini-Couper), Sims (also known as Maneri-Sims, due
    to the adoption of Ezra Sims’ accidentals by Joe Maneri of the
    Boston Microtonal Society), Ben Johnston, Marc Sabat and Wolfgang
    von Schweinitz’s Extended Helmholtz-Ellis Just Intonation
    Pitch Notation.

-   Added George Secor and Dave Keenan’s Sagittal system of accidentals.

-   Added accidentals used in Turkish folk music.

-   Added Persian accidentals.

-   Added staccatissimo wedge and stroke glyphs.

-   Added very short and very long fermatas, plus short caesura.

-   Added left and right halves of multirest H-bars and old-style
    quarter rest as seen in e.g. Novello editions.

-   Added *ventiduesima* (three octaves, “22”) glyphs to octaves range.

-   Added precomposed glyphs for common dynamics and *niente* circle
    for hairpins.

-   Added *schleifer* (long mordent) and Haydn ornament.

-   Added additional brass techniques, including short, medium and long
    versions of lift, doit, lip fall, smooth fall, rough fall, plus
    jazz turn.

-   Added range of glyphs for embouchure tightness, reed position,
    multiphonics, and stylistic alternates for double- and
    triple-tonguing with no slurs.

-   Added further overpressure glyphs, plus *jété*, *fouetté*, Rebecca
    Saunders’s “vibrato pulse” accent, thumb position and indeterminate
    bow direction to string techniques range.

-   Added plectrum pictogram and combining damp glyph for note stems to
    plucked techniques range.

-   Added arrows for breathing and intonation, plus combining
    *sussurando* glyph for note stems, to vocal techniques range.

-   Added pedal pictograms, *sostenuto* pedal symbols, and half-pedal
    marks to keyboard techniques range.

-   Added pictograms for metal rod and tuning key to harp
    techniques range.

-   Added Smith Brindle’s pictograms for tuned percussion instruments.

-   Added pictogram for Indian table, plus stylistic alternate for
    tambourine as used by Stockhausen.

-   Added pictogram for football rattle, plus Smith Brindle’s pictogram
    for castanets as a stylistic alternate.

-   Added pictogram for handbell, plus stylistic alternates for cow bell
    (from Berio) and sleigh bell (from Smith Brindle).

-   Added pictogram for Chinese cymbal.

-   Added pictogram for tam-tam with beater from Smith Brindle.

-   Added pictogram for maracas, rainstick, plus stylistic alternate for
    maraca from Smith Brindle.

-   Added pictogram for megaphone.

-   Added soft and hard glockenspiel beaters, superball beaters, wound
    beaters with hard and soft cores, plus soft, medium and hard
    gum beaters.

-   Added pluck lift to handbells range.

-   Added “Theme” indicators to analytics range.

-   Added minor (minus sign) glyph to chord symbols range.

-   Added mensural proportion glyphs.

-   Added combining raise and lower glyphs to figured bass range.

-   Added repetition, angle brackets, and prefix + and ring glyphs to
    Function theory range.

-   Added new range for multi-segment lines, including moving all of the
    various “wiggle” glyphs (for trill, glissando, arpeggiando,
    vibrato, etc.) plus the 11 ornament strokes from the Unicode Musical
    Symbols range into this range, and adding further glyphs for
    variable speed trills, alternate arpeggiato ending glyphs, wavy
    lines, squaretooth and sawtooth lines, group glissando, circular
    motion, and variable speed and intensity of vibrato.

-   Added new range of pictograms for electronic music, including
    microphone, loudspeaker, transport controls, volume level and MIDI
    controller level.

-   Added new “do not copy” glyphs, eyeglasses and choral divide arrows
    glyphs to the miscellaneous symbols range.

-   Adjusted the registration of many glyphs (e.g. noteheads,
    accidentals, time signatures, flags, rests) in Bravura in line with
    the interim guidelines for metrics and registration for
    SMuFL-compliant fonts intended for use with scoring applications.

Version 0.4 (2013-05-16):

-   Added range for Arel-Ezgi-Uzdilek (AEU) accidentals for Turkish
    maqam music.

-   Added equals sign and open time signature glyphs.

Version 0.3 (2013-03-11):

-   Moved combining flags glyphs to accommodate glyphs for 256th note
    stem up, 256th note stem down, 512th note stem up and 512th note
    stem down.

Version 0.2 (2013-02-08)

-   Added tick barline.

-   Changed names of time signature, tuplet and figured bass digit
    glyphs to ensure that they are unique.

-   Add upside-down and reversed G, F and C clefs for cancrizans and
    inverted canons.

-   Added Time signature + and Time signature fraction slash glyphs.

-   Added Black diamond notehead, White diamond notehead, Half-filled
    diamond notehead, Black circled notehead, White circled
    notehead glyphs.

-   Added 256th and 512th note glyphs.

-   All symbols shown on combining stems now also exist as
    separate symbols.

-   Added reversed sharp, natural, double flat and inverted flat and
    double flat glyphs for cancrizans and inverted canons.

-   Added trill wiggle segment, glissando wiggle segment and arpeggiato
    wiggle segment glyphs.

-   Added string Half-harmonic, Overpressure down bow and Overpressure
    up bow glyphs.

-   Added Breath mark glyph.

-   Added angled beater pictograms for xylophone, timpani and
    yarn beaters.

-   Added alternative glyph for Half-open, per Weinberg.

-   Added Scrape from rim to center and Scrape around rim glyphs.

-   Added Start of stimme glyph.

-   Added colon for tuplet ratios.

-   Added stem down versions of mensural notes, and signum congruentia
    and custos glyphs.

-   Added three additional mensuration signs.

-   Added Riemann Function theory glyphs.

Version 0.1 (2013-01-31)

-   Initial version.
