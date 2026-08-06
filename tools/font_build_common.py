#!/usr/bin/env python3
"""Small helpers shared by tools/generate_font.py and
tools/generate_bravura_text.py that operate on the compiled OTF rather
than the UFO source - things with no UFO-level representation at all.
"""
from fontTools.ttLib import newTable


def add_dummy_dsig(ttfont):
    """Adds an empty (zero-signature) DSIG table, in place. This is the
    standard "dummy" DSIG some Windows/legacy consumers expect a font to
    have at all - it carries no actual signature data (SMuFL fonts aren't
    cryptographically signed), it's a completeness/compatibility marker,
    same as what FontLab wrote into the previous shipped builds."""
    dsig = newTable("DSIG")
    dsig.ulVersion = 1
    dsig.usNumSigs = 0
    dsig.usFlag = 1
    dsig.signatureRecords = []
    ttfont["DSIG"] = dsig
