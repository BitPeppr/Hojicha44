"""Preview studio for the new procedural parts (round 9): the choc
switch, the artisan cap and the knob, side by side on a neutral field.
Not part of the delivery set — a feedback aid only."""
import bpy
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene as S

PARTS = os.path.join(S.ASSETS, "parts")
OUT = os.path.join(S.REPO, "generated", "renders", "previews")


def light(name, energy, size, loc, target, color=(1.0, 1.0, 1.0)):
    li = bpy.data.lights.new(name, "AREA")
    li.energy, li.size, li.color = energy, size, color
    o = bpy.data.objects.new(name, li)
    o.location = loc
    d = __import__("mathutils").Vector(target) - __import__("mathutils").Vector(loc)
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.collection.objects.link(o)


def main():
    os.makedirs(OUT, exist_ok=True)
    S.init_scene()
    mats = {
        "housing": S.pbr("p_housing", (0.72, 0.70, 0.66), rough=0.45),
        "artisan": S.pbr("p_artisan", (0.055, 0.30, 0.30), rough=0.22),
        "knob": S.pbr("p_knob", (0.72, 0.73, 0.75), rough=0.26, metal=1.0),
        "floor": S.pbr("p_floor", (0.42, 0.41, 0.40), rough=0.90),
    }
    b = mats["housing"].node_tree.nodes["Principled BSDF"]
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = 0.4
    b = mats["artisan"].node_tree.nodes["Principled BSDF"]
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = 0.5

    # neutral field
    bpy.ops.mesh.primitive_plane_add(size=0.5, location=(0, 0, 0))
    fl = bpy.context.active_object
    fl.name = "p_field"
    S.assign([fl], mats["floor"])

    for name, mat, (x, y) in (("choc", "housing", (0, 0.016)),
                              ("artisan", "artisan", (0, -0.020)),
                              ("knob", "knob", (0, -0.054))):
        _, roots, objs = S.import_glb(os.path.join(PARTS, f"{name}.glb"),
                                      f"pv_{name}")
        bpy.context.view_layer.update()
        S.assign(objs, mats[mat])
        for r in roots:
            r.location.x += x
            r.location.y += y
    bpy.context.view_layer.update()

    world = bpy.data.worlds.new("pv_world")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    bg1 = nt.nodes.new("ShaderNodeBackground")
    bg2 = nt.nodes.new("ShaderNodeBackground")
    bg1.inputs[0].default_value = (0.06, 0.065, 0.075, 1.0)
    bg2.inputs[0].default_value = (0.10, 0.10, 0.11, 1.0)
    L = nt.links.new
    L(bg1.outputs["Background"], mix.inputs[1])
    L(bg2.outputs["Background"], mix.inputs[2])
    L(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    L(mix.outputs["Shader"], out.inputs["Surface"])

    light("pv_key", 2.5, 0.4, (-0.10, -0.16, 0.12), (0, 0, 0.004))
    light("pv_fill", 0.6, 0.3, (0.14, -0.06, 0.05), (0, 0, 0.004),
          (0.75, 0.85, 1.0))

    cam = S.add_cam("pv", (-0.055, -0.135, 0.062), (0, -0.010, 0.004),
                    lens=60)
    cam.data.dof.use_dof = False   # reference plate: everything sharp
    S.render_to(cam, os.path.join(OUT, "parts.png"), (1600, 1000), 48)
    print("PARTS-PREVIEW-DONE")


main()
