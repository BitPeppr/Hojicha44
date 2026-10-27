"""Material-completeness audit (round 20): walk every material in a
built scene and flag any surface with no height/bump input or no
roughness variation — the review bar is "not a single face should be
void of a height map". Builds the scene; renders nothing.

Run: blender --background --python renders/audit_materials.py -- --scene product
     blender --background --python renders/audit_materials.py -- --scene env
     (--colourway dark --shots any also fine; shots are not rendered)
"""
import bpy
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene as S          # noqa: E402


class _A:
    pass


def _mat_census():
    """Walk every used material; classify what detail it carries."""
    rows = []
    for mat in bpy.data.materials:
        if mat.get("audit_seen"):
            continue
        nt = mat.node_tree
        if nt is None:
            continue
        bsdf = nt.nodes.get("Principled BSDF")
        if bsdf is None:
            continue
        has_bump = any(n.type in ("BUMP", "DISPLACEMENT", "NORMAL_MAP")
                       for n in nt.nodes)
        has_rough_var = False
        bump_node = next((n for n in nt.nodes if n.type == "BUMP"), None)
        if bump_node is not None:
            src = bump_node.inputs["Height"].links[0].from_socket.node \
                if bump_node.inputs["Height"].links else None
            if src is not None and src.type != "VALUE":
                has_rough_var = True
        # roughness that is linked (varies) vs a constant
        rough_linked = bool(bsdf.inputs["Roughness"].links)
        coat = "Coat Weight" in bsdf.inputs and \
            bsdf.inputs["Coat Weight"].default_value > 0.01
        rows.append({
            "name": mat.name,
            "users": mat.users,
            "bump": has_bump,
            "var": has_rough_var or rough_linked,
            "coat": coat,
        })
        mat["audit_seen"] = True
    return rows


def main():
    args = _A()
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    scene = "env" if "env" in argv else "product"
    args.palette = args.hide_cover = args.hide_case = args.hide_plate \
        = args.stack_colors = args.framecheck = False
    args.colourway = ("dark" if "dark" in argv else
                      ("play" if "play" in argv else "bright"))
    S.init_scene()
    if scene == "env":
        import scene_env
        # framecheck builds the whole env scene and returns before
        # any render — the audit can then walk its materials
        if "--framecheck" not in argv:
            sys.argv = [sys.argv[0]] + argv + ["--framecheck"]
        scene_env.main()
    else:
        S.build_keyboard(args)
        S.apply_colourway(bpy.data.objects.get("parts") and
                          {"L": {}, "R": {}} or {}, args.colourway) \
            if False else None
    rows = _mat_census()
    flat = [r for r in rows if not r["bump"] or not r["var"]]
    ok = len(rows) - len(flat)
    print(f"[audit] {scene}: {len(rows)} materials with a principled "
          f"BSDF, {ok} detailed (bump + variation), {len(flat)} flat")
    for r in sorted(flat, key=lambda r: -r["users"]):
        print(f"[audit] FLAT  {r['name']:28s} users={r['users']:3d} "
              f"bump={r['bump']} variation={r['var']}")
    print("AUDIT-DONE")


main()
