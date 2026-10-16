#!/usr/bin/env python3
"""Hojicha44 renders — the one canonical set. Pictures only.

Per half, exactly three files in pcb/kicad/export/:
  Hojicha44-{half}-top.png       bare board, orthographic top
  Hojicha44-{half}-bottom.png    bare board, orthographic bottom
  Hojicha44-{half}-populated-iso.png  iso with everything
      (switch bodies in sockets + all board models: encoder, MCU
      envelope, TRRS, JST, slide switch)

The repo board files carry NO switch bodies (switches plug into the
hotswap sockets; they are not PCB parts). The iso build uses throwaway
/tmp board copies with one dummy top-side footprint per switch, each
linking the community Kailh Choc V1 model; the repo tree is never
touched.

  Switch model: koktoh/keyswitch_model, Choc V1 Red
  (master/choc/v1/KiCad/red.wrl, StepUp-exported, same pipeline as our
  verified socket model). Measured 15.0 x 15.0 x 11.0mm = the published
  PG1350 15*15*11 profile exactly. Red = representative render variant
  only; the BOM leaves linear/tactile/clicky to the builder.
  Sockets live on B.Cu; dummies go on F.Cu at the same (x, y, rot) so
  bodies sit centered over their sockets with pins down.

  python3 pcb/render.py [all|iso|bare] [Left|Right]
      defaults: all halves, everything
  Iso camera looks from the thumb-cluster (south) side:
  --rotate '-50,0,205', no post-flip. (The old '-50,0,25' + sips -r 180
  looked from the number-row side; Z+180 absorbs the 180.)
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB_DIR = os.path.join(REPO, "pcb", "kicad")
EXPORT_DIR = os.path.join(PCB_DIR, "export")
TMP = tempfile.mkdtemp(prefix="hojicha-render-")

MODEL_URL = ("https://raw.githubusercontent.com/koktoh/keyswitch_model"
             "/master/choc/v1/KiCad/red.wrl")
MODEL_PATH = os.path.join(TMP, "choc_red_v1.wrl")

KICAD_CLI = (
    __import__("shutil").which("kicad-cli")
    or "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
)

SIZE = ['--width', '1992', '--height', '1409', '--quality', 'high']


def ensure_model():
    if not os.path.exists(MODEL_PATH):
        print(f'downloading {MODEL_URL}')
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
    assert os.path.getsize(MODEL_PATH) > 100000, \
        f'switch model download failed ({MODEL_PATH})'


def sw_instances(pcb_path):
    """(ref, x, y, rot) for every Choc socket instance."""
    lines = open(pcb_path).read().splitlines()
    out = []
    fp = at = None
    libref = None
    for i, ln in enumerate(lines):
        m = re.match(r'\s*\(footprint "([^"]+)"', ln)
        if m:
            libref, fp, at = m.group(1), m.group(1), None
            for k in range(i, min(i + 10, len(lines))):
                a = re.match(r'\s*\(at (-?[\d.]+) (-?[\d.]+)( -?[\d.]+)?',
                             lines[k])
                if a:
                    at = (float(a.group(1)), float(a.group(2)),
                          float(a.group(3) or 0))
                    break
        r = re.search(r'\(property "Reference" "(SW_[LR]\d+)"', ln)
        if r and fp and at and 'Hotswap' in libref:
            out.append((r.group(1),) + at)
    assert len(out) == 22, f'want 22 sockets, got {len(out)}'
    return out


def dummy_fp(ref, x, y, rot, n):
    return (
        f'(footprint "SWITCH_DUMMY" (layer "F.Cu") '
        f'(tstamp 00000000-0000-0000-0000-{n:012d})\n'
        f'  (at {x} {y} {rot})\n'
        f'  (property "Reference" "X_{ref}" (at 0 0 0) '
        f'(layer "F.SilkS") '
        f'(tstamp 10000000-0000-0000-0000-{n:012d}))\n'
        f'  (property "Value" "Kailh-Choc-V1-Red" (at 0 0 0) '
        f'(layer "F.Fab") '
        f'(tstamp 20000000-0000-0000-0000-{n:012d}))\n'
        f'  (model "{MODEL_PATH}" (at (xyz 0 0 0)) '
        f'(scale (xyz 1 1 1)) (rotate (xyz 0 0 0)))\n'
        f')\n'
    )


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        print(r.stdout[-2000:])
        print(r.stderr[-2000:])
        raise SystemExit(f'command failed: {cmd[0]}')


def main():
    ensure_model()
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    halves = (sys.argv[2],) if len(sys.argv) > 2 else ('Left', 'Right')
    for half in halves:
        src = os.path.join(PCB_DIR, f'Hojicha44-{half}.kicad_pcb')
        if what in ('all', 'bare'):
            # bare orthos straight off the repo board
            for side, flip in (('top', ['-f', 'vertical']),
                               ('bottom', ['-f', 'vertical'])):
                out = os.path.join(EXPORT_DIR, f'Hojicha44-{half}-{side}.png')
                run([KICAD_CLI, 'pcb', 'render', '--side', side]
                    + SIZE + ['-o', out, src], cwd=REPO)
                if shutil.which("sips"):
                    run(['sips'] + flip + [out], cwd=REPO)
                else:
                    print(f'warning: sips not found, leaving {out} unflipped')
                print(f'{half} bare {side}: {out}')
        if what in ('all', 'iso'):
            # populated iso off a throwaway copy (repo untouched).
            # ${KIPRJMOD} resolves to the BOARD's directory, so a /tmp copy
            # would lose every project-relative model (encoder, sockets,
            # TRRS, nano/switch envelopes) — mirror the 3dshapes dir next
            # to it. Without this the iso silently renders with bodies
            # missing.
            shutil.copytree(os.path.join(PCB_DIR, 'Hojicha44.3dshapes'),
                            os.path.join(TMP, 'Hojicha44.3dshapes'),
                            dirs_exist_ok=True)
            tmp = os.path.join(TMP, f'Hojicha44-{half}-populated.kicad_pcb')
            s = open(src).read().rstrip()
            assert s.endswith(')')
            inst = sw_instances(src)
            dummies = ''.join(dummy_fp(ref, x, y, rot, 1000 + k)
                              for k, (ref, x, y, rot) in enumerate(inst))
            open(tmp, 'w').write(s[:-1] + '\n' + dummies + ')\n')
            out = os.path.join(EXPORT_DIR,
                               f'Hojicha44-{half}-populated-iso.png')
            run([KICAD_CLI, 'pcb', 'render', '--side', 'top']
                + SIZE + ['--perspective', '--rotate', '-50,0,205',
                          '--floor', '-o', out, tmp], cwd=REPO)
            print(f'{half} populated iso: {out} ({len(inst)} switches)')


if __name__ == '__main__':
    main()
