/* Hojicha44 static repo checks — no KiCad needed (runs in CI).
 * Covers the doc/gate regressions that previously shipped silently:
 *  - spec/electronics.yaml parses + erc stanza states the exact gate
 *  - Ergogen TRRS comment matches measured 22.40/20.42/recessed geometry
 *  - gen_schematic.py NEED has no duplicate (lib, symbol) entries
 *  - gen_pcb.py W1 gate asserts the exact 28-entry mismatch set, verified
 *    against the TRACKED release DRC copies (generated/release/vX.Y.Z/)
 *  - release MANIFEST exists for the spec version and lists both halves
 *  - ZMK structure: transform map RC count == keymap bindings per layer,
 *    every RC inside the columns/rows span, right-half col-offset covered,
 *    BLE-only (no wired-split node, no SPLIT_WIRED), diode-direction set
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
  const pairs = [...src.matchAll(/\("([^"]+\.kicad_sym)",\s*"([^"]+)",/g)].map(
    (m) => `${m[1]}:${m[2]}`
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
  const layers = [...body.matchAll(/(?<!sensor-)bindings\s*=\s*<([\s\S]*?)>/g)]
    .map((m) => (m[1].match(/&[A-Za-z][\w-]*/g) || []).length);
  const problems = [];
  if (layers.length < 1) problems.push("no layer bindings blocks found");
  for (const [i, n] of layers.entries()) {
    if (n !== rcs.length) {
      problems.push(`layer ${i}: ${n} bindings vs ${rcs.length} map positions`);
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
  if (!/diode-direction/.test(dtsi)) problems.push("dtsi missing diode-direction");
  if (problems.length) fail("zmk-structure", problems.slice(0, 4).join("; "));
  else ok(`zmk-structure (${rcs.length} positions, ${layers.length} layers, BLE-only)`);
} catch (e) {
  fail("zmk-structure", e.message);
}

console.log(failures ? `\n${failures} check(s) FAILED` : "\nall static checks pass");
process.exit(failures ? 1 : 0);
