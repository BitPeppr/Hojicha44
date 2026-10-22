#!/usr/bin/env python3
"""Hojicha44 ZMK keymap generator — 4 variants from spec/layout.yaml.

The keymap files are GENERATED; do not hand-edit them.  The single source
of truth is spec/layout.yaml's `keymap:` block (the physical legends) and
`thumbs:` block, plus the variant table there.  This script emits:

    config/hojicha44.keymap           the ACTIVE variant (what CI builds)
    config/variants/<name>.keymap     all four, for diffing/flashing

Variants (keymap.variants in spec/layout.yaml):
    mac_left / mac_right   CAGS home-row mod order (macOS: Cmd on middle)
    win_left / win_right   GACS order (miryoku/precondition Windows/Linux)
The "space" half of the name is which thumb carries Space (the other
carries Enter).  The default variant is `keymap.variants.default`.

Usage:
    python3 config/gen_keymap.py            # regenerate everything
    python3 config/gen_keymap.py --check    # gate: tracked files in sync
    python3 config/gen_keymap.py --use X    # switch the active variant to X

Design (spec/keymap.md is the narrative; this is the mechanics):
  * QWERTY letters and the 1234567890 order are never moved.
  * Home-row mods as ZMK "timeless" hold-taps (ZMK's own documented
    recipe): flavor=balanced + require-prior-idle-ms + positional
    hold-trigger-key-positions (the OTHER hand's positions) +
    hold-trigger-on-release, one behavior per hand so the trigger lists
    can differ.
  * L1 (left thumb)  = digits row0 (QWERTY order), shifted digits row1,
                        F1-F12 row2.  Encoder = scroll.
  * L2 (right thumb) = BT + media + clipboard (left half); nav in an
                        inverted-T + Home/End/PgUp/PgDn/Ins/Caps/Pscrn
                        (right half).  Encoder = prev/next track.
  * L1+L2 chord -> Adjust (conditional_layers): bootloader + reset.
  * Encoder push (both halves) = Mute via the sideband, unchanged.

The --check gate re-derives everything and diffs the tracked files, and
additionally validates the structure of each EMITTED keymap (layer count,
binding count, sensor-bindings rule, mod positions, hold-trigger lists,
the dtsi transform's position count) so the gate is not vacuous: a
mutation of any tracked file, of the legends, or of the generator itself
fails the check.
"""
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(REPO, "spec", "layout.yaml")
KEYMAP = os.path.join(REPO, "config", "hojicha44.keymap")
VARDIR = os.path.join(REPO, "config", "variants")
DTSI = os.path.join(REPO, "boards", "shields", "hojicha44", "hojicha44.dtsi")

# ---- the four home-row mod orders (pinky -> index, mirrored by column) ----
# GACS: miryoku's order and precondition's recommended default for
#       Windows/Linux — frequency GUI < Alt < Ctrl < Shift, so the strongest
#       finger (index) gets the most-used modifier (Shift).
# CAGS: the macOS adaptation — on macOS Cmd(=GUI) outranks Ctrl, so GUI
#       takes the middle finger and Ctrl the pinky.
MOD_ORDERS = {
    "GACS": ["LGUI", "LALT", "LCTRL", "LSHIFT"],
    "CAGS": ["LCTRL", "LALT", "LGUI", "LSHIFT"],
}
RIGHT_OF = {"LGUI": "RGUI", "LALT": "RALT", "LCTRL": "RCTRL",
            "LSHIFT": "RSHIFT"}

# ---- home-row tap keys (position order: outer->inner on both halves) ----
# The LEFT hand's mod keys are A S D F (the outer four home keys); the RIGHT
# hand's are ; L K J.  G and H stay plain (miryoku does the same).
HOME_TAP_L = ["A", "S", "D", "F"]
HOME_TAP_R = ["SCLN", "L", "K", "J"]

