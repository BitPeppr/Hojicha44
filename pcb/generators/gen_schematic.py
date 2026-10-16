#!/usr/bin/env python3
"""Hojicha44 schematic generator — source of truth for pcb/kicad/*.kicad_sch.

Never hand-edit the .kicad_sch (GUI review is fine); change spec/electronics.yaml
or this script and regenerate:

  python3 pcb/generators/gen_schematic.py        # check + build both + ERC

Two sheets, one per half: Hojicha44-Left / Hojicha44-Right, each its own
KiCad project (hence its own .kicad_pcb — a split keyboard is two PCBs).
Halves are electrically identical except the TRRS crossover (straight cable,
TX/RX swap at the right MCU). Each sheet carries its own GND and its own
TRRS_T / TRRS_R1 (2 nodes each: this half's jack + the crossed MCU pin);
the cable joins the sheets. Anything NOT per-half-pair must stay that way —
in particular the battery rails: VBAT_SW_L and VBAT_SW_R are separate,
because PJ-320A ring2 is deliberately no-connected (see the TRRS block in
build_half). Wiring ring2 would join both LiPos through the cable into the
charger MOSFETs and damage the boards, so there is no VBAT_SHARED net.

Matrix per half: 4 rows x 6 cols, COL2ROW (col -> switch -> diode A -> diode K
-> row). R0-R2 x C0-C5 fingers, R3 x C0-C3 thumbs, R3C4-C5 unplaced spares.
Encoder push is a dedicated GPIO (D16), not matrix.
"""
import os
import re
import shutil
import subprocess
import sys
import uuid

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SPEC = os.path.join(REPO, "spec", "electronics.yaml")
PCB_DIR = os.path.join(REPO, "pcb", "kicad")
SYM_LIB = os.path.join(PCB_DIR, "Hojicha44.kicad_sym")
SYM_TABLE = os.path.join(PCB_DIR, "sym-lib-table")

# One KiCad project per half, so each half gets its own board file: a split
# keyboard is two separate PCBs, not one. Kept in one directory so both
# projects share the vendored symbol/footprint libraries.
PROJECT = {"L": "Hojicha44-Left", "R": "Hojicha44-Right"}
HALVES = ("L", "R")


def sch_path(tag):
    return os.path.join(PCB_DIR, PROJECT[tag] + ".kicad_sch")


def pro_path(tag):
    return os.path.join(PCB_DIR, PROJECT[tag] + ".kicad_pro")

KICAD_CLI = (
    shutil.which("kicad-cli")
    or "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
)
STOCK_SYM = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols"
STOCK_FP = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"

# Project-local 2x12 socket for the nice!nano. Stock
# Connector_PinSocket_2.54mm:PinSocket_2x12_P2.54mm_Vertical numbers pads
# ROW-major (serpentine: 1 top-right, 2 top-left, 3 row-2-right ...) with
# 2.54mm row spacing, while the nice_nano symbol follows the PRO MICRO /
# nice!nano naming with 15.24mm row separation. Netlists connect by pin
# number, so the stock part would land every net on the wrong physical pad
# (RAW on GND, ...) and neither ERC nor DRC could catch it — and the module
# physically cannot fit (rows 12.7mm too narrow).
# This footprint numbers pads so that 1-12 run down the TX/D1 edge (x=0) and
# 13-24 down the RAW edge (x=-15.24) in OPPOSITE directions, i.e. pads 1 (D1)
# and 24 (RAW) share the USB end (y=0), pads 12 (D9) and 13 (D10) share the
# antenna end (y=27.94) — the same pairing as keebio's ArduinoProMicro
# footprint (15.24mm row separation) and ProMicro symbol.
# check_mcu_footprint() enforces pitch, separation, numbering, and envelope.
MCU_FP_NAME = "Socket_Strips_2x12_P2.54mm_NiceNano"
MCU_FOOTPRINT = f"Hojicha44:{MCU_FP_NAME}"
MCU_FP_FILE = os.path.join(REPO, "pcb", "kicad", "Hojicha44.pretty",
                           MCU_FP_NAME + ".kicad_mod")

# Title-block revision, derived from spec version in load_spec() so the sheet
# can never drift from spec/electronics.yaml again.
REV = "0.0"

# lib file, symbol name, pins we require (numbers)
NEED = [
    ("Switch.kicad_sym", "SW_Push", ["1", "2"]),
    ("Switch.kicad_sym", "SW_SPDT", ["1", "2", "3"]),
    ("Diode.kicad_sym", "1N4001", ["1", "2"]),
    ("Device.kicad_sym", "RotaryEncoder_Switch", ["A", "B", "C", "S1", "S2"]),
    ("Connector_Audio.kicad_sym", "AudioJack4", ["T", "R1", "R2", "S"]),
    ("Connector.kicad_sym", "Conn_01x02_Socket", ["1", "2"]),
    ("power.kicad_sym", "GND", ["1"]),
    ("power.kicad_sym", "VCC", ["1"]),
    ("power.kicad_sym", "PWR_FLAG", ["1"]),
]

LIB_IDS = {
    "SW_Push": "Switch:SW_Push",
    "SW_SPDT": "Switch:SW_SPDT",
    "1N4001": "Diode:1N4001",
    "RotaryEncoder_Switch": "Device:RotaryEncoder_Switch",
    "AudioJack4": "Connector_Audio:AudioJack4",
    "Conn_01x02_Socket": "Connector:Conn_01x02_Socket",
    "GND": "power:GND",
    "VCC": "power:VCC",
    "PWR_FLAG": "power:PWR_FLAG",
}

# nice!nano: 24 footprint pins, unique numbers; names = Arduino silkscreen.
# (Battery goes to RAW/GND per official docs — RAW is B+ equivalent.)
# PRO MICRO / nice!nano pin-numbering convention (keebio's ProMicro symbol +
# ArduinoProMicro.kicad_mod, and the nice!nano v2 silkscreen):
#   pads 1-12 run down the TX/D1 edge, pads 13-24 run down the RAW edge in the
#   opposite direction, so pads 1 (D1) and 24 (RAW) share the USB end while
#   pads 12 (D9) and 13 (D10) share the antenna end.
# The stock PinSocket_2x12 numbers row-major (1,2 / 3,4 ...), which puts pads
# 1 and 13 at the same end and silently scrambles every MCU net — hence the
# project-local Socket_Strips_2x12_P2.54mm_NiceNano footprint.
# left column top->bottom, right column top->bottom.
MCU_LEFT = [("1", "D1"), ("2", "D0"), ("3", "GND"), ("4", "GND"),
            ("5", "D2"), ("6", "D3"), ("7", "D4"), ("8", "D5"),
            ("9", "D6"), ("10", "D7"), ("11", "D8"), ("12", "D9")]
MCU_RIGHT = [("13", "D10"), ("14", "D16"), ("15", "D14"), ("16", "D15"),
             ("17", "A0"), ("18", "A1"), ("19", "A2"), ("20", "A3"),
             ("21", "VCC"), ("22", "RST"), ("23", "GND"), ("24", "RAW")]

