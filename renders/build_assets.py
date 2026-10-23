#!/usr/bin/env python3
"""Build the render asset pack for Hojicha44 v0.5.0.

Runs in case/.venv (cadquery + ezdxf + trimesh + numpy). Read-only on all
manufacturing artifacts; every output lands under generated/renders/assets/
(a derived, regenerable tree — final renders and scripts are what get
committed).

Outputs:
  assets/board/Hojicha44-{L,R}.glb     PCB assembly, named nodes (kicad-cli
                                       STEP export -> OCCT CAF -> glTF)
  assets/plate/Hojicha44-{L,R}.glb     plate solid extruded from the
                                       tracked DXF (OUTLINE + CUTOUT through,
                                       RELIEF 0.55 pockets in the underside)
  assets/case/{L,R}-{tub,cover}.glb    converted from case/out/ STEPs
  assets/parts/{saddle,saddle_tilted,saddle_homing,normal_tilted,thumb}.glb
                                       KLP Lame keycaps (pinned download)
  assets/parts/knob.glb                procedural EC11 knob (13x13, knurl)
  assets/parts/screw.glb               procedural M2 pan-head
  assets/placements.json               every footprint (ref,x,y,rot) parsed
                                       from the COMMITTED boards — the scene
                                       script's single source for positions
  assets/PROVENANCE.json               tool versions + source hashes
"""
import json
import os
import re
import subprocess
import sys
import hashlib
from shutil import which as _which

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(REPO, "generated", "renders", "assets")
KICAD_CLI = (os.environ.get("KICAD_CLI")
             or _which("kicad-cli")
             or "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli")
KEYCAP_DIR = os.environ.get("KEYCAP_DIR", "/tmp/kbd-renders/keycaps")


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def r2(x):
    return round(float(x), 2)


# ------------------------------------------------------------- PCB -> glb

def export_pcb_step(half, dst):
    args = [KICAD_CLI, "pcb", "export", "step",
            "--include-tracks", "--include-pads", "--include-zones",
            "--include-soldermask", "--include-silkscreen",
            "-f", "-o", dst,
            os.path.join(REPO, "pcb", "kicad", f"Hojicha44-{half}.kicad_pcb")]
    r = subprocess.run(args, capture_output=True, text=True)
    # kicad-cli exits 2 when VRML component models cannot embed in STEP
    # ("Cannot use VRML models when exporting to non-mesh formats") while
    # still writing the file — the sockets/nano/slide-switch envelopes are
    # VRML, and they are hidden under the plate in renders anyway. The
    # artifact existing is the contract; the return code is not.
    if r.returncode != 0 and not (os.path.exists(dst)
                                  and os.path.getsize(dst) > 1_000_000):
        sys.exit(f"kicad-cli STEP export failed for {half}:\n{r.stderr[-800:]}")
    if r.returncode != 0:
        print("    (VRML component models skipped by kicad-cli — expected)")
    print(f"  pcb step: {dst} ({os.path.getsize(dst) // 1024} KiB)")