# ---- legend -> ZMK keycode (base layer; every legend must map or the
#      generator fails loudly — a new legend without a binding is a bug) ----
LEGEND_KP = {
    "~`": "GRAVE", "{[_-": "LBKT", "-_": "MINUS",
    "|\\": "BSLH", "}]": "RBKT", "'\"": "SQT",
    ":;0": "SCLN", "?/": "SLASH", "<": "COMMA", ">.": "DOT",
}
LEGEND_THUMB = {
    "Esc": "ESC", "L1": "&mo 1", "Tab": "TAB", "Space": "SPACE",
    "Enter": "RET", "Backspace": "BSPC", "L2": "&mo 2", "Delete": "DEL",
}
# (single letters map to themselves)

# ---- hold-tap tuning (ZMK's documented "timeless home-row mods" recipe) ----
HM_FLAVOR = "balanced"
HM_REQUIRE_PRIOR_IDLE_MS = 150   # rolls resolve to taps; deliberate holds
HM_TAPPING_TERM_MS = 280         # high: the positional triggers decide
HM_QUICK_TAP_MS = 175            # tap-then-hold auto-repeats the LETTER

# ---- L1 (lower): digits + shifted digits + F-keys, QWERTY digit order ----
L1_ROWS = [
    ["N1", "N2", "N3", "N4", "N5", "N6",
     "N7", "N8", "N9", "N0", "MINUS", "EQUAL"],
    ["EXCL", "AT", "HASH", "DLLR", "PRCNT", "CARET",
     "AMPS", "ASTRK", "LPAR", "RPAR", "UNDERSCORE", "PLUS"],
    ["F1", "F2", "F3", "F4", "F5", "F6",
     "F7", "F8", "F9", "F10", "F11", "F12"],
]
L1_SENSOR = "&inc_dec_kp C_AC_SCROLL_UP C_AC_SCROLL_DOWN"

# ---- L2 (raise): BT/media/clipboard left, nav right (inverted-T) ----
L2_ROWS = [
    ["&bt BT_CLR", "&bt BT_SEL 0", "&bt BT_SEL 1", "&bt BT_SEL 2",
     "&bt BT_SEL 3", "&bt BT_SEL 4",
     "&kp PSCRN", "&kp INS", "&kp CLCK", "&kp HOME", "&kp END", "&none"],
    ["&kp C_MUTE", "&kp C_PREV", "&kp C_PLAY", "&kp C_NEXT",
     "&kp C_VOL_UP", "&kp C_VOL_DN",
     "&kp PG_UP", "&none", "&kp UP", "&none", "&none", "&none"],
    ["&kp K_UNDO", "&kp K_CUT", "&kp K_COPY", "&kp K_PASTE",
     "&none", "&none",
     "&kp PG_DN", "&kp LEFT", "&kp DOWN", "&kp RIGHT", "&kp DEL",
     "&kp BSPC"],
]
L2_SENSOR = "&inc_dec_kp C_PREV C_NEXT"

# ---- Adjust (the L1+L2 chord, via conditional_layers) ----
ADJUST_BOOT_POS = 1        # W's position: miryoku puts bootloader on the
ADJUST_RESET_POS = 2       # top-row pinky column; reset beside it
ADJUST_SENSOR = "&inc_dec_kp C_VOL_UP C_VOL_DN"
BASE_SENSOR = "&inc_dec_kp C_VOL_UP C_VOL_DN"


# ---------------------------------------------------------------- spec parse
def _unquote(tok):
    tok = tok.strip()
    if len(tok) >= 2 and tok[0] == '"' and tok[-1] == '"':
        return tok[1:-1].replace('\\"', '"').replace("\\\\", "\\")
    return tok


