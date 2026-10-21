# Keymap review — Hojicha44 (status: DRAFT, decisions listed)

Reviewed 2026-10-21 against `config/hojicha44.keymap` (ZMK) and
`spec/layout.yaml`. The structural gates pass (`npm test` →
`zmk-structure`: 46 positions, 3 layers, binding order verified, BLE
only), so the map is *mechanically* sound. What is left is the
ergonomic content — these are the decisions, with a recommendation for
each, so the file is one edit away from shipping.

## 1. What is already right

- **Position order** is the transform's own order (row-major, both
  halves per row), and the layer-1/layer-2 blocks are `&trans` mirrors
  of it — so a layer can be filled without re-deriving the index
  arithmetic.
- **Encoder**: volume on the default layer, scroll on L1. The pinned
  ZMK v0.3 build rejects `&trans` inside `sensor-bindings`, so the
  layers carry the volume pair rather than a transparent sensor — that
  is the right workaround and it is already commented.
- **Right thumb** carries RSFT / RALT / mo2 / ENTER with ENTER on the
  outer thumb (the natural split-board choice); the left thumb carries
  LCTRL / LGUI / mo1 / SPACE.
- **Encoder push → C_MUTE** via the kscan sideband, keeping the
  46-cell matrix untouched.
- The export mirror (Ctrl→Shift, Cmd→Opt) is handled by the KLE
  export, not by the keymap — nothing to change.

## 2. Open decisions (with the recommendation)

### 2.1 L1 (lower layer) is currently empty of function
Layer 1 is a `&trans` mirror of the default with a scroll encoder
binding — i.e. L1 does nothing except the encoder. The layout spec's
`open_points` still carries "Backspace/Delete live on layers (unmapped
so far): decide L1 positions".

**Recommendation:** make L1 the *editing/navigation* layer and put the
two editing keys on the **right thumb's L1** (the same two positions
that carry RSFT/RALT on the default layer) — Backspace on the inner
right thumb, Delete on the outer. Reasons: the right thumb is the
hand that is already on the home row's outer edge for Delete in a
split board, and it keeps the left thumb free for SPACE/LCTRL/LGUI.
The change is 2 lines in `lower_layer` (positions 42/43 of the 46-cell
list) plus a `&kp BSPC` / `&kp DEL`.

### 2.2 L2 (raise layer) is a placeholder
Layer 2 is all `&trans`; its own comment says it exists only to prove
reachability. The intended behaviour is a **Fn chord = L1+L2**.

**Recommendation:** implement it the standard way — make L2 the
**shifted/symbol layer** (the shifted characters of the 36 matrix
keys), and implement L1+L2 as a ZMK **chord macro** (`&mt L1 L2` /
`&lt`) so the chord resolves to a single keypress instead of leaving
the user holding a modifier. Note the caveat already in the file:
during the chord the rotation currently reads volume rather than L1's
scroll — a proper chord macro fixes that too, because the layer is
resolved before the sensor is read.

### 2.3 "Tab via L1+Space"
Also a chord, also better as a macro (or a plain L1+Space binding in
ZMK's `&mt` form) than as a documented convention the user has to
remember.

### 2.4 Layer 1/2 access
`mo 1` is on the **left** thumb and `mo 2` on the **right** thumb —
reasonable (one layer per hand), and it should stay that way: it is
what makes the L1+L2 chord reachable with two thumbs.

## 3. Not a decision, but worth stating

The map is a **DRAFT** and the file says so. Nothing in it should be
certified as "final" until §2 is closed — the firmware is the one
part of the kit that can be changed by a keystroke later, but the
*keymap* is what the user learns in the first hour, so it is worth
getting right before the pilot batch is built.

## 4. How to close it

1. Decide §2.1–§2.3 (the recommendations above are the defaults).
2. Edit `config/hojicha44.keymap` (the layers are positional — the
   index arithmetic is the transform's, so only the changed cells
   move).
3. Re-run `npm test` (`zmk-structure` re-verifies the 46 positions, the
   layer count and the binding order).
4. Re-verify on the first article that: the right thumb's L1 sends
   Backspace/Delete, the L1+L2 chord resolves to the symbol layer, and
   the encoder still reads volume on the default layer and scroll on
   L1.
