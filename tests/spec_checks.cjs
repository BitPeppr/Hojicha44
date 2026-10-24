/* Hojicha44 static repo checks — no KiCad needed (runs in CI).
 * Covers the doc/gate regressions that previously shipped silently:
 *  - spec/electronics.yaml parses + erc stanza states the exact gate
 *  - Ergogen TRRS comment matches measured 22.40/20.42/recessed geometry
 *  - gen_schematic.py NEED has no duplicate (lib, symbol) entries
 *  - gen_pcb.py W1 gate asserts the exact 28-entry mismatch set, verified
 *    against the TRACKED release DRC copies (generated/release/vX.Y.Z/)
 *  - release MANIFEST exists for the spec version and lists both halves
 *  - ZMK structure: transform map RC count == keymap bindings per layer,
 *    exactly 4 layers (the gen gate), every binding's POSITION against
 *    the row-major interleaved legend signature (the left-then-right
 *    ordering bug can
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

// 5. ZMK structure: map RC count, span + offset coverage, BLE-only
//    transport, diode-direction set — no toolchain needed.  The KEYMAP
//    CONTENT is validated by config/gen_keymap.py's own gate (regenerate
//    + compare + structural checks): the keymap files are GENERATED from
//    spec/layout.yaml, and one source of the rules beats a JS copy that
//    drifted into a 3-layer/PLACEHOLDER world (M3.3 rework).
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
  // all 4 variants + the active one must match spec/layout.yaml; a
  // legend edit without regenerating (or vice versa) fails here.
  execFileSync("python3", [path.join(REPO, "config/gen_keymap.py"), "--check"],
    { stdio: "inherit", cwd: REPO });
  const problems = [];
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
  // Encoder setup gate (EC11E15244G1: 30 detents / 15 ALPS pulse-periods
  // per rev. ZMK v0.3 `steps` counts quadrature DELTAS per radical turn —
  // val = deltas*360/steps in app/module/drivers/sensor/ec11/ec11.c —
  // 15 periods x 4 deltas = 60; in-tree reference sofle uses 80/20 for a
  // 20-detent full-cycle part. Assert both fields against the part).
  const steps = /steps\s*=\s*<(\d+)>/.exec(dtsi);
  if (!steps || +steps[1] !== 60) {
    problems.push(`dtsi: encoder steps ${steps ? steps[1] : "missing"} ` +
      "!= 60 (quadrature deltas/rev = 15 pulse-periods x 4)");
  }
  const trig = /triggers-per-rotation\s*=\s*<(\d+)>/.exec(dtsi);
  if (!trig || +trig[1] !== 30) {
    problems.push(`dtsi: triggers-per-rotation ${trig ? trig[1] : "missing"}` +
      " != 30 (detents)");
  }
  if (problems.length) fail("zmk-structure", problems.slice(0, 4).join("; "));
  else ok(`zmk-structure (${rcs.length} positions, keymap gate CLEAN, ` +
    `BLE-only, col2row)`);
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
    const topFoam = rd("case/params.py", /^TOP_FOAM_T = ([\d.]+)/m);
    const topPreload = rd("case/params.py", /^TOP_PRELOAD = ([\d.]+)/m);
    // PETG strength floor (strength round 2026-10-24): the thinnest
    // structural features must be printable and safe in plain PETG at
    // 100% infill, not only in MJF PA12 (spec/case.md strength section).
    const floorT = rd("case/params.py", /^FLOOR_T\s*=\s*([\d.]+)/m);
    if (parseFloat(floorT) < 1.5)
      problems.push(`FLOOR_T ${floorT} < 1.5 (PETG floor-slab floor)`);
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
    // Thin-top round: the lip follows the 1.5mm TOP foam at TOP_PRELOAD
    // (33%, inside the spec's <=50% ceiling), not a hand-set gap. The
    // literal in params.py is the rounded build value, so allow +-0.01.
    if (Math.abs(lip - (under + pt + topFoam * (1 - topPreload))) > 0.01)
      problems.push(`TOP_LIP_Z ${lip} != PLATE_UNDER+PLATE_THICK+` +
        `TOP_FOAM_T*(1-TOP_PRELOAD) ` +
        `(${(under + pt + topFoam * (1 - topPreload)).toFixed(3)})`);
    if (ct - cmd < 1.2)
      problems.push(`cover pocket floor ${ct - cmd} < 1.2 (M4 fix)`);
    if (problems.length) fail("stack-ties", problems.join("; "));
    else ok(`stack-ties (GAP=${gap}, plate ${pt}, lip ${lip}, ` +
      `cover floor ${(ct - cmd).toFixed(1)})`);
  } catch (e) {
    fail("stack-ties", e.message);
  }
}

// 6. print-order manifest (audit-2 F-12): the shops are sent exactly the
//    files hashed in generated/print/vX.Y.Z/MANIFEST.txt — a tracked plate
//    file that drifted from the manifest must fail the gate (in CI the
//    case/out solids are gitignored and not buildable, so their hashes are
//    order-time records verified only where the files exist locally).
try {
  const crypto = require("crypto");
  const mpath = "generated/print/v0.5.0/MANIFEST.txt";
  const txt = fs.readFileSync(path.join(REPO, mpath), "utf8");
  const entries = new Map();
  for (const line of txt.split("\n")) {
    const m = /^([0-9a-f]{64})\s+(\S+)$/.exec(line);
    if (m) entries.set(m[2], m[1]);
  }
  const problems = [];
  const sha = (f) =>
    crypto.createHash("sha256").update(fs.readFileSync(f)).digest("hex");
  let verifiedPlate = 0, verifiedCase = 0;
  for (const [f, h] of entries) {
    const p = path.join(REPO, f);
    if (!fs.existsSync(p)) {
      if (f.startsWith("plate/"))
        problems.push(`${f} listed in manifest but missing`);
      continue; // gitignored case/out: record-only outside the local tree
    }
    if (sha(p) !== h) problems.push(`${f} drifted from ${mpath}`);
    else if (f.startsWith("case/out/")) verifiedCase += 1;
    else verifiedPlate += 1;
  }
  if (problems.length)
    fail("print-manifest", problems.slice(0, 4).join("; "));
  else ok(`print-manifest (${verifiedPlate} tracked plate files + ` +
    `${verifiedCase} local case solids verified against the order record)`);
} catch (e) {
  fail("print-manifest", e.message);
}

// 7. title-block revision tracks the spec version (audit-3 A-01): the
//    generators derive REV = spec MAJOR.MINOR, so a committed board/sch
//    whose (rev …) lags the spec is exactly the drift A-01 caught — the
//    gate pins the title blocks to the spec on every CI run.
try {
  const ver =
    /^version: ([\d.]+)/m.exec(
      fs.readFileSync(path.join(REPO, "spec/electronics.yaml"), "utf8"))[1];
  const want = ver.split(".").slice(0, 2).join(".");
  const probs = [];
  for (const f of ["pcb/kicad/Hojicha44-Left.kicad_pcb",
                   "pcb/kicad/Hojicha44-Right.kicad_pcb",
                   "pcb/kicad/Hojicha44-Left.kicad_sch",
                   "pcb/kicad/Hojicha44-Right.kicad_sch"]) {
    const txt = fs.readFileSync(path.join(REPO, f), "utf8");
    const m = /\(rev "([^"]*)"\)/.exec(txt);
    if (!m) probs.push(`${f}: no (rev …) in title block`);
    else if (m[1] !== want) probs.push(`${f}: rev ${m[1]} != spec ${want}`);
  }
  if (probs.length) fail("rev-track", probs.join("; "));
  else ok(`rev-track (board/sch title blocks = spec ${want})`);
} catch (e) {
  fail("rev-track", e.message);
}

console.log(failures ? `\n${failures} check(s) FAILED` : "\nall static checks pass");
process.exit(failures ? 1 : 0);