def _block(text, name):
    """The indented sub-block `name:` at any indent level (the yaml nests
    keymap/thumbs at 0, their children at 2, the column lists at 4)."""
    m = re.search(r"^([ \t]*)%s:\n" % name, text, re.M)
    assert m, f"spec/layout.yaml: no `{name}:` block"
    ind = len(m.group(1))
    out = []
    for line in text[m.end():].splitlines(keepends=True):
        if not line.strip() or line.lstrip().startswith("#"):
            out.append(line)
            continue
        if len(line) - len(line.lstrip()) <= ind:
            break
        out.append(line)
    assert out, f"spec/layout.yaml: `{name}:` block is empty"
    return "".join(out)


def _list_block(text, name):
    """{key: [entries]} for every `  key: [a, b, c]` line in the block.

    Greedy to the LAST `]` on the line: legends themselves contain `]`
    ("}]" is the right-inner-home key) and lines may carry trailing
    comments after the list.
    """
    out = {}
    for m in re.finditer(r"^\s+([A-Za-z0-9_]+): \[(.*)\]", text, re.M):
        out[m.group(1)] = [_unquote(t) for t in m.group(2).split(", ")]
    assert out, f"spec/layout.yaml: `{name}:` block has no list lines"
    return out


def load_spec():
    text = open(SPEC).read()
    km = _block(text, "keymap")
    left = _list_block(_block(km, "left"), "keymap.left")
    right = _list_block(_block(km, "right"), "keymap.right")
    for half, cols in (("left", left), ("right", right)):
        assert set(cols) == {"outer", "pinky", "ring", "middle", "index",
                             "inner"}, f"{half} columns drifted: {cols}"
        for c, legends in cols.items():
            assert len(legends) == 3, f"{half}.{c}: {legends}"
    # variants: `default: mac_left` + `mac_left: [CAGS, left]` lines
    var = _list_block(_block(km, "variants"), "keymap.variants")
    md = re.search(r"^\s+default:\s*(\S+)\s*$",
                   _block(km, "variants"), re.M)
    assert md, "keymap.variants: no `default:`"
    variants = {k: {"mods": v[0], "space": v[1]} for k, v in var.items()}
    assert md.group(1) in variants, \
        f"default variant {md.group(1)} not in {sorted(variants)}"
    for name, v in variants.items():
        assert v["mods"] in MOD_ORDERS, f"{name}: unknown order {v['mods']}"
        assert v["space"] in ("left", "right"), f"{name}: bad space side"
    # thumbs (the left-space arrangement is the spec's canonical order)
    th = _block(text, "thumbs")
    tl = _list_block(th, "thumbs")
    tleft = tl["left"]
    tright = tl["right"]
    assert len(tleft) == 4 and len(tright) == 4, (tleft, tright)
    assert tleft[3] == "Space" and tright[0] == "Enter", \
        "thumbs: the spec's canonical order must be the left-space variant"
    return left, right, variants, md.group(1), tleft, tright


# ----------------------------------------------------------------- emission
def legend_binding(legend):
    if legend in LEGEND_THUMB:
        b = LEGEND_THUMB[legend]
        return b if b.startswith("&") else f"&kp {b}"
    if legend in LEGEND_KP:
        return f"&kp {LEGEND_KP[legend]}"
    if len(legend) == 1 and legend.isalpha():
        return f"&kp {legend.upper()}"
    raise AssertionError(f"unmapped legend {legend!r} — add it to LEGEND_KP")


def half_rows(cols, half):
    """3 rows x 6 columns, position order (outer->inner on both halves)."""
    order = ["outer", "pinky", "ring", "middle", "index", "inner"] \
        if half == "left" else ["outer", "pinky", "ring", "middle",
                               "index", "inner"]
    # layout.yaml lists each COLUMN top->bottom; row r = [col[r] per column]
    return [[cols[c][r] for c in order] for r in range(3)]