# net per pin number. Right half: same except D1/D0 swapped (straight TRRS
# cable: T carries left-TX, R1 carries right-TX).
NETS_L = {
    "1": "TRRS_T", "2": "TRRS_R1", "3": "GND", "4": "GND",
    "5": "COL2_L", "6": "COL3_L", "7": "ROW0_L", "8": "ROW1_L",
    "9": "ROW2_L", "10": "ROW3_L", "11": "COL0_L", "12": "COL1_L",
    "13": "D10_L", "14": "ENC_SW_L", "15": "COL4_L", "16": "COL5_L",
    "17": "ENC_A_L", "18": "ENC_B_L", "19": "A2_L", "20": "A3_L",
    "21": "VCC3V3_L", "22": "RST_L", "23": "GND", "24": "VBAT_SW_L",
}
NETS_R = {n: (v[:-2] + "_R" if v.endswith("_L") else v)
          for n, v in NETS_L.items()}
NETS_R["1"] = "TRRS_R1"   # right TX rides ring1 (straight cable crossover)
NETS_R["2"] = "TRRS_T"


# ---------------------------------------------------------------- helpers

def U():
    return str(uuid.uuid4())


def get_symbol(lib, name):
    with open(os.path.join(STOCK_SYM, lib), encoding="utf-8", errors="ignore") as f:
        s = f.read()
    i = s.find('(symbol "' + name + '"')
    if i < 0:
        raise ValueError(f"stock symbol missing: {lib}:{name}")
    depth, j = 0, i
    while j < len(s):
        if s[j] == "(":
            depth += 1
        elif s[j] == ")":
            depth -= 1
            if depth == 0:
                break
        j += 1
    return s[i:j + 1]


def pin_numbers(sym_block):
    return re.findall(r'\(number\s+"([^"]+)"', sym_block)


def load_lib():
    """Returns (lib_symbols_text, {name: [pin numbers]})."""
    blocks, pins = {}, {}
    nicks = {}
    for lib, name, want in NEED:
        nick = lib[:-len(".kicad_sym")]
        b = get_symbol(lib, name)
        got = pin_numbers(b)
        m = re.search(r'\(extends\s+"([^"]+)"', b[:300])
        if m:
            parent = m.group(1)
            if parent not in blocks:
                blocks[parent] = get_symbol(lib, parent)
                nicks[parent] = nick
            if not got:
                got = pin_numbers(blocks[parent])
        for w in want:
            assert w in got, f"{name}: pin {w} not in {got}"
        blocks[name] = b
        nicks[name] = nick
        pins[name] = got
    blocks["nice_nano"] = nice_nano_def()
    nicks["nice_nano"] = "Hojicha44"
    pins["nice_nano"] = [n for n, _ in MCU_LEFT + MCU_RIGHT]
    # prefix top-level names with lib nick so lib_id refs resolve.
    # extends targets and their parent blocks keep BARE names (renaming them
    # breaks parent resolution and trips lib_symbol_mismatch).
    parents = set()
    for b in blocks.values():
        m = re.search(r'\(extends\s+"([^":]+)"', b[:300])
        if m:
            parents.add(m.group(1))
    for name, nick in nicks.items():
        if ":" in name or name in parents:
            continue
        b = blocks[name]
        b = b.replace(f'(symbol "{name}"', f'(symbol "{nick}:{name}"', 1)
        blocks[name] = b
    # kicad-cli ERC only connects pins found in the unit-specific _1_1 child;
    # stock SW_Push / PWR_FLAG keep pins in _0_x, so duplicate that child.
    for name, want in (("SW_Push", 2), ("PWR_FLAG", 1)):
        blocks[name] = graft_unit1(blocks[name], name, want)
    offs = {name: pin_offsets(b) for name, b in blocks.items()}
    return blocks, pins, offs


def pin_offsets(sym_block):
    """{pin number: (dx, dy_file)} from _1_1 (else _0_x).

    NOTE: library Y is UP, schematic Y is DOWN — callers negate dy."""
    out = {}
    for child in ("_1_1", "_0_1", "_0_0"):
        for m in re.finditer(
                r"\(pin\s+\S+\s+line\s+\(at\s+([-\d.]+)\s+([-\d.]+)\s+\d+\)"
                r".*?\(number\s+\"([^\"]+)\"", sym_block, re.S):
            dx, dy, num = m.groups()
            out.setdefault(num, (float(dx), float(dy)))
        if out:
            break
    return out


