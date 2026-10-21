#!/usr/bin/env python3
"""Board frame conversion: KiCad storage frame <-> design frame.

KiCad's Gerber/drill writers emit y-up artwork (they negate the y stored in
the .kicad_pcb).  The plate, case, points and specs are authored y-down
(design frame).  Until v0.4.0 the board was also stored in the design frame,
so every release artwork was the Y-mirror of the plate: the T12 centre holes
landed on the mirror of the plate cutouts and the T10 switch posts were
handed the wrong way (a standard Choc cannot install).

The fix is a full board-file reflection: store the board y-negated
(including footprint-local geometry and angles) so that KiCad's y-up export
reproduces the design frame.  This module is the single implementation of
that reflection, shared by the PCB generator, check_board and the plate /
case readers.  It is deliberately stdlib-only so the static CI gates can
use it without KiCad.

Frame marker
------------
The board title block carries ``(comment 3 "frame: design")`` or
``(comment 3 "frame: storage-yneg")``.  Readers call :func:`to_design` and
never have to guess.  A board with no marker (all releases before v0.4.0)
is treated as design frame, which keeps the historical artifacts readable.

The reflection is an involution: applying it twice returns the original
geometry.  Only coordinate/angle-bearing sexpr nodes are touched; sizes,
drills, layers, nets, text strings and UUIDs are unchanged.
"""
from decimal import Decimal
import re

STORAGE = "storage-yneg"
DESIGN = "design"
_MARK_RE = re.compile(r'\(comment 3 "[^"]*"\)')


def _neg(tok):
    """Negate a decimal token, preserving its precision; normalise -0."""
    d = -Decimal(tok)
    if d == 0:
        d = abs(d)
    return format(d, "f")


def _xy(m):
    return f"{m.group(1)}{m.group(2)} {_neg(m.group(3))}{m.group(4)}"


def _at(m):
    out = f"{m.group(1)}{m.group(2)} {_neg(m.group(3))}"
    if m.group(4) is not None:
        out += f" {_neg(m.group(4))}"
    return out + m.group(5)


def _offset(m):
    return (f"{m.group(1)}{m.group(2)} {_neg(m.group(3))} {m.group(4)}"
            f"{m.group(5)}")


# Headed coordinate nodes.  The patterns are anchored on the sexpr keyword
# so a size/drill/thickness pair can never be mistaken for geometry.
_AT_RE = re.compile(r'(\(at )([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?(\))')
_XY_NODE_RE = re.compile(
    r'(\((?:start|end|mid|center) )([-\d.]+) ([-\d.]+)(\))')
_XY_RE = re.compile(r'(\(xy )([-\d.]+) ([-\d.]+)(\))')
# 3D-model placement offset.  The model body itself cannot be reflected by
# a rotation, but placing the model's origin on the reflected footprint
# keeps the preview sane; every vendored override has zero model rotation.
_OFFSET_RE = re.compile(
    r'(\(offset\s*\(xyz )([-\d.]+) ([-\d.]+) ([-\d.]+)(\)\))')


def frame_of(text):
    """'storage-yneg' when the board carries the storage marker, else 'design'."""
    m = _MARK_RE.search(text)
    if m and STORAGE in m.group(0):
        return STORAGE
    return DESIGN


def set_frame(text, frame):
    """Return text with the title-block frame marker set to ``frame``."""
    marker = f'(comment 3 "frame: {frame}")'
    if _MARK_RE.search(text):
        return _MARK_RE.sub(marker, text, count=1)
    # title_block comments are indented with two tabs in KiCad's writer
    for anchor in (r'(\t\t\(comment 2 "[^"]*"\)\n)',
                   r'(\t\t\(rev "[^"]*"\)\n)',
                   r'(\t\t\(title "[^"]*"\)\n)'):
        m = re.search(anchor, text)
        if m:
            return text[:m.end()] + f"\t\t{marker}\n" + text[m.end():]
    raise AssertionError("board has no title_block anchor for the frame marker")


def mirror_geometry(text):
    """Reflect all geometry in y (and negate rotations).  Marker untouched."""
    text = _AT_RE.sub(_at, text)
    text = _XY_NODE_RE.sub(_xy, text)
    text = _XY_RE.sub(_xy, text)
    text = _OFFSET_RE.sub(_offset, text)
    return text


def to_storage(text):
    """Design-frame board text -> y-negated storage frame (idempotent)."""
    if frame_of(text) == STORAGE:
        return text
    return set_frame(mirror_geometry(text), STORAGE)


def to_design(text):
    """Storage-frame board text -> design frame (idempotent)."""
    if frame_of(text) == DESIGN:
        return set_frame(text, DESIGN)
    return set_frame(mirror_geometry(text), DESIGN)


def read_design(path):
    """Read a .kicad_pcb path and return design-frame text."""
    with open(path, encoding="utf-8") as f:
        return to_design(f.read())


def selftest():
    """Involution + known-coordinate checks; returns a list of failures."""
    bad = []
    src = ('(kicad_pcb\n\t(title_block\n\t\t(title "t")\n'
           '\t\t(comment 1 "x")\n\t\t(comment 2 "y")\n\t)\n'
           '\t(gr_line (start 1.5 -2.25) (end -3 4) (layer "Edge.Cuts"))\n'
           '\t(footprint "F" (layer "F.Cu") (uuid "u")\n'
           '\t\t(at 100 -27.7 27.5)\n'
           '\t\t(pad "" np_thru_hole circle (at 0 -5.9)\n'
           '\t\t\t(size 3.05 3.05) (drill 3.05))\n'
           '\t\t(model "m" (offset (xyz 0 5 0)) (rotate (xyz 0 0 0)))\n'
           '\t)\n\t(segment (start 1 2) (end 3 4) (width 0.2) (layer "F.Cu"))\n'
           '\t(via (at 5 -6) (size 0.65) (drill 0.3))\n'
           '\t(gr_circle (center 7 -8) (end 8 -8) (layer "Cmts.User"))\n'
           '\t(gr_text "t" (at 9 -10 0) (layer "F.SilkS"))\n)\n')
    st = to_storage(src)
    if 'frame: storage-yneg' not in st:
        bad.append("storage marker missing")
    if '(at 100 27.7 -27.5)' not in st and '(at 100.0 27.7 -27.5)' not in st:
        bad.append("placement was not reflected")
    if '(at 0 5.9)' not in st:
        bad.append("footprint-local pad was not reflected")
    if '(start 1.5 2.25)' not in st:
        bad.append("outline start was not reflected")
    if '(offset (xyz 0 -5 0))' not in st:
        bad.append("model offset was not reflected")
    if '(via (at 5 6)' not in st:
        bad.append("via was not reflected")
    if to_design(st) != set_frame(src, DESIGN):
        bad.append("to_design(to_storage(src)) is not the design text")
    if to_storage(st) != st:
        bad.append("to_storage is not idempotent")
    if to_design(set_frame(src, DESIGN)) != set_frame(src, DESIGN):
        bad.append("to_design is not idempotent")
    return bad


if __name__ == "__main__":
    import sys
    fails = selftest()
    for f in fails:
        print(f"  !! {f}")
    print("frame: CLEAN" if not fails else "frame: FAILING")
    sys.exit(1 if fails else 0)