def hold_trigger_positions(hand):
    """The OTHER hand's 22 keymap positions (0-45, row-major).

    Left hand: rows 0-2 cols 0-5 (0-5, 12-17, 24-29) + left thumbs 36-39.
    Right: 6-11, 18-23, 30-35 + right thumbs 42-45.
    """
    if hand == "left":   # triggers for the LEFT mods = right-hand keys
        return [p for r in range(3) for p in range(6 + 12 * r, 12 + 12 * r)] \
            + [42, 43, 44, 45]
    return [p for r in range(3) for p in range(12 * r, 6 + 12 * r)] \
        + [36, 37, 38, 39]


def base_layer(variant, lrows, rrows, tleft, tright):
    mods = MOD_ORDERS[variant["mods"]]
    out = []
    # position order is row-major INTERLEAVED (the transform's RC order):
    # row0-left, row0-right, row1-left, row1-right, row2-left, row2-right
    for r in range(3):
        for legend in lrows[r] + rrows[r]:
            out.append(legend_binding(legend))
    # home-row mods: left A S D F (positions 12-15), right ; L K J (18-21)
    for i, (pos, tap) in enumerate(zip((12, 13, 14, 15), HOME_TAP_L)):
        out[pos] = f"&hml {mods[i]} {tap}"
    rmods = [RIGHT_OF[m] for m in mods]
    for i, (pos, tap) in enumerate(zip((18, 19, 20, 21), HOME_TAP_R)):
        out[pos] = f"&hmr {rmods[i]} {tap}"
    # thumbs: the spec lists left west->east (outer->inner = position
    # order) but right west->east is INNER->outer, so the right half's
    # position order is the reverse of the spec list.
    thumbs = [legend_binding(t) for t in tleft] + ["&none", "&none"] \
        + [legend_binding(t) for t in reversed(tright)]
    if variant["space"] == "right":
        # swap Space and Enter between the two innermost thumbs (39 <-> 45)
        assert "&kp SPACE" in thumbs and "&kp RET" in thumbs, thumbs
        i, j = thumbs.index("&kp SPACE"), thumbs.index("&kp RET")
        thumbs[i], thumbs[j] = thumbs[j], thumbs[i]
    return out + thumbs


def thumbs_transparent():
    return ["&trans"] * 4 + ["&none", "&none"] + ["&trans"] * 4


def adjust_layer():
    out = ["&none"] * 46
    out[ADJUST_BOOT_POS] = "&bootloader"   # label is `bootloader` at pinned v0.3 (&boot is a later rename)
    out[ADJUST_RESET_POS] = "&sys_reset"
    return out


def bindings_dt(all46, indent="                "):
    """46 bindings -> the DT block (12 per row for rows 0-2, then thumbs)."""
    assert len(all46) == 46, len(all46)
    rows, thumbs = all46[:36], all46[36:]
    assert len(thumbs) == 10, len(thumbs)
    lines = []
    for r in range(3):
        lines.append(indent + " ".join(rows[12 * r:12 * r + 12]))
    lines.append(indent + " ".join(thumbs[:6]))
    lines.append(indent + " ".join(thumbs[6:]))
    close = indent[:-4] + ">;"
    # Rows are separated by bare newlines with NO ';' inside the `<>` array:
    # dtc has no ';' production inside an array, so an interior ';' is a
    # syntax error (dtc 1.8.1: <&kp 7;\n&kp 7;> -> "syntax error", while
    # newline-separated rows and </* valid */> parse clean). Style matches
    # the CI-compiled draft keymap (commit 063e47e). cf. validate().
    return "bindings = <\n" + "\n".join(lines) + "\n" + close