def graft_unit1(block, name, npins):
    pin_texts = []
    for suffix in ("_0_0", "_0_1"):
        tag = f'(symbol "{name}{suffix}"'
        i = block.find(tag)
        if i < 0:
            continue
        depth, j = 0, i
        while True:
            if block[j] == "(":
                depth += 1
            elif block[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        child = block[i:j + 1]
        k = 0
        while True:
            p = child.find("(pin ", k)
            if p < 0:
                break
            d2, q = 0, p
            while True:
                if child[q] == "(":
                    d2 += 1
                elif child[q] == ")":
                    d2 -= 1
                    if d2 == 0:
                        break
                q += 1
            pin_texts.append(child[p:q + 1])
            k = q + 1
    assert len(pin_texts) == npins, \
        f"{name}: found {len(pin_texts)} pins, want {npins}"
    # NOTE: pins stay in _0_x AND the whole child is duplicated as
    # _1_1 (t4-proven; pins-only _1_1 does NOT connect under kicad-cli)
    ef = block.rfind("(embedded_fonts")
    assert ef > 0, f"{name}: no embedded_fonts marker"
    dups = ""
    for suffix in ("_0_0", "_0_1"):
        tag = f'(symbol "{name}{suffix}"'
        i = block.find(tag)
        if i < 0:
            continue
        depth, j = 0, i
        while True:
            if block[j] == "(":
                depth += 1
            elif block[j] == ")":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        child = block[i:j + 1]
        if "(pin " not in child:
            continue  # graphics-only child: leave as-is
        dups += child.replace(tag, f'(symbol "{name}_1_1"', 1) + "\n"
    assert dups, f"{name}: no pin-bearing _0_x child found"
    unit1 = "\t" + dups.replace("\n", "\n\t").rstrip() + "\n"
    return block[:ef] + unit1 + block[ef:]


def nice_nano_def():
    n = len(MCU_LEFT)
    top = 27.94  # 12 pins x 5.08 pitch
    lines = [
        '(symbol "Hojicha44:nice_nano"',
        '\t(pin_names (offset 1.016) (hide yes))',
        '\t(exclude_from_sim no) (in_bom yes) (on_board yes)',
        prop("Reference", "U", 0, top + 5.08),
        prop("Value", "nice_nano", 0, -(top + 5.08)),
        prop("Footprint", "", 0, -(top + 10.16), hide=True),
        prop("Datasheet", "https://nicekeyboards.com/docs/nice-nano/",
             0, -(top + 15.24), hide=True),
        '\t(symbol "nice_nano_0_1"',
        rect(-10.16, top + 2.54, 10.16, -(top + 2.54)),
        '\t)',
        '\t(symbol "nice_nano_1_1"',
    ]
    for i, (num, name) in enumerate(MCU_LEFT):
        y = round(top - i * 5.08, 2)
        lines.append(pin_def(num, name, -12.7, y, 0, etype(name)))
    for i, (num, name) in enumerate(MCU_RIGHT):
        y = round(top - i * 5.08, 2)
        lines.append(pin_def(num, name, 12.7, y, 180, etype(name)))
    lines.append("\t)")
    lines.append(")")
    return "\n".join(lines)


def etype(name):
    if name == "GND" or name == "B-":
        return "power_in"
    if name == "VCC":
        return "power_out"
    return "bidirectional"


def pin_def(num, name, x, y, angle, etype):
    return (
        f'\t\t(pin {etype} line (at {x} {y} {angle}) (length 2.54)\n'
        f'\t\t\t(name "{name}" (effects (font (size 1.27 1.27))))\n'
        f'\t\t\t(number "{num}" (effects (font (size 1.27 1.27))))\n'
        "\t\t)"
    )


def rect(x1, y1, x2, y2):
    return (
        f'\t\t(rectangle (start {x1} {y1}) (end {x2} {y2})\n'
        '\t\t\t(stroke (width 0.254) (type default)) (fill (type background)))'
    )


def prop(name, value, x, y, hide=False):
    h = " (hide yes)" if hide else ""
    return (
        f'\t(property "{name}" "{value}" (at {x} {y} 0){h}\n'
        '\t\t(effects (font (size 1.27 1.27))))'
    )


# ---------------------------------------------------------------- schematic builder

class Sch:
    def __init__(self, project="Hojicha44"):
        self.lib = {}
        self.pins = {}
        self.offs = {}
        self.body = []
        self.refs = set()
        self.pwr = 0
        # Root-sheet uuid + project name for the per-symbol `instances`
        # blocks. Without them KiCad reports "schematic has annotation
        # errors" on every netlist/PCB export.
        self.project = project
        self.root = U()

    # Locked parts (spec/electronics.yaml). MPN exports into the BOM;
    # Datasheet holds a URL only where one is certain (controller docs).
    MPN = {"SW_Push": "Kailh PG1350",
           "1N4001": "1N4148W",
           "nice_nano": "nice!nano v2",
           "RotaryEncoder_Switch": "Alps EC11E15244G1",
           "AudioJack4": "XKB PJ-320A",
           "Conn_01x02_Socket": "JST S2B-PH-K-S",
           "SW_SPDT": "Wuerth 450301014042"}
    DATASHEET = {"nice_nano": "https://nicekeyboards.com/docs/nice-nano/"}

    def place(self, sym, ref, value, footprint, x, y, rot=0, props_at=None):
        assert ref not in self.refs, f"duplicate ref {ref}"
        # KiCad treats a reference that does not end in a digit as
        # un-annotated: every netlist/PCB export then warns "schematic has
        # annotation errors" even though ERC is clean. Catch it here.
        assert ref[0] == "#" or ref[-1].isdigit(), \
            f"refdes {ref!r} must end in a digit (KiCad annotation rule)"
        self.refs.add(ref)
        lib_id = LIB_IDS[sym] if sym != "nice_nano" else "Hojicha44:nice_nano"
        py = props_at if props_at is not None else y - 10
        L = [f'\t(symbol (lib_id "{lib_id}") (at {r2(x)} {r2(y)} {rot}) (unit 1)',
             "\t\t(in_bom yes) (on_board yes) (dnp no) (fields_autoplaced yes)",
             f'\t\t(uuid "{U()}")',
             prop("Reference", ref, r2(x), r2(py)),
             prop("Value", value, r2(x), r2(py - 4)),
             prop("Footprint", footprint, r2(x), r2(py - 8), hide=True),
             prop("Datasheet", self.DATASHEET.get(sym, ""), r2(x), r2(py - 12), hide=True),
             prop("MPN", self.MPN.get(sym, ""), r2(x), r2(py - 16), hide=True)]
        nums = self.pins[sym]
        for n in nums:
            L.append(f'\t\t(pin "{n}" (uuid "{U()}"))')
        L.append('\t\t(instances')
        L.append(f'\t\t\t(project "{self.project}"')
        L.append(f'\t\t\t\t(path "/{self.root}"')
        L.append(f'\t\t\t\t\t(reference "{ref}")')
        L.append('\t\t\t\t\t(unit 1)')
        L.append('\t\t\t\t)')
        L.append('\t\t\t)')
        L.append('\t\t)')
        L.append("\t)")
        self.body.append("\n".join(L))

    def wire(self, x1, y1, x2, y2):
        self.body.append(
            f'\t(wire (pts (xy {r2(x1)} {r2(y1)}) (xy {r2(x2)} {r2(y2)}))'
            f' (stroke (width 0) (type default)) (uuid "{U()}"))'
        )

    def junction(self, x, y):
        self.body.append(
            f'\t(junction (at {r2(x)} {r2(y)}) (diameter 0)'
            f' (color 0 0 0 0) (uuid "{U()}"))'
        )

    def label(self, text, x, y):
        self.body.append(
            f'\t(label "{text}" (at {r2(x)} {r2(y)} 0) (fields_autoplaced yes)'
            f' (uuid "{U()}") (effects (font (size 1.27 1.27)) (justify left)))'
        )

    def no_connect(self, x, y):
        self.body.append(
            f'\t(no_connect (at {r2(x)} {r2(y)}) (uuid "{U()}"))'
        )

    def tip(self, sym, x, y, num):
        """Pin-tip position for a symbol placed unrotated at (x, y).

        Library Y is UP, schematic Y is DOWN: dy is negated."""
        dx, dy = self.offs[sym][num]
        return (r2(x + dx), r2(y - dy))

    def gnd(self, x, y):
        self.pwr += 1
        self.place("GND", f"#PWR{self.pwr:03d}", "GND",
                   "", x, y, props_at=y + 6)

    def text(self, s, x, y, size=3.0):
        self.body.append(
            f'\t(text "{s}" (at {r2(x)} {r2(y)} 0) (uuid "{U()}")'
            f' (effects (font (size {size} {size}) bold) (justify left)))'
        )


def r2(v):
    return round(v, 2)


def build_half(s, tag, nets, ox):
    """One half at x-offset ox. Returns nothing; appends to Sch.

    All coordinates are multiples of 1.27mm (ERC connection grid) and every
    pin connection goes through Sch.tip() (library Y is UP, schematic Y DOWN).
    Matrix drawn at 19.05mm column spacing (15 x 1.27 grid units);
    measured physical MX column pitch is 19.00mm (schematic-only constant —
    PCB copper comes from ergogen, so P never feeds physical geometry).
    """
    P = 19.05
    STUB = 10.16  # label stubs (room for pin number + label side by side)
    oy = 120.65            # matrix top = 95 x 1.27
    oxm = ox + 38.1        # matrix left = 30 x 1.27
    s.text(f'{"LEFT" if tag == "L" else "RIGHT"} HALF — 22 keys + EC11',
           ox + 25.4, 292.1)  # bottom margin: top is crowded, bottom is free

    # --- MCU ---
    mx, my = ox + 86.36, 48.26  # 68 x, 38 x 1.27
    s.place("nice_nano", f"U_{tag}1", "nice!nano v2",
            MCU_FOOTPRINT,
            mx, my, props_at=my - 40.64)
    for cols, xoff in ((MCU_LEFT, -12.7), (MCU_RIGHT, 12.7)):
        for num, _name in cols:
            tx, ty = s.tip("nice_nano", mx, my, num)
            ex = mx + xoff - STUB if xoff < 0 else mx + xoff + STUB
            s.wire(tx, ty, ex, ty)
            s.label(nets[num], ex, ty)

    # --- matrix: 22 keys ---
    idx = 0
    for r in range(4):
        for c in range(6):
            if r == 3 and c >= 4:
                continue  # R3C4-C5 spares, unplaced
            kx, ky = r2(oxm + c * P), r2(oy + r * P)
            s.place("SW_Push", f"SW_{tag}{idx:02d}", f"K{idx:02d}",
                    "Hojicha44:SW_Hotswap_Kailh_Choc_V1_1.00u",
                    kx, ky, props_at=ky - 10.16)
            p1x, p1y = s.tip("SW_Push", kx, ky, "1")
            p2x, p2y = s.tip("SW_Push", kx, ky, "2")
            s.junction(p1x, p1y)  # meets column rail
            # diode sits BETWEEN this pin2 and the next column rail
            # (wire must not reach/cross it: next rail is +13.97 away)
            dix = r2(kx + 7.62)
            s.place("1N4001", f"D_{tag}{idx:02d}", "1N4148W",
                    "Diode_SMD:D_SOD-123", dix, ky, props_at=ky - 10.16)
            ax, ay = s.tip("1N4001", dix, ky, "2")   # anode <- switch
            kx2, ky2 = s.tip("1N4001", dix, ky, "1")  # cathode -> row
            s.wire(p2x, p2y, ax, ay)
            s.wire(kx2, ky2, kx2, ky2 + 6.35)
            s.junction(kx2, ky2 + 6.35)  # meets row rail
            idx += 1
    assert idx == 22, idx
    for c in range(6):  # column rails + labels
        cx = r2(oxm + c * P - 5.08)
        y0 = oy
        y3 = r2(oy + (2 if (c >= 4) else 3) * P)  # short rows have no R3 key
        s.wire(cx, y0, cx, y3)
        s.wire(cx, y0 - 6.35, cx, y0)
        s.junction(cx, y0)
        s.label(f"COL{c}_{tag}", cx, y0 - 6.35)
    for r in range(4):  # row rails + labels (labels live at the RIGHT end,
        # clear of the key reference texts that crowd the left end)
        ry = r2(oy + r * P + 6.35)
        last = 3 if r == 3 else 5  # R3 has no C4-C5 keys
        x1 = r2(oxm + 7.62 - 3.81)
        x2 = r2(oxm + last * P + 7.62 - 3.81)
        s.wire(x1, ry, x2, ry)  # stub to stub; ends sit on K junctions
        s.wire(x2, ry, x2, ry + 6.35)
        s.label(f"ROW{r}_{tag}", x2, ry + 6.35)

    # --- encoder (below matrix) ---
    ex, ey = ox + 63.5, r2(oy + 4 * P + 25.4)
    s.place("RotaryEncoder_Switch", f"ENC_{tag}1", "EC11E-Switch",
            "Rotary_Encoder:RotaryEncoder_Alps_EC11E-Switch_Vertical_H20mm_CircularMountingHoles",
            ex, ey, props_at=ey - 15.24)
    for num, net in (("A", f"ENC_A_{tag}"), ("B", f"ENC_B_{tag}")):
        tx, ty = s.tip("RotaryEncoder_Switch", ex, ey, num)
        s.wire(tx, ty, tx - STUB, ty)
        s.label(net, tx - STUB, ty)
    cx, cy = s.tip("RotaryEncoder_Switch", ex, ey, "C")
    # common GND rides a long stub west, clear of the A/B stubs + labels
    s.wire(cx, cy, cx - 15.24, cy)
    s.gnd(cx - 15.24, cy)
    sx1, sy1 = s.tip("RotaryEncoder_Switch", ex, ey, "S1")
    s.wire(sx1, sy1, sx1 + STUB, sy1)
    s.label(f"ENC_SW_{tag}", sx1 + STUB, sy1)
    sx2, sy2 = s.tip("RotaryEncoder_Switch", ex, ey, "S2")
    s.gnd(sx2, sy2)

    # --- TRRS ---
    jx, jy = ox + 139.7, r2(oy + 4 * P + 25.4)
    s.place("AudioJack4", f"J_{tag}1", "PJ-320A TRRS",
            "Hojicha44:TRRS-PJ-320A",
            jx, jy, props_at=jy - 15.24)
    # ring2 intentionally unconnected (leaving it wired would join both
    # batteries through the cable into the charger MOSFETs — board damage)
    for num, net in (("T", "TRRS_T"), ("R1", "TRRS_R1")):
        tx, ty = s.tip("AudioJack4", jx, jy, num)
        s.wire(tx, ty, tx + STUB, ty)
        s.label(net, tx + STUB, ty)
    rx, ry = s.tip("AudioJack4", jx, jy, "R2")
    s.no_connect(rx, ry)
    gx, gy = s.tip("AudioJack4", jx, jy, "S")
    # sleeve GND rides a long stub past the T/R1/R2 labels AND the long
    # VBAT_SHARED label, so its symbol texts stay clear of both
    s.wire(gx, gy, gx + 30.48, gy)
    s.gnd(gx + 30.48, gy)

    # --- battery + power switch (near MCU) ---
    # LiPo+ -> WS-SLTV pin 1 (middle = COMMON per Würth 450301014042
    # datasheet: front view labels 2-1-3, schematic marks 1 as COM) ->
    # pin 2 (throw) -> VBAT_SW -> MCU RAW. Pin 3 (other throw) NC.
    # Per nice!nano docs RAW is the B+ equivalent, GND the B- equivalent.
    # NOTE: generic SW_SPDT names these A/B/C with B on pin 2 — WRONG for
    # this part. Only pin NUMBERS matter: 1 = middle = common.
    bx, by = ox + 177.8, 48.26
    s.place("Conn_01x02_Socket", f"J_{tag}2", "BATT_LIPO",
            "Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal",
            bx, by, props_at=by - 12.7)
    j1x, j1y = s.tip("Conn_01x02_Socket", bx, by, "1")
    j2x, j2y = s.tip("Conn_01x02_Socket", bx, by, "2")
    s.wire(j2x, j2y, j2x - 5.08, j2y)
    s.label("GND", j2x - 5.08, j2y)
    sx, sy = ox + 177.8, 73.66
    s.place("SW_SPDT", f"SW_{tag}PWR1", "PWR_SW",
            "Button_Switch_THT:SW_Slide-03_Wuerth-WS-SLTV_10x2.5x6.4_P2.54mm",
            sx, sy, props_at=sy - 15.24)
    b1x, b1y = s.tip("SW_SPDT", sx, sy, "1")  # common (middle pin)
    a2x, a2y = s.tip("SW_SPDT", sx, sy, "2")  # throw -> rail
    c3x, c3y = s.tip("SW_SPDT", sx, sy, "3")  # unused throw
    # corner route: straight down would cross JST pin2's GND stub (short)
    cor = r2(j1x - 6.35)
    s.wire(j1x, j1y, cor, j1y)
    s.wire(cor, j1y, cor, b1y)
    s.wire(cor, b1y, b1x, b1y)
    s.junction(cor, j1y)
    s.junction(cor, b1y)
    s.wire(a2x, a2y, a2x + STUB, a2y)
    s.label(f"VBAT_SW_{tag}", a2x + STUB, a2y)
    s.no_connect(c3x, c3y)
    # PWR_FLAG drives the GND net (silences power-in-not-driven). Exactly one
    # per sheet: paralleled power-out flags trip pin_to_pin ERC. Each half is
    # its own project now, so each sheet carries its own flag.
    s.place("PWR_FLAG", "#FLG1", "PWR_FLAG", "", ox + 25.4, 241.3,
            props_at=231.14)  # ref above; label lives below the stub
    fx, fy = s.tip("PWR_FLAG", ox + 25.4, 241.3, "1")
    s.wire(fx, fy, fx, fy + STUB)
    s.label("GND", fx, fy + STUB)


def render(s):
    import datetime
    lib_lines = []
    for name, blk in s.lib.items():
        lib_lines.append(blk)
    lib_text = "\n".join(lib_lines)
    body = "\n".join(s.body)
    today = datetime.date.today().isoformat()
    return f"""(kicad_sch
\t(version 20250114)
\t(generator "eeschema")
\t(generator_version "10.0")
\t(uuid "{s.root}")
\t(paper "A2")
\t(title_block
\t\t(title "Hojicha44 {s.project}")
\t\t(date "{today}")
\t\t(rev "{REV}")
\t\t(company "BitPeppr")
\t)
\t(lib_symbols
{lib_text}
\t)
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
{body}
)
"""


# ---------------------------------------------------------------- spec check

def load_spec():
    with open(SPEC) as f:
        s = f.read()

    def num(key):
        m = re.search(rf"^\s*{key}:\s*(\d+)", s, re.M)
        if not m:
            raise ValueError(f"spec missing numeric key: {key}")
        return int(m.group(1))

    m = {"rows": num("rows"), "cols": num("cols"), "used": num("used")}
    assert m["rows"] * m["cols"] >= m["used"], "matrix too small"
    assert set(NETS_L) == {n for n, _ in MCU_LEFT + MCU_RIGHT}
    assert set(NETS_R) == set(NETS_L)
    v = re.search(r"^version:\s*(\d+)\.(\d+)(?:\.\d+)?", s, re.M)
    if not v:
        raise ValueError("spec missing version: expected MAJOR.MINOR.PATCH")
    global REV
    REV = f"{v.group(1)}.{v.group(2)}"
    print(f"matrix {m['rows']}x{m['cols']}, {m['used']} used, "
          f"{m['rows']*m['cols']-m['used']} spare; pin maps OK (24 each); "
          f"rev {REV}")
    return m


def audit(sch_path, offs, tag):
    """Independent net check: union-find over pin tips, wire ends and labels.

    Asserts every named net holds exactly its design pin count. Catches
    miswired-but-ERC-silent faults (e.g. mirrored pin order). `tag` is the
    half this sheet carries ("L" or "R").
    """
    s = open(sch_path).read()
    parent = {}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        parent.setdefault(a, a)
        parent.setdefault(b, b)
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    def pt(x, y):
        return (round(float(x), 2), round(float(y), 2))

    pin_at = []  # (ref, num, x, y)
    for m in re.finditer(
            r'\(symbol \(lib_id "([^"]+)"\) \(at ([-\d.]+) ([-\d.]+) (\d+)\)'
            r"(.*?)(?=\n\t\(symbol \(lib_id |\n\t\(wire |\n\t\(label |\n\t\(junction |\n\t\(no_connect |\n\t\(text |\n\)\s*$)",
            s, re.S):
        lib_id, x, y, rot, inner = m.groups()
        assert rot == "0", f"audit: rotation {rot} unsupported"
        short = lib_id.split(":")[-1]
        ref = re.search(r'\(property "Reference" "([^"]+)"', inner).group(1)
        key = short if short in offs else None
        assert key, f"audit: no offsets for {lib_id}"
        for pn in re.findall(r'\(pin "([^"]+)"', inner):
            dx, dy = offs[key][pn]
            pin_at.append((ref, pn, round(float(x) + dx, 2),
                           round(float(y) - dy, 2)))
    wires = re.findall(
        r"\(wire \(pts \(xy ([-\d.]+) ([-\d.]+)\) \(xy ([-\d.]+) ([-\d.]+)\)",
        s)
    labels = re.findall(r'\(label "([^"]+)" \(at ([-\d.]+) ([-\d.]+)', s)

    for ref, pn, x, y in pin_at:
        union(("pin", ref, pn), ("pt", x, y))
    segs = []
    for x1, y1, x2, y2 in wires:
        a, b = pt(x1, y1), pt(x2, y2)
        union(("pt",) + a, ("pt",) + b)
        segs.append((a, b))

    def on_seg(px, py, a, b):
        (x1, y1), (x2, y2) = a, b
        if x1 == x2 == px:
            return min(y1, y2) <= py <= max(y1, y2)
        if y1 == y2 == py:
            return min(x1, x2) <= px <= max(x1, x2)
        return False

    # T-joints: any endpoint touching a wire mid-segment joins it.
    # (Endpoints include pin tips, label anchors AND plain wire ends
    # such as K-stub bottoms landing on row rails.)
    touch_pts = {(x, y) for _, _, x, y in pin_at}
    touch_pts.update(pt(x, y) for _, x, y in labels)
    for x1, y1, x2, y2 in wires:
        touch_pts.add(pt(x1, y1))
        touch_pts.add(pt(x2, y2))
    for (px, py) in touch_pts:
        for a, b in segs:
            if on_seg(px, py, a, b):
                union(("pt", px, py), ("pt",) + a)
    by_text = {}
    for text, x, y in labels:
        union(("pt",) + pt(x, y), ("lab", text))
        by_text.setdefault(text, []).append((x, y))

    # power symbols name their net implicitly (no text label needed)
    for m in re.finditer(
            r'\(symbol \(lib_id "(power:[^"]+)"\) \(at ([-\d.]+) ([-\d.]+)',
            s):
        lib_id = m.group(1)
        # find instance ref + value after this position
        tail = s[m.start():m.start() + 2000]
        ref = re.search(r'\(property "Reference" "([^"]+)"', tail).group(1)
        val = re.search(r'\(property "Value" "([^"]+)"', tail).group(1)
        for (rr, pn, x, y) in pin_at:
            if rr == ref:
                union(("pin", rr, pn), ("lab", val))
    # no-connect markers: those pins must stand alone (exempt from labels)
    ncs = set()
    for m in re.finditer(r"\(no_connect \(at ([-\d.]+) ([-\d.]+)\)", s):
        ncs.add(pt(m.group(1), m.group(2)))
    nc_pins = {(r, p) for (r, p, x, y) in pin_at if (x, y) in ncs}

    nets = {}
    for ref, pn, x, y in pin_at:
        r = find(("pin", ref, pn))
        nets.setdefault(r, []).append(f"{ref}.{pn}")
    # name each net by its label(s)
    named = {}
    for text, _pts in by_text.items():
        r = find(("lab", text))
        named.setdefault(r, []).append(text)
    # every pin-net must carry exactly one label, except lone no-connects
    # and the anonymous switch->diode series segments (assert exact pairing)
    anon = 0
    for r, pins in nets.items():
        if len(pins) == 1:
            rt, pn = pins[0].split(".")
            if (rt, pn) in nc_pins:
                assert r not in named, \
                    f"audit: no-connect {pins[0]} shares net {named[r]}"
                continue
        if r not in named:
            assert len(pins) == 2, f"audit: unlabeled net {sorted(pins)}"
            parts = []
            for p in pins:
                m2 = (re.fullmatch(r"(SW|D)_([LR])(\d+)\.2", p)
                      or re.fullmatch(r"(J)_([LR])(2)\.1", p)
                      or re.fullmatch(r"(SW)_([LR])(PWR1)\.1", p))
                assert m2, f"audit: bad anon pin {p} in {sorted(pins)}"
                parts.append(m2.groups())
            kinds = {a for a, _, _ in parts}
            assert kinds == {"SW", "D"} or sorted(kinds) == ["J", "SW"], \
                f"audit: bad anon pair {sorted(pins)}"
            halves = {b for _, b, _ in parts}
            idxs = {c for _, _, c in parts}
            if kinds == {"SW", "D"}:
                assert len(halves) == 1 and len(idxs) == 1, \
                    f"audit: bad series pair {sorted(pins)}"
            else:  # BATT+ side of the power switch (JST.1 + SW common pin 1)
                assert halves == {"L"} or halves == {"R"}, \
                    f"audit: bad battery pair {sorted(pins)}"
                assert idxs == {"2", "PWR1"}, \
                    f"audit: bad battery pair {sorted(pins)}"
            anon += 1
            continue
        assert len(named[r]) == 1, \
            f"audit: net {sorted(pins)} labels={named.get(r)}"
    assert anon == 23, f"audit: {anon} anon segments, want 22 switches+1 battery"
    popis = {}
    for r, pins in nets.items():
        if r not in named:  # lone no-connect (asserted above)
            continue
        assert len(named[r]) == 1, \
            f"audit: net {sorted(pins)} labels={named.get(r)}"
        popis[named[r][0]] = sorted(pins)

    def expect(net, n):
        got = len(popis.get(net, []))
        assert got == n, f"audit: {net} has {got} pins, want {n} ({popis.get(net)})"

    # One sheet per half: every net is local to that half. TRRS_T/TRRS_R1 carry
    # this half's jack + the crossed MCU pin; the cable joins the two sheets.
    for r in range(3):
        expect(f"ROW{r}_{tag}", 7)
    expect(f"ROW3_{tag}", 5)
    for c in range(4):
        expect(f"COL{c}_{tag}", 5)
    for c in (4, 5):
        expect(f"COL{c}_{tag}", 4)
    for pre in ("ENC_A", "ENC_B", "ENC_SW"):
        expect(f"{pre}_{tag}", 2)
    expect(f"VBAT_SW_{tag}", 2)  # throw + MCU RAW (switch splits BATT+)
    expect("TRRS_T", 2)  # this half's jack tip + its MCU TX/RX pin
    expect("TRRS_R1", 2)
    # (no VBAT_SHARED: ring2 is intentionally unconnected — see TRRS block)
    expect("GND", 11)  # flag + 3 pwr-syms + JST + TRRS sleeve + 2 enc + 3 MCU
    print(f"audit {tag}: {len(popis)} nets, "
          f"{sum(len(v) for v in popis.values())} pins total")


def erc(tag):
    out = os.path.join(PCB_DIR, PROJECT[tag] + "-erc.rpt")
    # NOTE: no --exit-code-violations — kicad-cli returns the violation COUNT,
    # so the 5 deliberate spare-pin warnings would fail the build (exit 5).
    # Enforcement is by report parsing below instead: 0 errors, warnings
    # limited to the documented spares (same waiver style as the DRC gate).
    r = subprocess.run(
        [KICAD_CLI, "sch", "erc", "--format", "report",
         "--severity-all", "-o", out, sch_path(tag)],
        capture_output=True, text=True)
    tail = (r.stdout + r.stderr).strip().splitlines()
    print(f"  {tail[-1] if tail else 'erc done'}")
    return check_erc_report(out, tag)


# Spare MCU pins, deliberately single-pin (future use + UICR). They stay
# labeled — no_connect markers would hide intent (notes.md P1-6) — so the
# gate allowlists exactly these five isolated-pin warnings per half.
SPARE_LABELS = {"RST", "VCC3V3", "A3", "A2", "D10"}


def check_erc_report(path, tag):
    """0 if clean (0 errors + only documented spare warnings), 1 otherwise."""
    s = open(path).read()
    pats = re.findall(r"\[(.*?)\]: (.*?)\n((?:    .*\n)+)", s)
    want = {f"{n}_{tag}" for n in SPARE_LABELS}
    bad = []
    for typ, desc, body in pats:
        if "; error" in body:
            bad.append((typ, desc, body))
            continue
        if typ != "isolated_pin_label" or "; warning" not in body:
            bad.append((typ, desc, body))
            continue
        labels = set(re.findall(r"Label '([^']+)'", body))
        if labels - want:
            bad.append((typ, desc, body))
    nwarn = sum(1 for _, _, body in pats if "; warning" in body)
    nerr = sum(1 for _, _, body in pats if "; error" in body)
    print(f"  erc: {len(pats)} items ({nerr} errors, {nwarn} warnings, "
          f"{len(bad)} non-waived)" + ("" if not bad else " — FAILING"))
    for typ, desc, body in bad[:10]:
        print(f"  !! [{typ}] {desc}\n{body}")
    return 1 if bad else 0


def check_mcu_footprint():
    """Guard the faults ERC/DRC cannot see: socket pad MAP + GEOMETRY.

    The nice_nano symbol follows the PRO MICRO / nice!nano numbering: pins
    1-12 run down the TX/D1 edge (D1, D0, GND, GND, D2..D9) and pins 13-24 run
    down the RAW edge in the OPPOSITE direction (D10, D16, D14, D15, A0..A3,
    VCC, RST, GND, RAW). So pads 1 (D1) and 24 (RAW) are both at the USB end
    (y=0), while pads 12 (D9) and 13 (D10) are both at the antenna end
    (y=27.94). If the footprint's pad numbers don't match, KiCad still nets
    everything "correctly" (it connects by number) and every net lands on the
    wrong physical pad — RAW on GND and so on.

    Geometry (measured from the official nice!nano v2 pinout image at
    18.3 x 34.9mm board bbox, and keebio's ArduinoProMicro.kicad_mod):
      along-row pitch = 2.54mm (2.54mm between adjacent pads in one column)
      row separation  = 15.24mm (between the two columns — NOT 2.54mm)
      span along row  = 27.94mm (11 x 2.54, pads 1..12)

    This asserts the vendored socket is exactly:
       pads 1-12  -> column x=0,       y = 0, 2.54, ... 27.94   (D1 at y=0)
       pads 13-24 -> column x=-15.24,  y = 27.94 ... 0           (RAW at y=0)
    i.e. pad 1 and pad 24 share an end (the module's USB end). The old
    footprint used x=-2.54 (2.54mm separation, 12.7mm too narrow) and the
    module could not physically fit — this guard now checks separation as
    well as numbering, plus envelope containment in the _mcu keepout.
    """
    s = open(MCU_FP_FILE).read()
    pads = {}
    for m in re.finditer(
            r'\(pad\s+"(\d+)"\s+thru_hole\s+\S+\s+'
            r'\(at\s+([-\d.]+)\s+([-\d.]+)', s):
        pads[int(m.group(1))] = (float(m.group(2)), float(m.group(3)))
    assert len(pads) == 24, f"socket: {len(pads)} pads, want 24"
    col_a = sorted({x for i, (x, _) in pads.items() if i <= 12})
    col_b = sorted({x for i, (x, _) in pads.items() if i >= 13})
    assert len(col_a) == len(col_b) == 1, \
        f"socket: pads not on 2 columns: {col_a} {col_b}"
    # 1) along-row pitch: adjacent pads in one column are 2.54mm apart
    y_a = sorted([y for i, (_, y) in pads.items() if i <= 12])
    for a, b in zip(y_a, y_a[1:]):
        assert abs((b - a) - 2.54) < 0.01, \
            f"socket: along-row pitch {b - a}, want 2.54mm"
    # 2) row separation: columns are 15.24mm apart (Pro Micro standard)
    assert abs(abs(col_b[0] - col_a[0]) - 15.24) < 0.01, \
        f"socket: row separation {abs(col_b[0] - col_a[0])}, want 15.24mm"
    # 3) numbering: 1-12 up column A, 24-13 down column B (1/24 share y=0)
    for i in range(1, 25):
        want_x = col_a[0] if i <= 12 else col_b[0]
        want_y = round((i - 1) * 2.54, 2) if i <= 12 else round((24 - i) * 2.54, 2)
        x, y = pads[i]
        assert abs(x - want_x) < 0.01, \
            f"socket: pad {i} at x={x}, want column x={want_x}"
        assert abs(y - want_y) < 0.01, \
            f"socket: pad {i} at y={y}, want {want_y}"
    # 4) envelope: pads + courtyard must fit the measured 18.3 x 34.9 module
    xs = [x for x, _ in pads.values()]
    ys = [y for _, y in pads.values()]
    assert max(xs) - min(xs) <= 15.24 + 0.01, "socket: pad span exceeds 15.24"
    assert max(ys) - min(ys) <= 27.94 + 0.01, "socket: pad span exceeds 27.94"
    # the symbol geometry must agree: MCU_LEFT = pins 1-12, MCU_RIGHT = 13-24
    assert [n for n, _ in MCU_LEFT] == [str(i) for i in range(1, 13)]
    assert [n for n, _ in MCU_RIGHT] == [str(i) for i in range(13, 25)]
    # and the *functions* must match the nice!nano v2 silkscreen, so a
    # re-numbered symbol can't drift silently either.
    assert [n for _, n in MCU_LEFT] == \
        ["D1", "D0", "GND", "GND", "D2", "D3", "D4", "D5", "D6", "D7", "D8", "D9"]
    assert [n for _, n in MCU_RIGHT] == \
        ["D10", "D16", "D14", "D15", "A0", "A1", "A2", "A3",
         "VCC", "RST", "GND", "RAW"]
    print(f"socket OK: {MCU_FP_NAME} pitch 2.54, separation 15.24, "
          f"pad 1 (D1)/24 (RAW) at USB end; envelope fits 18.3x34.9")


def check_pwr_footprint():
    """Guard the WS-SLTV common assumption against library drift.

    Würth 450301014042: pin 1 (middle) = COMMON, pins 2/3 = throws. The
    schematic wires battery to symbol pin 1, so footprint pad 1 MUST be the
    middle pad — if a stock-library update ever renumbers the footprint,
    the battery lands on a throw and the switch still "works" in one
    position while shorting nothing (benign) or, worse, the rail floats.
    """
    p = os.path.join(STOCK_FP, "Button_Switch_THT.pretty",
                     "SW_Slide-03_Wuerth-WS-SLTV_10x2.5x6.4_P2.54mm.kicad_mod")
    s = open(p).read()
    pads = {}
    for m in re.finditer(
            r'\(pad\s+"(\d+)"\s+thru_hole\s+\S+\s+'
            r'\(at\s+([-\d.]+)\s+([-\d.]+)', s):
        pads[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    assert set(pads) == {"1", "2", "3"}, f"PWR footprint pads: {sorted(pads)}"
    x1, x2, x3 = pads["1"][0], pads["2"][0], pads["3"][0]
    assert min(x2, x3) < x1 < max(x2, x3), \
        f"PWR pad 1 not the middle pad: {pads} — common assumption broken"
    assert abs(abs(x2 - x3) - 5.08) < 0.01, \
        f"PWR outer span != 5.08mm: {pads}"
    print("PWR OK: WS-SLTV pad 1 middle (= common), 2.54mm pitch")


def build_project_file(tag):
    """Write Hojicha44-<Half>.kicad_pro from the shared template.

    KiCad rewrites this file on save; it only carries editor state, design
    rules and net classes, none of which differ between the halves. Keeping
    it generated means neither project can drift from the other.
    """
    import json
    src = pro_path("L") if os.path.exists(pro_path("L")) else pro_path("R")
    pro = json.load(open(src))
    pro["meta"]["filename"] = PROJECT[tag] + ".kicad_pro"
    # Sane routing defaults: the KiCad template ships 0-width/0-drill
    # presets that silently break DRC if used.
    pro["board"]["design_settings"]["track_widths"] = [0.25, 0.2]
    pro["board"]["design_settings"]["via_dimensions"] = [
        {"diameter": 0.8, "drill": 0.4}, {"diameter": 0.6, "drill": 0.3}]
    # DRC severities enforced by the generator (not left to GUI state):
    # PTH/NPTH inside courtyard = error so the tooling-hole gate stays armed
    # (pick_tooling() in gen_pcb.py is courtyard-aware). missing_courtyard
    # stays ignore: the vendored TRRS-PJ-320A has no courtyard by design.
    rs = pro["board"]["design_settings"].setdefault("rule_severities", {})
    rs["npth_inside_courtyard"] = "error"
    rs["pth_inside_courtyard"] = "error"
    # Netclasses. The battery rail (JST -> slide switch -> nice!nano RAW) is
    # the only high-current net on the board — a 130mAh cell peaks well under
    # 30mA, but the wire is still the one that must not be necked down by a
    # 0.25mm default while routing past the antenna keepout.
    ns = pro["net_settings"]
    default = next(c for c in ns["classes"] if c["name"] == "Default")
    power = dict(default)
    power.update({
        "name": "POWER",
        "priority": 1,
        "track_width": 0.5,
        "via_diameter": 1.0,
        "via_drill": 0.5,
        "clearance": 0.25,
    })
    if not any(c["name"] == "POWER" for c in ns["classes"]):
        ns["classes"].append(power)
    # Assign by pattern: works on both halves, and survives re-import.
    if not ns.get("netclass_patterns"):
        ns["netclass_patterns"] = []
    pat = {"pattern": "/VBAT_SW_*", "netclass": "POWER"}
    if not any(p.get("pattern") == pat["pattern"]
               for p in ns["netclass_patterns"]):
        ns["netclass_patterns"].append(pat)
    with open(pro_path(tag), "w") as f:
        json.dump(pro, f, indent=2)
        f.write("\n")


def build_half_project(tag):
    """Build one half: schematic + guards + audit. Returns the Sch."""
    s = Sch(project=PROJECT[tag])
    s.lib, s.pins, s.offs = load_lib()
    nets = NETS_L if tag == "L" else NETS_R
    build_half(s, tag, nets, 0)
    path = sch_path(tag)
    with open(path, "w") as f:
        f.write(render(s))
    sch_text = open(path).read()
    n_sym = len(s.refs)
    n_wire = sum(1 for b in s.body if b.startswith("\t(wire"))
    print(f"{PROJECT[tag]}: {n_sym} symbols, {n_wire} wires")
    uuids = re.findall(r'uuid "([^"]+)"', sch_text)
    assert len(uuids) == len(set(uuids)), "duplicate uuid!"
    # regression guards (per sheet): all diodes SOD-123 (the stock diode
    # symbol's default footprint is DO-41 and must never leak through);
    # exactly one PWR_FLAG (paralleling trips pin_to_pin ERC); no VBAT_SHARED
    # net (each half has its own cell; joining them via TRRS ring2 damages
    # the charger MOSFETs); the guarded column-major MCU socket.
    placed_diode_fps = re.findall(
        r'\(symbol \(lib_id "Diode:[^"]+"\).*?'
        r'\(property "Footprint" "([^"]+)"', sch_text, re.S)
    assert len(placed_diode_fps) == 22, \
        f"want 22 placed diodes, got {len(placed_diode_fps)}"
    assert set(placed_diode_fps) == {"Diode_SMD:D_SOD-123"}, \
        f"diode footprint drift: {set(placed_diode_fps)}"
    assert sch_text.count('(lib_id "power:PWR_FLAG")') == 1, \
        "want exactly one PWR_FLAG"
    assert "VBAT_SHARED" not in sch_text, "VBAT_SHARED must not exist"
    assert f'"Footprint" "{MCU_FOOTPRINT}"' in sch_text, \
        "MCU footprint drifted from the guarded column-major socket"
    assert sch_text.count(f'"Footprint" "{MCU_FOOTPRINT}"') == 1, \
        "MCU socket must be used exactly once per sheet"
    check_pwr_footprint()
    # No foreign refs: a sheet may only carry its own half, otherwise
    # "Update PCB from schematic" would drag both halves into one board.
    for other in set(HALVES) - {tag}:
        assert not re.search(rf'"Reference" "[^"]*_{other}\d', sch_text), \
            f"sheet {tag} carries half-{other} references"
    print("  guards OK: 22x SOD-123, 1x PWR_FLAG, no VBAT_SHARED")
    audit(path, s.offs, tag)
    return s


BOARD_TEMPLATE = """(kicad_pcb
	(version 20260206)
	(generator "pcbnew")
	(generator_version "10.0")
	(general
		(thickness 1.6)
		(legacy_teardrops no)
	)
	(paper "A3")
	(title_block
		(title "Hojicha44 {project}")
		(date "{date}")
		(rev "{rev}")
		(company "BitPeppr")
		(comment 1 "{comment}")
		(comment 2 "blank: import outline, place, route")
	)
	(layers
		(0 "F.Cu" signal)
		(2 "B.Cu" signal)
		(9 "F.Adhes" user "F.Adhesive")
		(11 "B.Adhes" user "B.Adhesive")
		(13 "F.Paste" user)
		(15 "B.Paste" user)
		(5 "F.SilkS" user "F.Silkscreen")
		(7 "B.SilkS" user "B.Silkscreen")
		(1 "F.Mask" user)
		(3 "B.Mask" user)
		(17 "Dwgs.User" user "User.Drawings")
		(19 "Cmts.User" user "User.Comments")
		(21 "Eco1.User" user "User.Eco1")
		(23 "Eco2.User" user "User.Eco2")
		(25 "Edge.Cuts" user)
		(27 "Margin" user)
		(31 "F.CrtYd" user "F.Courtyard")
		(29 "B.CrtYd" user "B.Courtyard")
		(35 "F.Fab" user)
		(33 "B.Fab" user)
	)
	(setup
		(stackup
			(layer "F.SilkS"
				(type "Top Silk Screen")
			)
			(layer "F.Paste"
				(type "Top Solder Paste")
			)
			(layer "F.Mask"
				(type "Top Solder Mask")
				(color "Green")
				(thickness 0.01)
			)
			(layer "F.Cu"
				(type "copper")
				(thickness 0.035)
			)
			(layer "dielectric 1"
				(type "core")
				(thickness 1.51)
				(material "FR4")
				(epsilon_r 4.5)
				(loss_tangent 0.02)
			)
			(layer "B.Cu"
				(type "copper")
				(thickness 0.035)
			)
			(layer "B.Mask"
				(type "Bottom Solder Mask")
				(color "Green")
				(thickness 0.01)
			)
			(layer "B.Paste"
				(type "Bottom Solder Paste")
			)
			(layer "B.SilkS"
				(type "Bottom Silk Screen")
			)
			(copper_finish "None")
			(dielectric_constraints no)
		)
		(pad_to_mask_clearance 0)
		(allow_soldermask_bridges_in_footprints no)
		(pcbplotparams
			(layerselection 0x00010fc_ffffffff)
			(plot_on_all_layers_selection 0x0000000_00000000)
			(disableapertmacros no)
			(usegerberextensions no)
			(usegerberattributes yes)
			(usegerberadvancedattributes yes)
			(creategerberjobfile yes)
			(dashed_line_dash_ratio 12.000000)
			(dashed_line_gap_ratio 3.000000)
			(svgprecision 4)
			(plotframeref no)
			(mode 1)
			(useauxorigin no)
			(hpglpennumber 1)
			(hpglpenspeed 20)
			(hpglpendiameter 15.000000)
			(pdf_front_fp_property_popups yes)
			(pdf_back_fp_property_popups yes)
			(pdf_metadata yes)
			(pdf_single_document no)
			(dxfpolygonmode yes)
			(dxfimperialunits yes)
			(dxfusepcbnewfont yes)
			(psnegative no)
			(psa4output no)
			(plot_black_and_white yes)
			(plotinvisibletext no)
			(sketchpadsonfab no)
			(plotpadnumbers no)
			(hidednponfab no)
			(sketchdnponfab yes)
			(crossoutdnponfab yes)
			(subtractmaskfromsilk no)
			(outputformat 1)
			(mirror no)
			(drillshape 1)
			(scaleselection 1)
			(outputdirectory "gerbers/")
		)
	)
	(net 0 "")
)
"""


def build_board_file(tag):
    """Write the per-half board file as a blank 2-layer board.

    A split keyboard is two PCBs, so each project needs its own .kicad_pcb
    before "Update PCB from schematic" can run. Deliberately EMPTY: the
    board outline is imported from layout/generated/v2/outlines/board.dxf and
    the footprints are placed from the ergogen points during layout. Only the
    stackup (1.6mm, 2 layer) and plot params live here.

    Never clobbers a placed board: gen_pcb.py owns footprints/nets/outline,
    so a re-run here skips files that already contain footprints.
    """
    import datetime
    path = os.path.join(PCB_DIR, PROJECT[tag] + ".kicad_pcb")
    if os.path.exists(path) and "(footprint" in open(path).read():
        print(f"  {PROJECT[tag]}.kicad_pcb already placed — kept")
        return path
    with open(path, "w") as f:
        f.write(BOARD_TEMPLATE.format(
            project=PROJECT[tag], date=datetime.date.today().isoformat(),
            rev=REV, comment=("Left half" if tag == "L" else "Right half")))
    return path


def main():
    load_spec()
    # project symbol library + table (same nice_nano def, bare name on disk)
    lib, _, _ = load_lib()
    bare = lib["nice_nano"].replace('(symbol "Hojicha44:nice_nano"',
                                    '(symbol "nice_nano"', 1)
    with open(SYM_LIB, "w") as f:
        f.write("(kicad_symbol_lib\n\t(version 20251024)\n"
                "\t(generator \"kicad_symbol_editor\")\n"
                "\t(generator_version \"10.0\")\n"
                + bare + "\n)\n")
    with open(SYM_TABLE, "w") as f:
        f.write("(sym_lib_table\n\t(version 7)\n"
                "\t(lib (name \"Hojicha44\")(type \"KiCad\")"
                "(uri \"${KIPRJMOD}/Hojicha44.kicad_sym\")"
                "(options \"\")(descr \"Hojicha44 project symbols\")))\n")
    check_mcu_footprint()
    # One project and one board file per half: a split keyboard is two PCBs.
    for tag in HALVES:
        build_half_project(tag)
    build_project_file("L")
    build_project_file("R")
    for tag in HALVES:
        build_board_file(tag)
    rc = 0
    for tag in HALVES:
        rc |= erc(tag)
    sys.exit(rc)


if __name__ == "__main__":
    main()