def step_to_named_glb(step_path, glb_path, tess_tol=0.12):
    """Convert a STEP (possibly multi-solid, KiCad-named) to glTF with named
    nodes. Uses OCCT's CAF reader so footprint reference names survive."""
    from OCP.STEPCAFControl import STEPCAFControl_Reader
    from OCP.TDocStd import TDocStd_Document
    from OCP.TCollection import TCollection_ExtendedString
    from OCP.XCAFDoc import XCAFDoc_DocumentTool
    from OCP.TDF import TDF_LabelSequence
    from OCP.TDataStd import TDataStd_Name
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location
    import trimesh
    import numpy as np

    doc = TDocStd_Document(TCollection_ExtendedString("kbddoc"))
    reader = STEPCAFControl_Reader()
    reader.SetNameMode(True)
    reader.SetColorMode(False)
    if reader.ReadFile(step_path) != IFSelect_RetDone:
        sys.exit(f"cannot read {step_path}")
    reader.Transfer(doc)
    tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())

    labels = TDF_LabelSequence()
    tool.GetFreeShapes(labels)

    def label_name(lab, fallback):
        attr = TDataStd_Name()
        if lab.FindAttribute(TDataStd_Name.GetID_s(), attr):
            s = attr.Get().ToExtString()
            return s if s else fallback
        return fallback

    scene = trimesh.Scene()
    used = {}

    def add_shape(shape, name):
        # tessellate this shape in place, then harvest triangles per face
        BRepMesh_IncrementalMesh(shape, tess_tol, False, 0.35, True)
        verts, faces = [], []
        exp = TopExp_Explorer(shape, TopAbs_FACE)
        seen = 0
        while exp.More():
            face = TopoDS.Face_s(exp.Current())
            loc = TopLoc_Location()
            tris = BRep_Tool.Triangulation_s(face, loc)
            if tris is not None and tris.NbNodes() > 0:
                trsf = loc.Transformation()
                base = len(verts)
                for i in range(1, tris.NbNodes() + 1):
                    p = tris.Node(i).Transformed(trsf)
                    verts.append((p.X(), p.Y(), p.Z()))
                for i in range(1, tris.NbTriangles() + 1):
                    t = tris.Triangle(i)
                    a, b, c = t.Get()
                    faces.append((base + a - 1, base + b - 1, base + c - 1))
                seen += 1
            exp.Next()
        if not faces:
            return
        key = name
        n = used.get(key, 0)
        used[key] = n + 1
        if n:
            key = f"{name}#{n + 1}"
        import trimesh as _t
        mesh = _t.Trimesh(vertices=verts, faces=faces, process=False)
        scene.add_geometry(mesh, node_name=key, geom_name=key)

    def walk(lab, depth=0):
        # assemblies: descend into component (instance) labels — each keeps
        # its own name + world location; leaves are tessellated as-is
        if tool.IsAssembly_s(lab):
            comps = TDF_LabelSequence()
            tool.GetComponents_s(lab, comps)
            if comps.Length() == 0:
                add_shape(tool.GetShape_s(lab), label_name(lab, f"asm{depth}"))
                return
            for i in range(1, comps.Length() + 1):
                walk(comps.Value(i), depth + 1)
        else:
            add_shape(tool.GetShape_s(lab), label_name(lab, f"leaf{depth}"))

    for i in range(1, labels.Length() + 1):
        walk(labels.Value(i))

    scene.export(glb_path)
    print(f"  glb: {glb_path} ({len(scene.geometry)} named geoms, "
          f"{os.path.getsize(glb_path) // 1024} KiB)")


# ------------------------------------------------------------- plate -> glb

def plate_glb(half, glb_path):
    """Extrude the tracked DXF: OUTLINE 1.2mm, CUTOUT through,
    RELIEF pockets 0.55 deep from the underside (z=0..0.55), PORON ignored
    (it is a punch template, not a cut)."""
    import ezdxf
    import cadquery as cq
    import trimesh

    doc = ezdxf.readfile(os.path.join(REPO, "plate",
                                      f"Hojicha44-{half}-plate.dxf"))
    msp = doc.modelspace()

    def poly_pts(e):
        if e.dxftype() == "LWPOLYLINE":
            return [(p[0], p[1]) for p in e.get_points()]
        if e.dxftype() == "POLYLINE":
            return [(v.dxf.location.x, v.dxf.location.y) for v in e.vertices]
        return None

    outline, cutouts, reliefs = None, [], []
    for e in msp:
        pts = poly_pts(e)
        if pts is None:
            continue
        if e.dxf.layer == "OUTLINE":
            outline = pts
        elif e.dxf.layer == "CUTOUT":
            cutouts.append(pts)
        elif e.dxf.layer == "RELIEF":
            reliefs.append(pts)
    assert outline, "no OUTLINE polyline"
    plate = (cq.Workplane("XY")
             .polyline(outline).close()
             .extrude(1.2))
    for pts in cutouts:
        plate = plate.cut(cq.Workplane("XY").polyline(pts).close()
                          .extrude(1.3).translate((0, 0, -0.05)))
    for pts in reliefs:
        plate = plate.cut(cq.Workplane("XY").polyline(pts).close()
                          .extrude(0.55))
    # render mesh: flip to y-up-equivalent later happens nowhere — the DXF
    # frame matches the board storage frame, so keep as-is
    shape = plate.val()
    verts, faces = [], []
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    BRepMesh_IncrementalMesh(shape.wrapped, 0.1, False, 0.3, True)
    exp = TopExp_Explorer(shape.wrapped, TopAbs_FACE)
    while exp.More():
        face = TopoDS.Face_s(exp.Current())
        loc = TopLoc_Location()
        tris = BRep_Tool.Triangulation_s(face, loc)
        if tris is not None:
            trsf = loc.Transformation()
            base = len(verts)
            for i in range(1, tris.NbNodes() + 1):
                p = tris.Node(i).Transformed(trsf)
                verts.append((p.X(), p.Y(), p.Z()))
            for i in range(1, tris.NbTriangles() + 1):
                a, b, c = tris.Triangle(i).Get()
                faces.append((base + a - 1, base + b - 1, base + c - 1))
        exp.Next()
    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    scene = trimesh.Scene({f"plate_{half}": mesh})
    scene.export(glb_path)
    bb = mesh.bounds
    print(f"  plate glb: {glb_path}  bbox x {bb[0][0]:.1f}..{bb[1][0]:.1f} "
          f"y {bb[0][1]:.1f}..{bb[1][1]:.1f} z {bb[0][2]:.2f}..{bb[1][2]:.2f}")