def generate(variant, lrows, rrows, tleft, tright):
    base = base_layer(variant, lrows, rrows, tleft, tright)
    l1 = [f"&kp {k}" for row in L1_ROWS for k in row]
    l2 = L2_ROWS[0] + L2_ROWS[1] + L2_ROWS[2]
    adj = adjust_layer()
    th_l1 = th_l2 = thumbs_transparent()
    th_adj = ["&none"] * 10
    hml_trig = " ".join(str(p) for p in hold_trigger_positions("left"))
    hmr_trig = " ".join(str(p) for p in hold_trigger_positions("right"))
    mod_note = {"GACS": "GUI Alt Ctrl Shift (miryoku/Windows)",
                "CAGS": "Ctrl Alt GUI Shift (macOS: Cmd on the middle)"}[
        variant["mods"]]
    return f"""/* Hojicha44 keymap — {variant['name']} variant.
 * GENERATED by config/gen_keymap.py from spec/layout.yaml — DO NOT EDIT.
 *   mod order : {mod_note}
 *   space     : {variant['space']} thumb (the other carries Enter)
 * Regenerate: python3 config/gen_keymap.py            (all variants)
 * Switch   : python3 config/gen_keymap.py --use {variant['name']}
 * Design   : spec/keymap.md (the narrative for every table below).
 */
#include <behaviors.dtsi>
#include <dt-bindings/zmk/keys.h>
#include <dt-bindings/zmk/bt.h>

/ {{
    /* Home-row mods, ZMK's documented "timeless" recipe: balanced flavor,
     * require-prior-idle (fast rolls resolve to taps), a long tapping term
     * (the POSITIONAL triggers decide, not the timer) and positional
     * hold-trigger-key-positions listing the OTHER hand's keys, with
     * hold-trigger-on-release so same-hand modifier combos still work.
     * One behavior per hand so the trigger lists can differ. */
    behaviors {{
        hml: home_row_mod_left {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "{HM_FLAVOR}";
            require-prior-idle-ms = <{HM_REQUIRE_PRIOR_IDLE_MS}>;
            tapping-term-ms = <{HM_TAPPING_TERM_MS}>;
            quick-tap-ms = <{HM_QUICK_TAP_MS}>;
            bindings = <&kp>, <&kp>;
            hold-trigger-key-positions = <{hml_trig}>;
            hold-trigger-on-release;
        }};
        hmr: home_row_mod_right {{
            compatible = "zmk,behavior-hold-tap";
            #binding-cells = <2>;
            flavor = "{HM_FLAVOR}";
            require-prior-idle-ms = <{HM_REQUIRE_PRIOR_IDLE_MS}>;
            tapping-term-ms = <{HM_TAPPING_TERM_MS}>;
            quick-tap-ms = <{HM_QUICK_TAP_MS}>;
            bindings = <&kp>, <&kp>;
            hold-trigger-key-positions = <{hmr_trig}>;
            hold-trigger-on-release;
        }};
    }};

    /* L1 + L2 held together -> Adjust (ZMK conditional layers; this is
     * the "Fn chord" the v1 layout spec called for). */
    conditional_layers {{
        compatible = "zmk,conditional-layers";
        adjust_cond {{
            if-layers = <1 2>;
            then-layer = <3>;
        }};
    }};

    keymap {{
        compatible = "zmk,keymap";
        label = "Hojicha44";

        default_layer {{
            {bindings_dt(base)}
            sensor-bindings = <{BASE_SENSOR}>;
        }};
        lower_layer {{
            {bindings_dt(l1 + th_l1)}
            sensor-bindings = <{L1_SENSOR}>;
        }};
        raise_layer {{
            {bindings_dt(l2 + th_l2)}
            sensor-bindings = <{L2_SENSOR}>;
        }};
        adjust_layer {{
            {bindings_dt(adj)}
            sensor-bindings = <{ADJUST_SENSOR}>;
        }};
    }};

    /* Encoder push -> Mute on BOTH halves (the dtsi defines the direct-GPIO
     * kscan on the shared D16; the sideband keeps the 46-cell matrix
     * untouched). First article: press on EACH half must send Mute. */
    enc_push_sideband: sideband_enc_push {{
        compatible = "zmk,kscan-sideband-behaviors";
        kscan = <&enc_push_kscan>;
        auto-enable;
        push_mute: push_0 {{
            row = <0>;
            column = <0>;
            bindings = <&kp C_MUTE>;
        }};
    }};
}};
"""


