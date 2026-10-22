# Keymap — Hojicha44 (status: FINAL, rev 3 / M3.3)

Reviewed and finalised 2026-10-22. The keymap files are **generated** by
`config/gen_keymap.py` from `spec/layout.yaml` and gated by
`npm test` → `zmk-structure` (which runs the generator's `--check`).
Do not hand-edit `config/hojicha44.keymap`; change `spec/layout.yaml`
or the generator and regenerate.

Locked constraints (from the layout spec):
- QWERTY letters and the digit order 1234567890 are **not moved**.
- Every modifier, Space, Backspace, Tab, `` `~ `` and punctuation has a
  home on the board: nothing lives only inside a catch-22 chord.
- Inspiration: miryoku (home-row mods, thumb blocks, letters left
  plain), Corne/Sofle (digits + F-keys on L1, nav cluster on L2,
  `conditional_layers` adjust), precondition's home-row-mod guide
  (mod-frequency placement and hold/tap tuning).

## 1. Variants

Four firmware variants, differing ONLY in the home-row mod order and in
which thumb carries Space (spec/layout.yaml `keymap.variants`):

| variant      | mod order (pinky→index) | Space thumb | for |
|--------------|-------------------------|-------------|-----|
| `mac_left`   | CAGS (Ctrl Alt Gui Shft)| left        | macOS-heavy (default) |
| `mac_right`  | CAGS                    | right       | macOS |
| `win_left`   | GACS (Gui Alt Ctrl Shft)| left        | Windows/Linux |
| `win_right`  | GACS                    | right       | Windows/Linux |

The active variant is `config/hojicha44.keymap` (what CI builds and what
`MANIFEST.txt`-tracked firmware ships from); the default is `mac_left`
(macOS-heavy). Switch with:
`python3 config/gen_keymap.py --use win_right` — it rewrites
`config/hojicha44.keymap`, commit it, CI builds it. All four are always
regenerated into `config/variants/` for diffing and local flashing.

Mod-order rationale (precondition's frequency data; both orders keep
**Shift on F/J** — the index fingers, the strongest):
- Windows/Linux frequency: GUI < Alt < Ctrl < Shift → GACS (miryoku's
  order): Ctrl on D/K, Alt on S/L, GUI on A/;.
- macOS adds Cmd (=GUI, second-most-used) and demotes Ctrl → CAGS:
  Ctrl on A/;, Cmd on D/K, Alt on S/L.
Mods are side-specific codes: `L*` on the left hand (A S D F in position
order), `R*` on the right (; L K J).

## 2. Base layer (`default_layer`, layer 0)

```
Q W E R T  ~`    |  P O I U Y  |\
hml? A S D F  G [ |  ; L K J  H  ]}
Z X C V B  -     |  / . , M N  '
Esc  L1  Tab  Space    |    Del  L2  Bksp  Enter
```
(`hml`/`hmr` = the per-hand home-row mod-tap behaviors; `?` is one of
GUI/Ctrl depending on the variant. `|` = shift-\ parses to BSLH. Left
thumbs outer→inner; right thumbs outer→inner too — the spec's
`thumbs.right` list is written west→east = inner→outer and the generator
reverses it.)

- Letters and `/ . , M N ; : '` are plain `&kp` — no layer games on the
  hot alphabetic keys; G and H stay plain too (miryoku: keeps roll space
  in the middle and leaves the workingest keys untouched).
- `[ { ] }` on the inner home keys (unchanged from rev 2), `` ` ~ `` on
  the inner top (unchanged), **`-` on the left inner-bottom and `'` on
  the right inner-bottom are NEW (rev 3)** — Tab and Esc moved to the
  thumbs, so the "third symbol" of those columns is now useful on the
  base layer: `-` beside `, .` for ranges/negatives, `'` for quotes.
  The shifted forms (`_` `"` via the mods/Shift) need no dedicated keys.

### Thumbs — measured placement

Thumb-joint circle R = 91.2 mm; the four keys sit ~13.9° apart: the
innermost keys are the arc's ends (21° off neutral = strained to hold,
fine to tap), the middle two are 6.66°/7.25° off neutral (comfortable).
Therefore the rare keys take the extremes, the **holds** take the
comfortable mids, the frequent primaries take the inner palm-side:

| left (outer→inner) | right (outer→inner) | why |
|--------------------|---------------------|-----|
| Esc                | Delete              | rare + recoverable = outermost |
| **L1 hold**        | **L2 hold**         | long holds want low strain |
| Tab / Backspace    | Backspace / Tab*    | used pairs near the pinkie |
| Space / Enter*     | Enter / Space*      | Space on the palm-side inner |

(*left/right per the space-hand variant: left-space is the spec's
canonical order; right-space swaps Space↔Enter between the two
innermost positions, everything else fixed.)

## 3. Home-row mods — ZMK's "timeless" recipe

One behavior per hand so the hold-trigger lists can differ:

```
hml/hmr: zmk,behavior-hold-tap
  flavor = "balanced"          hold also fires when another key resolves
  require-prior-idle-ms = 150  fast rolls (of letters) resolve to taps
  tapping-term-ms = 280        high: the POSITIONAL triggers decide, not the timer
  quick-tap-ms = 175           tap-then-hold auto-repeats the LETTER
  bindings = <&kp>, <&kp>
  hold-trigger-key-positions = <the OTHER hand's 22 positions>
  hold-trigger-on-release      lets same-hand mod+key combos still work
```

