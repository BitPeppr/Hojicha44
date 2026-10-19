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
import glob
import json
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


def board_commit():
    """Last commit that touched board-affecting sources. A release cut at
    an older commit is stale by definition (gerbers predate the boards)."""
    def run(*a):
        r = subprocess.run(a, capture_output=True, text=True, cwd=REPO)
        return r.stdout.strip().splitlines()[0] if r.returncode == 0 and \
            r.stdout.strip() else "unknown"
    return run("git", "log", "-1", "--format=%H", "--",
               "pcb/kicad", "pcb/generators", "pcb/make_release.py",
               "spec/electronics.yaml")


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
    # KiCad 10 writes Finish: "None"; stamp the decided board finish so
    # CAM readers don't get a hole (first-article decision: ENIG). The
    # reader-visible field is GeneralSpecs.Finish — a top-level Finish is
    # off-spec noise that fab parsers ignore (the point of the stamp).
    for jb in glob.glob(os.path.join(outdir, "*.gbrjob")):
        with open(jb) as f:
            job = json.load(f)
        gs = job.get("GeneralSpecs") or {}
        if gs.get("Finish") in (None, "", "None"):
            gs["Finish"] = "ENIG"
            job["GeneralSpecs"] = gs
            with open(jb, "w") as f:
                json.dump(job, f, indent=2)
                f.write("\n")
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
    # audit P0-1 (export ordering): the cut gates on the SAME reports the
    # generators produced — a failing or stale report must not ride
    # beside fresh gerbers just because the file exists
    sys.path.insert(0, os.path.join(REPO, "pcb", "generators"))
    import gen_pcb as _gp
    import gen_schematic as _gs
    drc_rc = _gp.check_drc_report(
        os.path.join(outdir, f"Hojicha44-{half}-drc.rpt"), half[0])
    erc_rc = _gs.check_erc_report(
        os.path.join(outdir, f"Hojicha44-{half}-erc.rpt"), half[0])
    if drc_rc or erc_rc:
        sys.exit(f"release cut refused: {half} report gate failed "
                 f"(drc rc={drc_rc}, erc rc={erc_rc})")


def sha12(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()[:12]


def manifest_lines(reldir):
    man = os.path.join(reldir, "MANIFEST.txt")
    if not os.path.exists(man):
        return []
    return open(man).read().splitlines()


def manifest_value(lines, key):
    """Value of 'key: value' manifest header line, or None."""
    for l in lines:
        if l.startswith(f"{key}: "):
            return l.split(f"{key}: ", 1)[1].strip()
    return None


def verify_release(reldir, with_manifest=True):
    """with_manifest=True (--check/CI): hashes + commit currency + scope.
    with_manifest=False (mid-build): structure only, manifest not written yet."""
    bad = []
    lines = manifest_lines(reldir)
    if with_manifest and not lines:
        return ["MANIFEST.txt missing or empty"]
    if with_manifest:
        tops = sorted(os.listdir(reldir))
        if tops != ["Left", "MANIFEST.txt", "Right"]:
            bad.append(f"unexpected release top-level: {tops} (clean-cut only)")
    # every listed file must still hash to its manifest sha12 (the manifest
    # is the tamper evidence; eb6678f was caught shipping stale gerbers
    # beside a re-pointed manifest exactly because nothing re-verified)
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
            p = os.path.join(d, f)
            if os.path.getsize(p) == 0:
                bad.append(f"{half}/{f} empty")
        if with_manifest:
            listed = {}
            started = False
            for l in lines:
                if l.startswith(f"[{half}]"):
                    started = True
                    continue
                if started and l.startswith("["):
                    break
                if started:
                    m = re.match(r"^  ([0-9a-f]{12})  (\S+)$", l)
                    if not m:
                        bad.append(f"{half}: unparseable manifest line {l!r}")
                        continue
                    listed[m.group(2)] = m.group(1)
            if len(listed) != len(files):
                bad.append(f"{half}: manifest lists {len(listed)} files, "
                           f"dir has {len(files)}")
            for f, want_hash in listed.items():
                if not os.path.exists(os.path.join(d, f)):
                    bad.append(f"{half}/{f} in manifest but missing on disk")
                    continue
                got_hash = sha12(os.path.join(d, f))
                if got_hash != want_hash:
                    bad.append(f"{half}/{f} hash {got_hash} != manifest "
                               f"{want_hash} (stale content or edited artifact)")
            for f in files:
                if f not in listed:
                    bad.append(f"{half}/{f} on disk but not in manifest")
    # the manifest must claim the CURRENT board-affecting commit, else the
    # gerbers were exported from older boards
    if with_manifest:
        head = board_commit()
        cmt = manifest_value(lines, "git commit")
        if cmt != head:
            bad.append(f"manifest commit {cmt} != board-affecting HEAD {head} "
                       f"(- boards changed since the cut; re-run make_release)")
    return bad


def main():
    check_only = "--check" in sys.argv
    ver = spec_version()
    reldir = os.path.join(REPO, "generated", "release", f"v{ver}")
    bhead = board_commit()
    if check_only:
        bad = verify_release(reldir)
        print(f"release {reldir}: "
              f"{'CLEAN' if not bad else 'FAIL'} (boards @{bhead[:12]})")
        for b in bad:
            print(f"  !! {b}")
        sys.exit(1 if bad else 0)
    # refuse a dirty tree: the manifest certifies committed sources only.
    # Untracked junk cannot be referenced by any generator input, so it
    # only warrants a note; a modified tracked file would silently ship.
    st = subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                        text=True, cwd=REPO).stdout.splitlines()
    mod = [l for l in st if not l.startswith("??")]
    if mod:
        sys.exit("release cut refused: committed tree is dirty "
                 "(commit first — the manifest certifies committed "
                 "sources):\n" + "\n".join(mod[:12]))
    if st:
        print(f"  note: {len(st)} untracked file(s) present (not certified)")
    # clean cut: no stale artifacts from previous exports can survive
    # beside the new ones (a half-updated tree shipped exactly that way
    # once — drill+manifest refreshed, gerbers not)
    if os.path.isdir(reldir):
        shutil.rmtree(reldir)
    cli, router = tool_versions()
    for half in ("Left", "Right"):
        export_half(half, os.path.join(reldir, half))
    bad = verify_release(reldir, with_manifest=False)
    if bad:  # surface BEFORE hashing so a broken cut never self-certifies
        print(f"release v{ver}: export FAILED:")
        for b in bad:
            print(f"  !! {b}")
        sys.exit(1)
    lines = [
        "Hojicha44 release manifest",
        f"spec version: {ver}",
        # commit the boards were exported from (NOT repo HEAD — case, docs
        # and firmware commits must not flag the release stale)
        f"git commit: {bhead}",
        f"git tag: {git_info()[1]}",
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
    print(f"  spec {ver} boards @{bhead[:12]} router {router} cli {cli[:24]}")
    print("  CLEAN: 9 gerbers + job + drill + pos + pos-smt + bom + erc + drc per half")


if __name__ == "__main__":
    main()