# ------------------------------------------------------------------ gates
# The transform order the generator ASSUMES (audit-verified against
# gpio-map.md and the PCB column contract: left scan cols 0-5 physical
# outer->inner; the right half is mirrored at col-offset 6, so scan col 6
# is physical outer too; thumbs RC(3,0..3) left outer->inner, RC(3,4)/(3,5)
# the two ghost matrix slots, RC(3,6..9) right thumbs). Pinned so a hand
# reorder/renumber of the dtsi map fails the gate instead of silently
# relabeling every key under it.
CANON_MAP_ORDER = (
    [(r, c) for r in range(3) for band in (range(6), range(6, 12))
     for c in band]
    + [(3, 0), (3, 1), (3, 2), (3, 3), (3, 4), (3, 5),
       (3, 6), (3, 7), (3, 8), (3, 9)])


def dtsi_map():
    """The transform's RC() entries IN ORDER — the keymap's position order."""
    t = re.sub(r"/\*[\s\S]*?\*/", "", open(DTSI).read())
    return [tuple(map(int, m)) for m in
            re.findall(r"RC\((\d+),\s*(\d+)\)", t)]


def dtsi_position_count():
    """The transform's RC() count — the keymap must have exactly as many
    bindings per layer as the dtsi has positions (cross-file gate)."""
    return len(dtsi_map())