# ------------------------------------------------------------- knob + screw

def knob_glb(glb_path):
    """EC11 knob: kriscables anodized 13x13 with a knurled cylindrical
    crown. Sits on the 20mm shaft; D-bore not modelled (hidden)."""
    import math
    import cadquery as cq
    import trimesh
    body = (cq.Workplane("XY")
            .rect(13, 13).extrude(4.0)
            .edges("|Z").chamfer(1.0))
    crown = (cq.Workplane("XY").workplane(offset=4.0)
             .circle(6.5).extrude(6.0))
    for i in range(24):
        a = 2 * math.pi * i / 24
        crown = crown.cut(
            cq.Workplane("XY").workplane(offset=4.0)
            .center(6.9 * math.cos(a), 6.9 * math.sin(a))
            .circle(0.55).extrude(6.0))
    knob = body.union(crown)
    verts, faces = [], []
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    shape = knob.val().wrapped
    BRepMesh_IncrementalMesh(shape, 0.08, False, 0.3, True)
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        face = TopoDS.Face_s(exp.Current())
        loc = TopLoc_Location()
        tris = BRep_Tool.Triangulation_s(face, loc)
        if tris is not None:
            trsf = loc.Transformation()
            base = len(verts)
            for i in range(1, tris.NbNodes() + 1):
                p = tris.Node(i).Transformed(trsf)
                verts.append((p.X(), p.Y(), p.Z()))
            for i in range(1, tris.NbTriangles() + 1):
                a, b, c = tris.Triangle(i).Get()
                faces.append((base + a - 1, base + b - 1, base + c - 1))
        exp.Next()
    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    scene = trimesh.Scene({"knob": mesh})
    scene.export(glb_path)
    print(f"  knob glb: {glb_path} ({len(mesh.faces)} tris)")


def screw_glb(glb_path):
    """M2x6 pan-head + 0.8mm hex socket suggestion (procedural)."""
    import cadquery as cq
    import trimesh
    head = (cq.Workplane("XY").circle(1.9).extrude(0.9)
            .edges(">Z").fillet(0.25))
    socket = (cq.Workplane("XY").workplane(offset=0.4)
              .circle(0.6).extrude(0.5))
    head = head.cut(socket)
    shank = cq.Workplane("XY").circle(1.0).extrude(6.0)
    screw = head.union(shank)
    from OCP.TopExp import TopExp_Explorer
    from OCP.TopAbs import TopAbs_FACE
    from OCP.TopoDS import TopoDS
    from OCP.BRep import BRep_Tool
    from OCP.TopLoc import TopLoc_Location
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    verts, faces = [], []
    shape = screw.val().wrapped
    BRepMesh_IncrementalMesh(shape, 0.05, False, 0.25, True)
    exp = TopExp_Explorer(shape, TopAbs_FACE)
    while exp.More():
        face = TopoDS.Face_s(exp.Current())
        loc = TopLoc_Location()
        tris = BRep_Tool.Triangulation_s(face, loc)
        if tris is not None:
            trsf = loc.Transformation()
            base = len(verts)
            for i in range(1, tris.NbNodes() + 1):
                p = tris.Node(i).Transformed(trsf)
                verts.append((p.X(), p.Y(), p.Z()))
            for i in range(1, tris.NbTriangles() + 1):
                a, b, c = tris.Triangle(i).Get()
                faces.append((base + a - 1, base + b - 1, base + c - 1))
        exp.Next()
    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    scene = trimesh.Scene({"screw": mesh})
    scene.export(glb_path)
    print(f"  screw glb: {glb_path}")


# ------------------------------------------------------------- placements

