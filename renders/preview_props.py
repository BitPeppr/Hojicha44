"""Preview studio for the sculpted desk props (round 13): mouse, mini
PC, pens, mug up close — the desk shot frames them at ~50 px, which
is why the round-12 upgrade was invisible to review. Feedback aid."""
import bpy
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import scene as S          # noqa: E402
import env_props as EP     # noqa: E402

import mathutils

OUT = os.path.join(S.REPO, "generated", "renders", "previews")


def light(name, energy, size, loc, target, color=(1.0, 1.0, 1.0)):
    li = bpy.data.lights.new(name, "AREA")
    li.energy, li.size, li.color = energy, size, color
    o = bpy.data.objects.new(name, li)
    o.location = loc
    d = mathutils.Vector(target) - mathutils.Vector(loc)
    o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    bpy.context.collection.objects.link(o)
    return o


def main():
    os.makedirs(OUT, exist_ok=True)
    S.init_scene()
    m_field = S.pbr("pp_field", (0.42, 0.41, 0.40), rough=0.90)
    S.micro_texture(m_field, 500, 0.3, 0.0004, 0.85, 0.95, detail=4.0)
    bpy.ops.mesh.primitive_plane_add(size=1.1, location=(0, 0, 0))
    fl = bpy.context.active_object
    fl.name = "pp_field"
    S.assign([fl], m_field)

    ep_mats = {}
    objs = []
    objs += EP.build_mouse((-0.06, 0.020, 0), ep_mats, rot_z=0.5)
    objs += EP.build_minipc((0.155, -0.075, 0), ep_mats)
    objs += EP.build_pens((-0.185, -0.055, 0), ep_mats, n=2)
    objs += EP.build_mug((0.30, 0.115, 0), ep_mats)

    world = bpy.data.worlds.new("pp_world")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    lp = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    bg1 = nt.nodes.new("ShaderNodeBackground")
    bg2 = nt.nodes.new("ShaderNodeBackground")
    bg1.inputs[0].default_value = (0.055, 0.058, 0.066, 1.0)
    bg2.inputs[0].default_value = (0.10, 0.10, 0.11, 1.0)
    L = nt.links.new
    L(bg1.outputs["Background"], mix.inputs[1])
    L(bg2.outputs["Background"], mix.inputs[2])
    L(lp.outputs["Is Camera Ray"], mix.inputs["Fac"])
    L(mix.outputs["Shader"], out.inputs["Surface"])

    light("pp_key", 3.2, 0.5, (-0.10, -0.24, 0.18), (0.02, 0.0, 0.004))
    light("pp_fill", 0.8, 0.3, (0.22, -0.10, 0.08), (0.02, 0.0, 0.004),
          (0.80, 0.88, 1.0))

    cam = S.add_cam("pp", (-0.045, -0.30, 0.115), (0.045, -0.005, 0.008),
                    lens=52)
    # CPU for this preview: the Metal path crashed mid-buffer-copy on
    # this scene (Cycles PathTraceWork::copy_from_render_buffers)
    dev = "cpu"
    if "--metal" in sys.argv:
        dev = "metal"
    S.render_to(cam, os.path.join(OUT, "props.png"), (1600, 1000), 48,
                dev)
    print("PROPS-PREVIEW-DONE")


main()