def validate(text, variant, lrows, rrows, tleft, tright):
    """Structural checks on an EMITTED keymap (not just byte-compare)."""
    bad = []
    npos = dtsi_position_count()
    if npos != 46:
        bad.append(f"dtsi has {npos} RC positions, want 46")
    order = dtsi_map()
    if order != CANON_MAP_ORDER:
        for i, (got, want) in enumerate(zip(order, CANON_MAP_ORDER)):
            if got != want:
                bad.append(f"dtsi transform [{i}]: RC({got[0]}, {got[1]}) "
                           f"!= RC({want[0]}, {want[1]}) — the map drifted, "
                           "every key under it would mislabel")
                break
    layers = []
    for m in re.finditer(
            r"^\s{8}(\w+_layer) \{([^{}]*?(?:\{[^{}]*\}[^{}]*?)*)\};",
            text, re.M):
        name, blk = m.group(1), m.group(2)
        bm = re.search(r"bindings = <\n([\s\S]*?)>;", blk)
        sm = re.search(r"sensor-bindings = <(.*)>;", blk)
        if not bm or not sm:
            bad.append(f"{name}: malformed layer node")
            continue
        layers.append((name, bm.group(1), sm.group(1)))
        # dtc gate: an interior ';' inside `bindings = <…>` is a syntax
        # error (see bindings_dt). Regex-only so the gate runs without dtc.
        if ";" in bm.group(1):
            bad.append(f"{name}: interior ';' inside `bindings = <…>` — "
                       "rows must be newline-separated")
    if len(layers) != 4:
        bad.append(f"{len(layers)} layer nodes, want exactly 4")
    want_sensors = [BASE_SENSOR, L1_SENSOR, L2_SENSOR, ADJUST_SENSOR]
    BIND_RE = re.compile(r"&[A-Za-z][\w-]*(?:\s+[A-Za-z0-9_+]+)*")
    for (name, blk, sensor), want in zip(layers, want_sensors):
        toks = BIND_RE.findall(blk)
        if len(toks) != 46:
            bad.append(f"{name}: {len(toks)} bindings, want 46")
        if sensor.strip() != want:
            bad.append(f"{name}: sensor {sensor!r} != {want!r}")
        if re.search(r"&(?:trans|none)(?![\w-])", sensor):
            bad.append(f"{name}: &trans/&none in sensor-bindings "
                       f"(rejected by the pinned ZMK v0.3)")
    # home-row mods exactly on 12-15 (&hml) and 18-21 (&hmr)
    toks = BIND_RE.findall(layers[0][1])
    mods = MOD_ORDERS[variant["mods"]]
    for i, pos in enumerate((12, 13, 14, 15)):
        if not toks[pos].startswith("&hml "):
            bad.append(f"position {pos} is {toks[pos]!r}, want &hml")
        elif toks[pos] != f"&hml {mods[i]} {HOME_TAP_L[i]}":
            bad.append(f"position {pos}: {toks[pos]!r} != "
                       f"'&hml {mods[i]} {HOME_TAP_L[i]}'")
    rmods = [RIGHT_OF[m] for m in mods]
    for i, pos in enumerate((18, 19, 20, 21)):
        if toks[pos] != f"&hmr {rmods[i]} {HOME_TAP_R[i]}":
            bad.append(f"position {pos}: {toks[pos]!r} != "
                       f"'&hmr {rmods[i]} {HOME_TAP_R[i]}'")
    # plain keys stay plain: G at 16, H at 22 (miryoku leaves them free)
    if toks[16] != "&kp G" or toks[22] != "&kp H":
        bad.append(f"G/H drifted: {toks[16]!r} {toks[22]!r}")
    # every thumb slot is exactly the designed binding — no slot is left
    # unchecked (Esc L1 Tab Space|Enter / ghost gap gap / Del L2 Backspace
    # Enter|Space at positions 36-45)
    thumb_want = ["&kp ESC", "&mo 1", "&kp TAB", None,
                  "&none", "&none", "&kp DEL", "&mo 2", "&kp BSPC", None]
    left_space = variant["space"] == "left"
    thumb_want[3] = "&kp SPACE" if left_space else "&kp RET"
    thumb_want[9] = "&kp RET" if left_space else "&kp SPACE"
    for pos, w in zip(range(36, 46), thumb_want):
        if w is not None and toks[pos] != w:
            bad.append(f"thumb position {pos}: {toks[pos]!r} != {w!r}")
    # base legends: every non-mod, non-thumb binding matches spec/layout.yaml
    # (position order is row-major interleaved, same as base_layer)
    want = []
    for r in range(3):
        want += [legend_binding(x) for x in lrows[r] + rrows[r]]
    for pos in range(36):
        if pos in (12, 13, 14, 15, 18, 19, 20, 21):
            continue
        if toks[pos] != want[pos]:
            bad.append(f"position {pos}: {toks[pos]!r} != legend "
                       f"{want[pos]!r}")
    # hold-trigger lists: exactly the other hand's positions
    hml = re.search(r"hml: home_row_mod_left \{[\s\S]*?"
                    r"hold-trigger-key-positions = <([^>]*)>", text)
    hmr = re.search(r"hmr: home_row_mod_right \{[\s\S]*?"
                    r"hold-trigger-key-positions = <([^>]*)>", text)
    want_l = " ".join(str(p) for p in hold_trigger_positions("left"))
    want_r = " ".join(str(p) for p in hold_trigger_positions("right"))
    if not hml or hml.group(1).split() != want_l.split():
        bad.append("hml hold-trigger-key-positions != the right hand's "
                   "positions (the timeless mods would misfire)")
    if not hmr or hmr.group(1).split() != want_r.split():
        bad.append("hmr hold-trigger-key-positions != the left hand's "
                   "positions")
    if "hold-trigger-on-release" not in text:
        bad.append("hold-trigger-on-release missing (same-hand mod combos "
                    "would break)")
    # the chord
    if "if-layers = <1 2>;" not in text or "then-layer = <3>;" not in text:
        bad.append("conditional_layers L1+L2 -> 3 missing")
    # adjust content: the bootloader recipe stays anchored (v0.3 label)
    want_idx = {ADJUST_BOOT_POS: "&bootloader", ADJUST_RESET_POS: "&sys_reset"}
    adj_toks = BIND_RE.findall(layers[3][1])
    if len(adj_toks) == 46:
        for pos, want_b in want_idx.items():
            if adj_toks[pos] != want_b:
                bad.append(f"adjust position {pos}: {adj_toks[pos]!r} "
                           f"!= {want_b!r} (boot/reset anchors moved)")
    # the sideband: exactly one sideband node, wired to the dtsi's
    # direct-GPIO kscan, push key at row 0 / column 0 (the dtsi contract:
    # `input-keys` emits row 0 / column 0 events), bound to Mute
    if text.count("zmk,kscan-sideband-behaviors") != 1 \
            or "push_mute: push_0" not in text \
            or "kscan = <&enc_push_kscan>" not in text \
            or "row = <0>" not in text or "column = <0>" not in text \
            or "&kp C_MUTE" not in text:
        bad.append("the encoder-push sideband (Mute at row 0/column 0 on "
                   "the enc_push_kscan) must appear exactly once with the "
                   "dtsi wiring intact")
    # no transparent on the base layer
    if "&trans" in layers[0][1]:
        bad.append("transparent on the base layer")
    return bad


