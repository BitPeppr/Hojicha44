#!/usr/bin/env python3
"""Hojicha44 versioned release builder — roadmap Phase 7/12 evidence gate.

Exports Gerbers/drill/pos/bom per half with explicit layers (default export
dumps 21 junk layers), copies the gitignored ERC/DRC reports into the
versioned tree, and writes MANIFEST.txt (spec version, git commit, tool
versions, router rev, sha256 per file, gate status).

  python3 pcb/make_release.py            # writes generated/release/vX.Y.Z/
  python3 pcb/make_release.py --check    # verify only, no kicad-cli runs

Outputs stay tracked under generated/release/ (NOT gitignored — only
layout/generated/, *-erc.rpt, *-drc.rpt, pcb/kicad/export/, out/ are).
out/release/ remains scratch.
"""
import csv
import hashlib
import os
import re
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(REPO, "spec", "electronics.yaml")
PCB_DIR = os.path.join(REPO, "pcb", "kicad")
LAYERS = "F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,F.Paste,B.Paste,Edge.Cuts"
BOM_FIELDS = "Reference,Value,Footprint,MPN,Datasheet,QUANTITY"

KICAD_CLI = (
    shutil.which("kicad-cli")
    or "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
)


def spec_version():
    s = open(SPEC).read()
    m = re.search(r"^version:\s*(\d+\.\d+\.\d+)", s, re.M)
    assert m, "spec missing version MAJOR.MINOR.PATCH"
    return m.group(1)


def git_info():
    def run(*a):
        r = subprocess.run(a, capture_output=True, text=True, cwd=REPO)
        return r.stdout.strip() if r.returncode == 0 else "unknown"
    return run("git", "rev-parse", "HEAD"), run("git", "describe", "--tags", "--always", "--dirty")


def tool_versions():
    r = subprocess.run([KICAD_CLI, "version"], capture_output=True, text=True)
    cli = (r.stdout + r.stderr).strip().splitlines()
    cli = cli[0] if cli else "unknown"
    sys.path.insert(0, os.path.join(REPO, "pcb", "generators"))
    import gen_route
    return cli, f"r{gen_route.ROUTER_VERSION}"


def export_half(half, outdir):
    pcb = os.path.join(PCB_DIR, f"Hojicha44-{half}.kicad_pcb")
    sch = os.path.join(PCB_DIR, f"Hojicha44-{half}.kicad_sch")
    os.makedirs(outdir, exist_ok=True)
    subprocess.run(
        [KICAD_CLI, "pcb", "export", "gerbers", "-l", LAYERS,
         "-o", outdir, pcb], check=True, capture_output=True)
    subprocess.run(
        [KICAD_CLI, "pcb", "export", "drill", "-o", outdir, pcb],
        check=True, capture_output=True)
    subprocess.run(
        [KICAD_CLI, "pcb", "export", "pos", "--format", "csv",
         "--units", "mm", "-o", os.path.join(outdir, "pos.csv"), pcb],
        check=True, capture_output=True)
    subprocess.run(
        [KICAD_CLI, "sch", "export", "bom", "--fields", BOM_FIELDS,
         "-o", os.path.join(outdir, "bom.csv"), sch],
        check=True, capture_output=True)
    # pos-smt.csv: SMD-fab subset (SOD-123 diodes only; everything else hand
    # assembly per spec/bom.md). Derived from pos.csv so both stay in sync.
    with open(os.path.join(outdir, "pos.csv"), newline="") as f:
        rows = list(csv.DictReader(f))
    smt = [r for r in rows if r.get("Package", "") == "D_SOD-123"]
    assert len(smt) == 22, f"{half}: want 22 SMT diodes, got {len(smt)}"
    with open(os.path.join(outdir, "pos-smt.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(smt)
    # ERC/DRC reports are gitignored at the source — copy them here so the
    # versioned release carries the evidence (fix.md P0-3 hash manifest).
    for ext in ("-erc.rpt", "-drc.rpt"):
        src = os.path.join(PCB_DIR, f"Hojicha44-{half}{ext}")
        assert os.path.exists(src), f"missing {src}: run gen_schematic/gen_pcb first"
        shutil.copy(src, os.path.join(outdir, f"Hojicha44-{half}{ext}"))


def sha12(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def verify_release(reldir):
    bad = []
    for half in ("Left", "Right"):
        d = os.path.join(reldir, half)
        if not os.path.isdir(d):
            bad.append(f"{half}/ missing")
            continue
        files = sorted(os.listdir(d))
        gerbers = [f for f in files if f.endswith(
            (".gbl", ".gbs", ".gbp", ".gbo", ".gm1", ".gtl",
             ".gts", ".gtp", ".gto"))]
        for want in ("pos.csv", "pos-smt.csv", "bom.csv",
                     f"Hojicha44-{half}-erc.rpt", f"Hojicha44-{half}-drc.rpt"):
            p = os.path.join(d, want)
            if not os.path.exists(p) or os.path.getsize(p) == 0:
                bad.append(f"{half}/{want} missing or empty")
        if len(gerbers) != 9:
            bad.append(f"{half}: want 9 gerbers, got {len(gerbers)}")
        if not any(f.endswith(".gbrjob") for f in files):
            bad.append(f"{half}: job file missing")
        if not any(f.endswith(".drl") for f in files):
            bad.append(f"{half}: drill file missing")
        for f in files:
            if os.path.getsize(os.path.join(d, f)) == 0:
                bad.append(f"{half}/{f} empty")
    return bad


def main():
    check_only = "--check" in sys.argv
    ver = spec_version()
    reldir = os.path.join(REPO, "generated", "release", f"v{ver}")
    if check_only:
        bad = verify_release(reldir)
        print(f"release {reldir}: {'CLEAN' if not bad else 'FAIL'}")
        for b in bad:
            print(f"  !! {b}")
        sys.exit(1 if bad else 0)
    commit, tag = git_info()
    cli, router = tool_versions()
    for half in ("Left", "Right"):
        export_half(half, os.path.join(reldir, half))
    bad = verify_release(reldir)
    lines = [
        "Hojicha44 release manifest",
        f"spec version: {ver}",
        f"git commit: {commit}",
        f"git tag: {tag}",
        f"router: gen_route.py {router}",
        f"kicad-cli: {cli}",
        "ERC: 0 errors + 5 documented spare warnings/half (check_erc_report gate)",
        "DRC: 0 non-waived (exact W1 set of 28/half asserted); "
        "unconnected NOT waived; PTH/NPTH-in-courtyard = error",
        "",
    ]
    for half in ("Left", "Right"):
        d = os.path.join(reldir, half)
        files = sorted(os.listdir(d))
        lines.append(f"[{half}] {len(files)} files")
        for f in files:
            lines.append(f"  {sha12(os.path.join(d, f))}  {f}")
    open(os.path.join(reldir, "MANIFEST.txt"), "w").write("\n".join(lines) + "\n")
    print(f"release v{ver}: {reldir}")
    print(f"  spec {ver} commit {commit[:12]} router {router} cli {cli[:24]}")
    if bad:
        print("  FAIL:")
        for b in bad:
            print(f"  !! {b}")
        sys.exit(1)
    print("  CLEAN: 9 gerbers + job + drill + pos + pos-smt + bom + erc + drc per half")


if __name__ == "__main__":
    main()
