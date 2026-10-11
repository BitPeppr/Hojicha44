// Render a labeled layout PNG (+SVG) from a KLE json.
// Uses only magick-safe SVG (rects/polygons, no text/transforms); labels are
// added with `magick -annotate` using an explicit TTF (no system fonts needed).
//
// Usage (from repo root):
//   node layout/generators/render_preview.mjs [kle.json] [out stem]
// Defaults: layout/iterations/keyboard_layout_v2.json -> layout/generated/v2/preview
import { execFileSync } from 'child_process';
import fs from 'fs';
import os from 'os';

const klePath = process.argv[2] || 'layout/iterations/keyboard_layout_v2.json';
const outStem = process.argv[3] || 'layout/generated/v2/keymap';
const raw = JSON.parse(fs.readFileSync(klePath, 'utf8'));

// --- minimal KLE walk (mirrors kle-serial cursor semantics) ---
const keys = [];
let cy = 0, prx = 0, pry = 0, pr = 0;
for (const row of raw) {
  if (!Array.isArray(row)) continue;
  let cx = prx, rx = prx, ry = pry, r = pr, w = 1, h = 1;
  for (const it of row) {
    if (typeof it === 'string') {
      keys.push({ x: cx, y: cy, w, h, r, rx, ry, label: it });
      cx += w; w = 1; h = 1;
    } else {
      if (it.rx != null) { rx = it.rx; cx = rx; cy = it.ry != null ? it.ry : cy; }
      if (it.ry != null) { ry = it.ry; cx = it.rx != null ? it.rx : cx; cy = ry; }
      if (it.r != null) r = it.r;
      if (it.x) cx += it.x;
      if (it.y) cy += it.y;
      if (it.w) w = it.w;
      if (it.h) h = it.h;
    }
  }
  cy += 1; prx = rx; pry = ry; pr = r;
}

// --- geometry helpers (KLE units, y down) ---
const rot = (px, py, cx, cy, deg) => {
  // NOTE: no negation. KLE/canvas positive angles render clockwise on
  // screen, which in y-down coords is exactly math R(+deg). Negating here
  // mirrors every rotated cap and fabricates overlaps (seen before).
  const t = deg * Math.PI / 180, c = Math.cos(t), s = Math.sin(t);
  const dx = px - cx, dy = py - cy;
  return [cx + dx * c - dy * s, cy + dx * s + dy * c];
};
for (const k of keys) {
  k.cx = k.r ? k.rx : k.x + k.w / 2;
  k.cy = k.r ? k.ry : k.y + k.h / 2;
  const hw = k.w / 2, hh = k.h / 2;
  k.corners = [[-hw, -hh], [hw, -hh], [hw, hh], [-hw, hh]]
    .map(([dx, dy]) => rot(k.cx + dx, k.cy + dy, k.cx, k.cy, k.r || 0));
}
let minx = 1e9, maxx = -1e9, miny = 1e9, maxy = -1e9;
for (const k of keys) for (const [x, y] of k.corners) {
  minx = Math.min(minx, x); maxx = Math.max(maxx, x);
  miny = Math.min(miny, y); maxy = Math.max(maxy, y);
}
const PAD = 0.6, S = 1600 / (maxx - minx + PAD * 2);
const OX = -minx + PAD, OY = -miny + PAD;
const X = x => (x + OX) * S, Y = y => (y + OY) * S;
const W = Math.ceil((maxx - minx + PAD * 2) * S), H = Math.ceil((maxy - miny + PAD * 2) * S);

const capFill = k => /^(Space|Enter)$/.test(k.prim) ? '#bcd6f5'
  : /^(L1|L2|Cmd|Ctrl|Opt|Shift|Alt|Tab|Esc|Func)$/.test(k.prim) ? '#c9c9d2'
  : k.prim === 'Enc' ? '#f5cf9a' : '#ececf0';
for (const k of keys) {
  const lines = k.label.split('\n').map(s => s.trim()).filter(Boolean);
  k.prim = lines[0] || '';
  k.sub = lines.slice(1, 3).join(' ');
}

const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
let svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}">` +
  `<rect width="${W}" height="${H}" fill="#232328"/>`;
for (const k of keys) {
  const pts = k.corners.map(([x, y]) => `${X(x).toFixed(1)},${Y(y).toFixed(1)}`).join(' ');
  svg += `<polygon points="${pts}" fill="${capFill(k)}" stroke="#101014" stroke-width="${Math.max(1, S * 0.02).toFixed(1)}"/>`;
}
for (const k of keys) {
  if (!k.prim) continue;
  const cx = X(k.cx), cy = Y(k.cy);
  const safe = s => esc(s).slice(0, 24);
  svg += `<text x="${cx.toFixed(1)}" y="${(cy - (k.sub ? S * 0.08 : 0)).toFixed(1)}" font-size="${Math.round(S * 0.30)}" text-anchor="middle" dominant-baseline="central" font-family="sans-serif" fill="#1a1a1e">${safe(k.prim)}</text>`;
  if (k.sub) svg += `<text x="${cx.toFixed(1)}" y="${(cy + S * 0.22).toFixed(1)}" font-size="${Math.round(S * 0.15)}" text-anchor="middle" dominant-baseline="central" font-family="sans-serif" fill="#1a1a1e">${safe(k.sub)}</text>`;
}
svg += '</svg>';
fs.writeFileSync(outStem + '.svg', svg);

// --- rasterize a text-free copy (magick's SVG engine can't do fonts),
// then annotate labels (upright text always) ---
const png = outStem + '.png';
const rasterSrc = outStem + '.notext.svg';
fs.writeFileSync(rasterSrc, svg.replace(/<text.*?<\/text>/g, ''));
execFileSync('magick', [rasterSrc, '-background', '#232328', '-flatten', png]);
fs.unlinkSync(rasterSrc);

const home = os.homedir();
const fontCandidates = [
  `${home}/Library/Fonts/HackNerdFont-Regular.ttf`,
  '/System/Library/Fonts/Helvetica.ttc',
];
let font = null;
for (const f of fontCandidates) {
  try { fs.accessSync(f); font = f; break; } catch { /* next */ }
}
if (!font) { console.log('no usable font found; wrote SVG only:', outStem + '.svg'); process.exit(0); }
const args = [png, '-font', font, '-fill', '#1a1a1e', '-gravity', 'None'];
const textW = (s, ps) => ps * 0.58 * [...s].length;
for (const k of keys) {
  if (!k.prim) continue;
  const cx = X(k.cx), cy = Y(k.cy);
  const safe = s => (s.startsWith('@') ? '(at)' + s.slice(1) : s).slice(0, 24);
  const ps1 = Math.round(S * 0.30);
  args.push('-pointsize', String(ps1),
    '-annotate', `+${Math.round(cx - textW(k.prim, ps1) / 2)}+${Math.round(cy + ps1 * 0.35 - (k.sub ? S * 0.08 : 0))}`, safe(k.prim));
  if (k.sub) {
    const ps2 = Math.round(S * 0.15);
    args.push('-pointsize', String(ps2),
      '-annotate', `+${Math.round(cx - textW(k.sub, ps2) / 2)}+${Math.round(cy + ps2 * 0.35 + S * 0.22)}`, safe(k.sub));
  }
}
args.push(png);
execFileSync('magick', args);
console.log('wrote', outStem + '.svg', '+', png, `(${W}x${H})`);