def main():
    args = sys.argv[1:]
    left, right, variants, default, tleft, tright = load_spec()
    lrows = half_rows(left, "left")
    rrows = half_rows(right, "right")
    names = ["mac_left", "mac_right", "win_left", "win_right"]
    assert set(names) == set(variants), \
        f"variant table drifted: {sorted(variants)}"

    for name in names:
        v = dict(variants[name])
        v["name"] = name
        text = generate(v, lrows, rrows, tleft, tright)
        bad = validate(text, v, lrows, rrows, tleft, tright)
        if bad:
            for b in bad[:8]:
                print(f"  !! {name}: {b}")
            print(f"keymap gate: FAILING (internal validation of {name})")
            return 1

    if "--use" in args:
        new = args[args.index("--use") + 1]
        assert new in variants, f"--use {new}: not one of {names}"
        v = dict(variants[new])
        v["name"] = new
        open(KEYMAP, "w").write(
            generate(v, lrows, rrows, tleft, tright))
        print(f"config/hojicha44.keymap is now the {new} variant "
              f"(commit it; CI builds it).")
        return 0

    if "--check" in args:
        problems = 0
        for name in names + [f"active ({default})"]:
            is_active = name not in names
            path = KEYMAP if is_active else \
                os.path.join(VARDIR, f"hojicha44_{name}.keymap")
            v = dict(variants[default if is_active else name])
            v["name"] = default if is_active else name
            fresh = generate(v, lrows, rrows, tleft, tright)
            tracked = open(path).read()
            if tracked != fresh:
                problems += 1
                print(f"  !! {os.path.relpath(path, REPO)} is stale — "
                      f"regenerate with config/gen_keymap.py")
            bad = validate(tracked, v, lrows, rrows, tleft, tright)
            if bad:
                problems += 1
                for b in bad[:6]:
                    print(f"  !! {os.path.relpath(path, REPO)}: {b}")
        if problems:
            print("keymap gate: FAILING")
            return 1
        print(f"keymap gate: CLEAN (4 variants + active={default}, "
              f"validated against spec/layout.yaml and "
              f"{dtsi_position_count()} dtsi positions)")
        return 0

    # --check handled above; this is the write path
    os.makedirs(VARDIR, exist_ok=True)
    for name in names:
        v = dict(variants[name])
        v["name"] = name
        text = generate(v, lrows, rrows, tleft, tright)
        path = os.path.join(VARDIR, f"hojicha44_{name}.keymap")
        open(path, "w").write(text)
    v = dict(variants[default])
    v["name"] = default
    open(KEYMAP, "w").write(generate(v, lrows, rrows, tleft, tright))
    print(f"keymap: regenerated 4 variants + active={default} "
          f"(config/hojicha44.keymap)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