def placements_json(dst):
    """Every footprint of the COMMITTED boards: (ref, x, y, rot)."""
    sys.path.insert(0, os.path.join(REPO, "pcb", "generators"))
    import audit_silk as A
    placements = {}
    for half in ("Left", "Right"):
        path = os.path.join(REPO, "pcb", "kicad", f"Hojicha44-{half}.kicad_pcb")
        out = []
        for ref, fx, fy, frot, blk in A.footprints(path):
            out.append({"ref": ref, "x": r2(fx), "y": r2(fy), "rot": float(frot)})
        placements[half] = out
        print(f"  placements {half}: {len(out)} footprints")
    with open(dst, "w") as f:
        json.dump(placements, f, indent=1)


# ------------------------------------------------------------- main

def main():
    os.makedirs(OUT, exist_ok=True)
    for sub in ("board", "plate", "case", "parts"):
        os.makedirs(os.path.join(OUT, sub), exist_ok=True)

    print("== 1. PCB STEP exports (kicad-cli, read-only on the boards)")
    for half in ("Left", "Right"):
        step = os.path.join(OUT, "board", f"Hojicha44-{half}.step")
        export_pcb_step(half, step)

    print("== 2. PCB STEP -> named glTF")
    for half in ("Left", "Right"):
        step_to_named_glb(os.path.join(OUT, "board", f"Hojicha44-{half}.step"),
                          os.path.join(OUT, "board", f"Hojicha44-{half}.glb"))

    print("== 3. plates from the tracked DXF")
    for half in ("Left", "Right"):
        plate_glb(half, os.path.join(OUT, "plate", f"Hojicha44-{half}.glb"))

    print("== 4. case solids (convert from case/out)")
    import trimesh
    for half in ("Left", "Right"):
        for part in ("tub", "cover"):
            src = os.path.join(REPO, "case", "out",
                               f"Hojicha44-{half}-{part}.stl")
            mesh = trimesh.load(src, force="mesh")
            scene = trimesh.Scene({f"{part}_{half}": mesh})
            dst = os.path.join(OUT, "case", f"Hojicha44-{half}-{part}.glb")
            scene.export(dst)
            bb = mesh.bounds
            print(f"  {half}-{part}: bbox x {bb[0][0]:.1f}..{bb[1][0]:.1f} "
                  f"y {bb[0][1]:.1f}..{bb[1][1]:.1f} z {bb[0][2]:.1f}..{bb[1][2]:.1f}")

    print("== 5. keycaps (KLP Lame, pinned download) -> glb")
    for v in ("Saddle", "Saddle_Tilted", "Saddle_Homing", "Normal_Tilted",
              "Thumb"):
        src = os.path.join(KEYCAP_DIR, f"klp_{v}.step")
        if not os.path.exists(src):
            sys.exit(f"missing keycap source {src} — run the fetch step")
        step_to_named_glb(src, os.path.join(OUT, "parts", f"klp_{v.lower()}.glb"),
                          tess_tol=0.05)

    print("== 6. knob + screw (procedural)")
    knob_glb(os.path.join(OUT, "parts", "knob.glb"))
    screw_glb(os.path.join(OUT, "parts", "screw.glb"))

    print("== 7. placements from the committed boards")
    placements_json(os.path.join(OUT, "placements.json"))

    print("== 8. provenance")
    import platform
    prov = {
        "source_release": "generated/release/v0.5.0 (boards @8eef566357b8)",
        "keycaps": {
            "project": "braindefender/KLP-Lame-Keycaps",
            "license": "CC-BY-SA-4.0 (attribution required)",
            "pinned_commit": open(os.path.join(
                KEYCAP_DIR, "PINNED_SOURCE.txt")).read().strip(),
            "files": [f"klp_{v}.step" for v in ("Saddle", "Saddle_Tilted",
                      "Saddle_Homing", "Normal_Tilted", "Thumb")],
        },
        "tools": {
            "kicad_cli": subprocess.run([KICAD_CLI, "version"],
                                        capture_output=True,
                                        text=True).stdout.strip(),
            "cadquery": __import__("cadquery").__version__,
            "trimesh": trimesh.__version__,
            "python": sys.version.split()[0],
        },
    }
    with open(os.path.join(OUT, "PROVENANCE.json"), "w") as f:
        json.dump(prov, f, indent=1)
    print(json.dumps(prov["tools"], indent=1))


if __name__ == "__main__":
    main()
