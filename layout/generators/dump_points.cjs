#!/usr/bin/env node
/**
 * Ergogen 4.2.1 only writes DXF (and SVG with --svg): the `points.yaml`,
 * `units.yaml`, `source/canonical.yaml` and `outlines/*.yaml` sidecars that
 * older Ergogen versions used to emit are gone. This script reproduces them
 * through the ergogen API so the intermediate geometry stays readable and
 * diffable:
 *
 *   node layout/generators/dump_points.cjs
 *
 * Writes into layout/generated/v2 (same place the CLI writes its output).
 */
const fs = require("fs");
const path = require("path");
const yaml = require("js-yaml");

const REPO = path.resolve(__dirname, "..", "..");
const SRC = path.join(REPO, "layout", "ergogen");
const OUT = path.join(REPO, "layout", "generated", "v2");

const ergogen = require(path.join(REPO, "node_modules", "ergogen", "src", "ergogen"));

// Ergogen's result tree mirrors the web UI's file tree:
//   { raw, canonical, units, points, demo: {dxf,yaml,svg}, outlines: {<name>: {...}} }
(async () => {
  const configText = fs.readFileSync(path.join(SRC, "config.yaml"), "utf8");

  const results = await ergogen.process(
    configText,
    { debug: true, svg: true },
    (m) => {}
  );

  const write = (rel, data) => {
    const p = path.join(OUT, rel);
    fs.mkdirSync(path.dirname(p), { recursive: true });
    fs.writeFileSync(p, typeof data === "string" ? data : yaml.dump(data));
    return rel;
  };

  if (results.canonical) write("source/canonical.yaml", results.canonical);
  if (results.units) {
    write("points/units.yaml", results.units);
  }
  if (results.points) {
    write("points/points.yaml", results.points);
  }

  for (const [name, outline] of Object.entries(results.outlines || {})) {
    if (outline.yaml !== undefined) {
      write(`outlines/${name}.yaml`, outline.yaml);
    }
  }

  console.log(
    Object.keys(results.outlines || {}).length + " outline sidecars into " +
      "layout/generated/v2"
  );
})().catch((e) => {
  console.error(e);
  process.exit(1);
});