Sourced from ZMK's own hold-tap documentation ("timeless home row
mods", balanced + require-prior-idle + positional triggers), which is
also what v0.3's binding schema supports (verified against the pinned
v0.3 `zmk,behavior-hold-tap` YAML: `tapping-term-ms`, `quick-tap-ms`,
`require-prior-idle-ms`, the flavor enum, all present).

How it resolves:
- type "ao" fast: O is on A's OTHER hand? no — O is same-hand as A →
  A resolves on O's press+release before the term → tap → "ao" ✓.
- hold A, press K: K is other-hand list → hold fires on K's release
  (hold-trigger-on-release) → instant cross-hand shortcuts ✓.
- hold A, press G (same hand): G is not in the list → A still resolves
  to GUI if held ≥ the term or when a listed key resolves ✓ (rare
  same-hand chord, deliberately slower than the term — this is the
  accidental-mod insurance).
- typist rolls like "the quick": require-prior-idle keeps zoom-mid-roll
  taps as taps even past 150 ms.

The trigger position lists are COMPUTED (the other hand's 22 of 46
positions, row-major interleaved), not hand-typed — the gate asserts
them against the layout.

## 4. L1 (lower, layer 1) — editing numbers: digits, shifts, F-keys

```
 1  2  3  4  5  6   |  7  8  9  0  -  =
 !  @  #  $  %  ^   |  &  *  (  )  _  +
 F1 F2 F3 F4 F5 F6  |  F7 F8 F9 F10 F11 F12
 thumbs: transparent (the row keeps working), L1 encoder = scroll
```
Digits in QWERTY order under 1–0 exactly as printed (Corne/Sofle
standard: one mental mapping, no relearning); equal/minus mirrored at
the inner ends for the `=`-`-` pairs of ranges; shifted symbols sit
directly under their digits. Encoder: `C_AC_SCROLL_*` (v0.3 has no bare
`C_SCROLL_*`).

## 5. L2 (raise, layer 2) — navigation, media, BT

```
 BT CLR  P0 .  P3 | Scr  Ins  Cap
 MUTE PREV PLAY NEXT V+ V- |  PgUp    ↑
 UNDO CUT COPY PAST    |  PgDn ←  ↓  →  Del  Bksp
 thumbs: transparent; L2 encoder = prev/next track
```
Left half = media/BT (Sofle's raise pattern; BT profiles 0–4 for the
split's central+peripheral+hosts), right half = an inverted-T arrow
cluster on the strong columns with PgUp/PgDn on the outer rail and
Home/End/Ins/PrtSc/Caps on the top rail. Delete/Backspace repeat here so
the editing trio lives under one thumb-hand reach.

## 6. Adjust (layer 3, the L1+L2 chord)

```
conditional_layers: if-layers = <1 2>, then-layer = <3>
- &bootloader at W's position, &sys_reset at E's (miryoku: reset on the
  top-row pinky column, both thumbs already busy holding the chord)
- every other key &none (there is nothing safe to type mid-chord)
- encoder = volume (harmless while reaching for boot)
```

## 7. Encoder

| layer | rotation | push |
|-------|----------|------|
| base  | volume ± | Mute (kscan sideband `enc_push_sideband`, both halves) |
| L1    | scroll ± | — |
| L2    | prev/next track | — |
| adjust| volume ± | — |

The push stays a **sideband**: the 46-cell matrix is untouched, the EC11
press maps through `enc_push_kscan` → `C_MUTE` on each half.

## 8. Gates

`npm test` → `zmk-structure` shells `python3 config/gen_keymap.py
--check`, which:
1. re-derives every binding from `spec/layout.yaml` and byte-compares
   the tracked active keymap + all 4 variants (a legend edit without
   regeneration, or vice versa, fails);
2. structurally validates each emitted keymap: exactly 4 layers × 46
   bindings matching the dtsi `RC()` count, one real `sensor-bindings`
   per layer (`&trans`/`&none` there is rejected by pinned v0.3 and
   would kill CI), mods exactly on the 8 home positions with the right
   variant codes, Space/Enter on the variant's thumb pair, `&mo 1`/`&mo
   2` fixed, hold-trigger lists == the other hand's 22 positions,
   hold-trigger-on-release present, the L1+L2→3 chord present, exactly
   one sideband Mute.

Negative controls (proven non-vacuous 2026-10-22, each reverts to
CLEAN): wrong tap keycode → caught as position drift AND stale-file;
deleted binding → 45-want-46; legend drift in the spec → both halves
stale; truncated hold-trigger list → caught; thumbs canonical-order edit
→ spec-parse assert.

## 9. First-article bench (firmware half)

See `spec/first-article.md` §firmware-bench; the items: per-half matrix
type-through, per-half encoder push = Mute, per-layer encoder direction
check, home-row hold/tap on all 8 positions × both flavors of muscle
memory (slow deliberate hold, fast roll), same-hand mod chord
(press-hold-past-term), the L1+L2 chord → Adjust, and the bootloader key
with a re-flash before anything else ("reply-btn" recovery proven).
