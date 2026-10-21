/* Hojicha44 static repo checks — no KiCad needed (runs in CI).
 * Covers the doc/gate regressions that previously shipped silently:
 *  - spec/electronics.yaml parses + erc stanza states the exact gate
 *  - Ergogen TRRS comment matches measured 22.40/20.42/recessed geometry
 *  - gen_schematic.py NEED has no duplicate (lib, symbol) entries
 *  - gen_pcb.py W1 gate asserts the exact 28-entry mismatch set, verified
 *    against the TRACKED release DRC copies (generated/release/vX.Y.Z/)
 *  - release MANIFEST exists for the spec version and lists both halves
 *  - ZMK structure: transform map RC count == keymap bindings per layer,
 *    exact 2 layers, every binding's POSITION against the row-major
 *    interleaved legend signature (the left-then-right ordering bug can
 *    never silently ship wrong characters), col-offset coverage, BLE-only
 *    (no wired-split node, no SPLIT_WIRED), diode-direction set
 *    (the 6-column-transform-for-12-columns bug can never recur silently)
 */
const { execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");
const yaml = require("js-yaml");

const REPO = path.dirname(path.dirname(path.resolve(__filename)));
let failures = 0;
const ok = (name) => console.log(`ok: ${name}`);
const fail = (name, detail) => {
  failures += 1;
  console.log(`FAIL: ${name}${detail ? ` — ${detail}` : ""}`);
};

// 1. spec parses + erc gate text
try {
  const spec = yaml.load(
    fs.readFileSync(path.join(REPO, "spec", "electronics.yaml"), "utf8")
  );
  const erc = String((spec.schematic || {}).erc || "");
  if (!/0 errors/.test(erc) || !/RST/.test(erc) || !/D10/.test(erc)) {
    fail("spec-erc", "erc stanza must state 0 errors + spare list");
  } else {
    ok("spec-erc");
  }
  const ver = String(spec.version || "");
  if (!/^\d+\.\d+\.\d+$/.test(ver)) {
    fail("spec-version", `want MAJOR.MINOR.PATCH, got ${ver}`);
  } else {
    ok(`spec-version (${ver})`);
    const reldir = path.join(REPO, "generated", "release", `v${ver}`);
    if (!fs.existsSync(path.join(reldir, "MANIFEST.txt"))) {
      fail("release-manifest", `missing ${reldir}/MANIFEST.txt`);
    } else {
      const man = fs.readFileSync(path.join(reldir, "MANIFEST.txt"), "utf8");
      if (!/\[Left\]/.test(man) || !/\[Right\]/.test(man)) {
        fail("release-manifest", "must list [Left] and [Right]");
      } else {
        ok("release-manifest");
      }
    }
  }
} catch (e) {
  fail("spec-parse", e.message);
}

// 2. Ergogen TRRS comment matches measured geometry
{
  const cfg = fs.readFileSync(
    path.join(REPO, "layout", "ergogen", "config.yaml"),
    "utf8"
  );
  if (/3\.46mm PROUD/.test(cfg) || /13\.50mm/.test(cfg)) {
    fail("trrs-comment", "stale 3.46mm-PROUD / 13.50mm numbers still present");
  } else if (
    !/22\.40mm/.test(cfg) ||
    !/20\.42mm/.test(cfg) ||
    !/0\.99mm RECESSED/.test(cfg)
  ) {
    fail("trrs-comment", "must state 22.40/20.42/0.99mm recessed");
  } else {
    ok("trrs-comment");
  }
}

// 3. NEED has no duplicate (lib, symbol) entries
{
  const src = fs.readFileSync(
    path.join(REPO, "pcb", "generators", "gen_schematic.py"),
    "utf8"
  );
  // Only scan the NEED block (first occurrence region) to avoid false hits.
  const needBlock = src.slice(src.indexOf("NEED = ["), src.indexOf("LIB_IDS"));
  const needPairs = [...needBlock.matchAll(/"([^"]+\.kicad_sym)",\s*"([^"]+)"/g)].map(
    (m) => `${m[1]}:${m[2]}`
  );
  const dupes = needPairs.filter((p, i) => needPairs.indexOf(p) !== i);
  if (dupes.length) {
    fail("need-dedupe", `duplicates: ${[...new Set(dupes)].join(", ")}`);
  } else {
    ok(`need-dedupe (${needPairs.length} entries)`);
  }
}

// 4. W1 exact-set gate, run against tracked release DRC copies (no KiCad).
try {
  const py = `
import sys
sys.path.insert(0, ${JSON.stringify(
    path.join(REPO, "pcb", "generators")
  )})
import gen_pcb, glob, os
reldir = ${JSON.stringify(
    path.join(
      REPO,
      "generated",
      "release",
      `v${yaml.load(
        fs.readFileSync(path.join(REPO, "spec", "electronics.yaml"), "utf8")
      ).version}`
    )
  )}
rc = 0
for tag, half in (("L", "Left"), ("R", "Right")):
    p = os.path.join(reldir, half, f"Hojicha44-{half}-drc.rpt")
    assert os.path.exists(p), f"missing {p}"
    rc |= gen_pcb.check_drc_report(p, tag)
# negative control: a 29th mismatch must fail
s = open(os.path.join(reldir, "Left", "Hojicha44-Left-drc.rpt")).read()
s += "[lib_footprint_mismatch]: Footprint 'D_SOD-123' does not match copy in library 'Diode_SMD'\\n    Local override; warning\\n    @(0, 0): Footprint D_L99\\n"
open("/tmp/hojicha-w1-neg.rpt", "w").write(s)
neg = gen_pcb.check_drc_report("/tmp/hojicha-w1-neg.rpt", "L")
assert neg == 1, "W1 gate must reject a 29th mismatch"
print("w1-gate: exact 28/half passes, 29th rejected")
sys.exit(rc)
`;
  execFileSync("python3", ["-c", py], { stdio: "inherit", cwd: REPO });
  ok("w1-gate");
} catch (e) {
  fail("w1-gate", "see python output above");
}

// 5. ZMK structure: map RC count == bindings/layer, span + offset covered,
//    BLE-only transport, diode-direction set (no toolchain needed).
try {
  const d = (p) => fs.readFileSync(path.join(REPO, p), "utf8");
  const strip = (s) => s
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .split("\n")
    .filter((l) => !l.trim().startsWith("#") && !l.trim().startsWith("//"))
    .join("\n");
  const dtsi = strip(d("boards/shields/hojicha44/hojicha44.dtsi"));
  const cols = parseInt(/columns\s*=\s*<(\d+)>/.exec(dtsi)[1], 10);
  const rows = parseInt(/rows\s*=\s*<(\d+)>/.exec(dtsi)[1], 10);
  const rcs = [.../map\s*=\s*<([\s\S]*?)>/.exec(dtsi)[1]
    .matchAll(/RC\((\d+),\s*(\d+)\)/g)].map((m) => [+m[1], +m[2]]);
  const have = (r, c) => rcs.some(([a, b]) => a === r && b === c);
  const km = strip(d("config/hojicha44.keymap"));
  const ki = km.indexOf("keymap");
  let depth = 0, end = -1;
  const start = km.indexOf("{", ki);
  for (let i = start; i < km.length; i++) {
    if (km[i] === "{") depth++;
    else if (km[i] === "}") { depth--; if (!depth) { end = i; break; } }
  }
  const body = km.slice(start, end);
  // Layer-1 (lower) and layer-2 (raise) placeholders: all-transparent
  // except the deliberately-unbound left R3C4-C5 (&none, floating row).
  const PLACEHOLDER = [
    ...Array(36).fill("&trans"),
    "&trans", "&trans", "&trans", "&trans",
    "&none", "&none",                          // unpopulated left R3C4-C5
    "&trans", "&trans", "&trans", "&trans",
  ];
  // Full token sequence per layer (binding + args, in position order),
  // checked against the ROW-MAJOR INTERLEAVED signature so the B1-class
  // bug (bindings listed left-half-first instead of per-row) can never
  // ship silently again. The default layer's signature is now DERIVED
  // from spec/layout.yaml's keymap legends — single source, so a legend
  // edit must ride with a keymap edit or the compare fails. (The old
  // hardcoded DEFAULT_EXP silently pinned a stale draft binding set.)
  const toks = (s) => s.match(/&[A-Za-z][\w-]*(?:\s+[A-Za-z0-9_+]+)*/g) || [];
  const layerBlocks = [
    ...body.matchAll(/(?<!sensor-)bindings\s*=\s*<([\s\S]*?)>/g),
  ].map((m) => toks(m[1]));
  const kmY = yaml.load(fs.readFileSync(
    path.join(REPO, "spec", "layout.yaml"), "utf8"));
  const legends = {
    left: kmY.keymap.left, right: kmY.keymap.right, thumbs: kmY.thumbs,
  };
  const colNames = ["outer", "pinky", "ring", "middle", "index", "inner"];
  // US-layout composite legends -> UNSHIFTED ZMK keycode (| is shift-\,
  // } is shift-]; the digits on ":;0" live on L1, still pending).
  // Thumb/mod legends name side-specific modifiers per export_kle's
  // mirror map (Ctrl->Shift, Cmd->Opt across the halves).
  const KP = {
    Q: "Q", W: "W", E: "E", R: "R", T: "T", Y: "Y", U: "U", I: "I",
    O: "O", P: "P", A: "A", S: "S", D: "D", F: "F", G: "G", H: "H",
    J: "J", K: "K", L: "L", Z: "Z", X: "X", C: "C", V: "V", B: "B",
    M: "M", N: "N",
    "~`": "GRAVE", "{[_-": "LBKT", "|\\": "BSLH", "}]": "RBKT",
    ":;0": "SCLN", "<": "COMMA", ">.": "DOT", "?/": "SLASH",
    Tab: "TAB", Esc: "ESC",
    Ctrl: "LCTRL", Cmd: "LGUI", Space: "SPACE",
    Shift: "RSFT", Opt: "RALT", Enter: "ENTER",
  };
  const mkBinding = (lg) => {
    if (lg === "L1") return "&mo 1";
    if (lg === "L2") return "&mo 2";
    if (!KP[lg]) throw new Error(
      `unmapped legend in spec/layout.yaml keymap: "${lg}"`);
    return `&kp ${KP[lg]}`;
  };
  const exp = [];
  for (let r = 0; r < 3; r++) {
    for (const c of colNames) exp.push(mkBinding(legends.left[c][r]));
    for (const c of colNames) exp.push(mkBinding(legends.right[c][r]));
  }
  // Thumbs: left list is west->east == position order (outer..inner);
  // the right list is west->east == inner->outer (gap side), so position
  // order reads it mirrored end-first. 2 &none close the left row (the
  // floating R3C4-C5).
  for (const lg of legends.thumbs.left) exp.push(mkBinding(lg));
  exp.push("&none", "&none");
  for (const lg of [...legends.thumbs.right].reverse())
    exp.push(mkBinding(lg));
  const problems = [];
  // Sensor bindings may reference only sensor-capable behaviors: the
  // pinned ZMK v0.3 build-user-config workflow rejects &trans there
  // ("/behaviors/transparent lacks #sensor-binding-cells" — this killed
  // CI on the first v0.3.1 push). Structure checks stop short of
  // devicetree semantics, so guard the class most likely to recur.
  const sensorLines = body.match(/^\s*sensor-bindings.*$/gm) || [];
  if (sensorLines.length !== layerBlocks.length) {
    problems.push(`want one sensor-bindings per layer ` +
      `(${layerBlocks.length}), got ${sensorLines.length}`);
  }
  for (const sl of sensorLines) {
    if (/&(?:trans|none)(?![\w-])/.test(sl)) {
      problems.push(`sensor-bindings &trans/&none rejected by ZMK v0.3 ` +
        `(its node "lacks #sensor-binding-cells"): ${sl.trim()}`);
    }
  }
  if (layerBlocks.length !== 3) {
    problems.push(`want exactly 3 layers (default + lower + L2 raise ` +
      `placeholder), got ${layerBlocks.length}`);
  }
  for (const [i, got] of layerBlocks.entries()) {
    if (got.length !== rcs.length) {
      problems.push(`layer ${i}: ${got.length} bindings vs ${rcs.length} map positions`);
    }
    const expArr = [exp, PLACEHOLDER, PLACEHOLDER][i];
    if (expArr && got.length === rcs.length) {
      const want = expArr.join("\u0000");
      if (got.join("\u0000") !== want) {
        for (let j = 0; j < rcs.length; j++) {
          if (got[j] !== expArr[j]) {
            problems.push(`layer ${i} position ${j} is RC(${rcs[j][0]},${rcs[j][1]})=` +
              ` got ${got[j]}, want ${exp[j]}`);
            break;
          }
        }
      }
    }
  }
  for (const [r, c] of rcs) {
    if (r >= rows || c >= cols) {
      problems.push(`RC(${r},${c}) outside ${rows}x${cols} span`);
      break;
    }
  }
  const rovl = strip(d("boards/shields/hojicha44/hojicha44_right.overlay"));
  const off = /col-offset\s*=\s*<(\d+)>/.exec(rovl);
  if (!off) {
    problems.push("right overlay missing col-offset");
  } else {
    // right half populates the left's shape mirrored: full rows 0-2 plus
    // the 4 populated thumbs (r3c0-3); RC(3,10..11) intentionally omitted
    for (let r = 0; r < 3; r++) {
      for (let c = 0; c < 6; c++) {
        if (!have(r, c + +off[1])) problems.push(`RC(${r},${c + +off[1]}) missing from map`);
      }
    }
    for (let c = 0; c < 4; c++) {
      if (!have(3, c + +off[1])) problems.push(`RC(3,${c + +off[1]}) missing from map`);
    }
  }
  for (const f of ["boards/shields/hojicha44/hojicha44_left.overlay",
    "boards/shields/hojicha44/hojicha44_right.overlay",
    "boards/shields/hojicha44/hojicha44.dtsi"]) {
    if (/wired-split|wired_split/.test(strip(d(f)))) problems.push(`${f} still enables wired split`);
  }
  const conf = strip(d("config/hojicha44.conf"));
  if (/SPLIT_WIRED/.test(conf)) problems.push("conf still sets SPLIT_WIRED");
  if (!/CONFIG_ZMK_BLE=y/.test(conf)) problems.push("conf missing BLE");
  // the VALUE matters, not just the presence: a flipped diode-direction
  // reads the matrix backwards while every presence check still passes
  // (3-review audit 2026-10-21)
  if (!/diode-direction\s*=\s*"col2row"/.test(dtsi))
    problems.push('dtsi diode-direction is not "col2row" (the matrix is ' +
      'read backwards if flipped)');
  // Encoder setup gate (EC11E15244G1: 30 detents = 15 pulses per rev;
  // ZMK `steps` semantics count PULSES per revolution, not detents —
  // assert both fields against the vendored part).
  const steps = /steps\s*=\s*<(\d+)>/.exec(dtsi);
  if (!steps || +steps[1] !== 15) {
    problems.push(`dtsi: encoder steps ${steps ? steps[1] : "missing"} ` +
      "!= 15 (pulses/rev)");
  }
  const trig = /triggers-per-rotation\s*=\s*<(\d+)>/.exec(dtsi);
  if (!trig || +trig[1] !== 30) {
    problems.push(`dtsi: triggers-per-rotation ${trig ? trig[1] : "missing"}` +
      " != 30 (detents)");
  }
  if (problems.length) fail("zmk-structure", problems.slice(0, 4).join("; "));
  else ok(`zmk-structure (${rcs.length} positions, ${layerBlocks.length} layers, ` +
    `binding order verified, BLE-only)`);
} catch (e) {
  fail("zmk-structure", e.message);
}

// N. case<->plate stack ties (M7 review: these constants live in two
// generators and could drift apart silently)
{
  const rd = (f, re) => {
    const m = fs.readFileSync(path.join(REPO, f), "utf8").match(re);
    if (!m) throw new Error(`${f}: /${re.source}/ not found`);
    return parseFloat(m[1]);
  };
  try {
    const gap = rd("plate/gen_plate.py", /^GAP = ([\d.]+)/m);
    const pt = rd("plate/gen_plate.py", /^PLATE_THICK = ([\d.]+)/m);
    const under = rd("case/params.py", /^PLATE_UNDER = ([\d.]+)/m);
    const lip = rd("case/params.py", /^TOP_LIP_Z = ([\d.]+)/m);
    const ct = rd("case/params.py", /^COVER_T = ([\d.]+)/m);
    const cmd = rd("case/params.py", /^COVER_MAG_DEPTH = ([\d.]+)/m);
    // Post-audit round: more cross-generator ties that could drift.
    const tabwP = rd("plate/gen_plate.py", /^TAB_W = ([\d.]+)/m);
    const tabwC = rd("case/params.py", /^TAB_W = ([\d.]+)/m);
    const tablP = rd("plate/gen_plate.py", /^TAB_L = ([\d.]+)/m);
    const tablC = rd("case/params.py", /^TAB_L = ([\d.]+)/m);
    const antP = rd("pcb/generators/gen_pcb.py", /^ANT_R_MM = ([\d.]+)/m);
    const antC = rd("case/params.py", /^ANT_R_MM = ([\d.]+)/m);
    const mag = rd("case/params.py", /^MAG_DIA = ([\d.]+)/m);
    const band = rd("case/params.py", /^MAG_STATION_BAND = ([\d.]+)/m);
    const problems = [];
    if (tabwP !== tabwC)
      problems.push(`TAB_W ${tabwP} (plate) != ${tabwC} (case params)`);
    if (tablP !== tablC)
      problems.push(`TAB_L ${tablP} (plate) != ${tablC} (case params)`);
    if (Math.abs(antP - antC) > 1e-9)
      problems.push(`ANT_R_MM ${antP} (gen_pcb) != ${antC} (case params)`);
    // ABSOLUTE web floor (the reviewer floor). The derived value shrinks
    // with the band it polices, so it cannot catch a thinner pocket —
    // the floor is pinned here (3-review audit 2026-10-21).
    if ((band - mag) / 2 < 1.6)
      problems.push(`magnet web (band ${band} - dia ${mag})/2 = ` +
        `${((band - mag) / 2).toFixed(2)} < 1.60 (absolute reviewer floor)`);
    if (Math.abs(gap - under) > 1e-9)
      problems.push(`GAP ${gap} != PLATE_UNDER ${under}`);
    if (Math.abs(lip - (under + pt + 2.5)) > 1e-9)
      problems.push(`TOP_LIP_Z ${lip} != PLATE_UNDER+PLATE_THICK+2.5 ` +
        `(${(under + pt + 2.5).toFixed(2)})`);
    if (ct - cmd < 1.2)
      problems.push(`cover pocket floor ${ct - cmd} < 1.2 (M4 fix)`);
    if (problems.length) fail("stack-ties", problems.join("; "));
    else ok(`stack-ties (GAP=${gap}, plate ${pt}, lip ${lip}, ` +
      `cover floor ${(ct - cmd).toFixed(1)})`);
  } catch (e) {
    fail("stack-ties", e.message);
  }
}

console.log(failures ? `\n${failures} check(s) FAILED` : "\nall static checks pass");
process.exit(failures ? 1 : 0);
