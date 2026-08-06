Implementations
---------------

The reference font for SMuFL is Bravura, which can be downloaded from [GitHub](https://github.com/steinbergmedia/bravura/releases).
Bravura is provided in OpenType, WOFF, WOFF2 and SVG formats, and is released under the
[SIL Open Font License](https://github.com/steinbergmedia/bravura/releases). The example glyphs
in this specification are all taken from Bravura.

This repository also automatically builds Bravura's OpenType font file, and its accompanying
font-specific metadata file, directly from the same sources as this specification, on every
change: [download Bravura.otf](media/Bravura.otf) / [download Bravura.json](media/Bravura.json).
This build tracks the specification exactly as it stands in this repository, including any
glyphs added since the last stable release — it is not a substitute for the stable release
linked above, which is signed off and versioned independently by Steinberg.

Other SMuFL-compliant fonts are available under a variety of licenses. A list
of such fonts can be found [here](http://www.smufl.org/fonts).

Support for SMuFL-compliant fonts has been implemented by a variety of
applications. A list of applications that support SMuFL can be found [here](http://www.smufl.org/software).
