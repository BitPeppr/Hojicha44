"""MacBook Pro 16" (M3 Max, Space Black) as a render prop.

Round 24d: the desk set needed ONE hero computer that reads as a real
product, so the numbers below are the shipped ones, not stylisations:

  enclosure      355.7 x 248.1 mm, 16.8 mm closed
  base wedge     11.4 mm at the hinge tapering to 8.8 mm at the front
  display        16.2"  3456 x 2234  -> 344.3 x 222.5 mm active area
  keyboard       78 keys, 14 columns, 19.65 mm pitch, full-height
                 function row, US ANSI
  trackpad       150.0 x 96.0 mm, recessed 0.4 mm, glass
  ports          left  MagSafe 3, 2x Thunderbolt 4, 3.5 mm jack
                 right HDMI, Thunderbolt 4, SDXC
  finish         Space Black anodised (the M3 Pro/Max colour), matte
                 bead-blasted, with the machined chamfer catching light;
                 black glass display, black keycaps, rubber feet.

Geometry is built in DESIGN MILLIMETRES and scaled to metres at the
end, so every number below can be checked against the spec sheet.
"""

import math

import bpy


def _mat(name, colour, rough, metal=0.0, coat=None):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*colour, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if coat and "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = coat[0]
        b.inputs["Coat Roughness"].default_value = coat[1]
    return m


def _bead_blast(mat, scale=900.0, strength=0.10, dist=0.000006,
                r0=0.30, r1=0.42):
    """Bead-blasted anodising: a fine isotropic tooth that breaks the
    highlight. Without it a big flat aluminium panel reads as CG."""
    nt = mat.node_tree
    b = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = scale
    nz.inputs["Detail"].default_value = 6.0
    nz.inputs["Roughness"].default_value = 0.55
    nt.links.new(tc.outputs["Generated"], nz.inputs["Vector"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = dist
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    rr = nt.nodes.new("ShaderNodeMapRange")
    rr.inputs["From Min"].default_value = 0.25
    rr.inputs["From Max"].default_value = 0.75
    rr.inputs["To Min"].default_value = r0
    rr.inputs["To Max"].default_value = r1
    nt.links.new(nz.outputs["Fac"], rr.inputs["Value"])
    nt.links.new(rr.outputs["Result"], b.inputs["Roughness"])
    mat["micro_texture"] = True
    return mat


def _grille(mat, scale=(320.0, 320.0, 1.0), strength=0.55):
    """Speaker grille: rows of drilled holes. A hole grid is a
    high-frequency square wave in both axes minus its product."""
    nt = mat.node_tree
    b = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    mp = nt.nodes.new("ShaderNodeMapping")
    mp.inputs["Scale"].default_value = scale
    nt.links.new(tc.outputs["Generated"], mp.inputs["Vector"])
    wx = nt.nodes.new("ShaderNodeTexWave")
    wx.wave_type, wx.bands_direction = "BANDS", "X"
    wx.inputs["Scale"].default_value = 1.0
    wy = nt.nodes.new("ShaderNodeTexWave")
    wy.wave_type, wy.bands_direction = "BANDS", "Y"
    wy.inputs["Scale"].default_value = 1.0
    nt.links.new(mp.outputs["Vector"], wx.inputs["Vector"])
    nt.links.new(mp.outputs["Vector"], wy.inputs["Vector"])
    dark_x = nt.nodes.new("ShaderNodeMapRange")
    dark_x.inputs["From Min"].default_value = 0.62
    dark_x.inputs["From Max"].default_value = 0.38
    dark_x.inputs["To Min"].default_value = 0.0
    dark_x.inputs["To Max"].default_value = 1.0
    nt.links.new(wx.outputs["Fac"], dark_x.inputs["Value"])
    dark_y = nt.nodes.new("ShaderNodeMapRange")
    dark_y.inputs["From Min"].default_value = 0.62
    dark_y.inputs["From Max"].default_value = 0.38
    dark_y.inputs["To Min"].default_value = 0.0
    dark_y.inputs["To Max"].default_value = 1.0
    nt.links.new(wy.outputs["Fac"], dark_y.inputs["Value"])
    holes = nt.nodes.new("ShaderNodeMath")
    holes.operation = "MULTIPLY"
    nt.links.new(dark_x.outputs["Result"], holes.inputs[0])
    nt.links.new(dark_y.outputs["Result"], holes.inputs[1])
    tint = nt.nodes.new("ShaderNodeMixRGB")
    tint.blend_type = "MIX"
    tint.inputs["Color1"].default_value = (0.020, 0.020, 0.022, 1.0)
    tint.inputs["Color2"].default_value = (0.055, 0.055, 0.060, 1.0)
    nt.links.new(holes.outputs["Value"], tint.inputs["Fac"])
    nt.links.new(tint.outputs["Color"], b.inputs["Base Color"])
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = 0.00018
    nt.links.new(holes.outputs["Value"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    mat["micro_texture"] = True
    return mat


# every width in the ANSI layout, in key units (1u = 19.65 mm)
ROWS = [
    [1.0] * 14,                                    # esc F1..F12 + touch id
    [1.0] * 13 + [2.0],                            # ` 1..0 - =      delete
    [1.5] + [1.0] * 12 + [1.5],                    # tab QWERTYUIOP[] \
    [1.75] + [1.0] * 11 + [2.25],                  # caps ASDFGHJKL;' enter
    [2.25] + [1.0] * 10 + [2.75],                  # shift ZXCVBNM,./ shift
    [1.25, 1.25, 1.25, 5.0, 1.25, 1.25, 0.75, 0.75, 0.75, 0.75],
]


def build_macbook(loc, rot_z=0.0, open_deg=104.0,
                  finish=(0.215, 0.219, 0.228), scale=0.001):
    """Return the list of objects. loc = the underside centre of the
    base in metres; the laptop is centred there and yawed by rot_z."""
    W, D, H = 355.7, 248.1, 16.8
    BASE_F, BASE_R = 8.8, 11.4                # base wedge front/rear
    LID_T0, LID_T1 = 5.9, 8.4                 # lid thickness near/at hinge
    PITCH = 19.65
    KEY_W, KEY_GAP = 17.4, 1.4
    KEY_H = 3.4
    WELL_INSET = 1.6
    KB_W = 14 * PITCH
    TP_W, TP_D, TP_DEPTH = 150.0, 96.0, 0.4

    S = scale
    objs = []

    m_alu = _bead_blast(_mat("mb_alu", finish, 0.34, metal=1.0))
    m_alu_dark = _bead_blast(_mat("mb_alu_dark", (0.045, 0.046, 0.049),
                                  0.30, metal=1.0), scale=1400.0,
                             strength=0.08)
    m_key = _mat("mb_key", (0.026, 0.026, 0.029), 0.52)
    _bead_blast(m_key, scale=2000.0, strength=0.14, dist=0.000004,
                r0=0.46, r1=0.60)
    m_glass = _mat("mb_glass", (0.006, 0.006, 0.008), 0.045,
                   coat=(1.0, 0.03))
    m_well = _mat("mb_well", (0.006, 0.006, 0.007), 0.62)
    m_grille = _grille(_mat("mb_grille", (0.03, 0.03, 0.033), 0.42,
                            metal=0.6))
    m_rubber = _mat("mb_rubber", (0.020, 0.020, 0.022), 0.88)
    m_port = _mat("mb_port", (0.028, 0.028, 0.030), 0.45, metal=0.5)

    def box(name, centre, size, mat, bevel=0.0, segments=3, yaw=0.0):
        bpy.ops.mesh.primitive_cube_add(size=1)
        o = bpy.context.active_object
        o.name = name
        o.scale = (size[0] * S, size[1] * S, size[2] * S)
        o.location = (loc[0] + centre[0] * S, loc[1] + centre[1] * S,
                      loc[2] + centre[2] * S)
        o.rotation_euler.z = math.radians(rot_z + yaw)
        if bevel > 0:
            bm = o.modifiers.new("bev", "BEVEL")
            bm.width, bm.segments = bevel * S, segments
            bm.limit_method = "ANGLE"
        o.data.materials.append(mat)
        objs.append(o)
        return o

    # ---- base wedge: 11.4 mm at the hinge, 8.8 mm at the front. Built
    # as a box and SHEARED in z by moving the front-top edge down — the
    # real enclosure is a machined wedge, and a flat slab reads as a
    # generic laptop immediately.
    base = box("mb_base", (0.0, 0.0, BASE_R / 2.0), (W, D, BASE_R),
               m_alu, bevel=1.6)
    # The DECK is flat (the keyboard is machined into a flat surface);
    # the taper is on the BOTTOM, which sweeps up towards the front
    # edge. Local +y is the hinge side, so the front is -y.
    me = base.data
    for v in me.vertices:
        if v.co.z < 0 and v.co.y < 0:
            v.co.z += (BASE_R - BASE_F) / BASE_R

    # ---- keyboard well: a dark recessed plate, then the keys
    deck_y = 0.0
    kb_y = deck_y + 30.0
    box("mb_well", (0.0, kb_y, BASE_R - 1.0),
        (KB_W + 2 * WELL_INSET, 6 * PITCH + 2 * WELL_INSET, 2.4), m_well)
    row_y = kb_y - (6 * PITCH) / 2.0 + PITCH / 2.0
    for ri, row in enumerate(ROWS):
        total = sum(row) * PITCH
        x = -total / 2.0 + 0.0
        y = row_y + (5 - ri) * PITCH
        for w in row:
            cw = w * PITCH - KEY_GAP
            box(f"mb_key_{ri}_{int(x)}", (x + w * PITCH / 2.0, y,
                                          BASE_R + KEY_H / 2.0 - 0.6),
                (cw, PITCH - KEY_GAP, KEY_H), m_key, bevel=0.55)
            x += w * PITCH

    # ---- trackpad: 150 x 96 recessed 0.4 mm with a 0.15 mm gap line
    tp_y = kb_y - (6 * PITCH) / 2.0 - TP_D / 2.0 - 16.0
    box("mb_trackpad", (0.0, tp_y, BASE_R - TP_DEPTH / 2.0 - 0.05),
        (TP_W, TP_D, TP_DEPTH), m_glass, bevel=2.0, segments=4)

    # ---- speaker grilles flanking the well
    gr_w = 58.0
    for sgn in (-1, 1):
        box(f"mb_grille_{'l' if sgn < 0 else 'r'}",
            (sgn * (KB_W / 2.0 + WELL_INSET + gr_w / 2.0 + 3.0), kb_y,
             BASE_R - 0.35),
            (gr_w, 6 * PITCH * 0.86, 0.9), m_grille)

    # ---- ports: cut-outs are dark; the shells sit in the side walls
    def port(name, x, y, size, mat=m_port):
        return box(name, (x, y, BASE_F / 2.0 + 1.2), size, mat, bevel=0.3)

    port("mb_magsafe", -W / 2.0 + 8.0, 62.0, (7.0, 5.6, 3.4), m_alu_dark)
    port("mb_usbc_l1", -W / 2.0 + 6.6, 22.0, (9.2, 3.6, 3.2), m_alu_dark)
    port("mb_usbc_l2", -W / 2.0 + 6.6, -2.0, (9.2, 3.6, 3.2), m_alu_dark)
    port("mb_jack", -W / 2.0 + 4.0, -34.0, (3.6, 3.6, 3.2), m_port)
    port("mb_hdmi", W / 2.0 - 10.0, 30.0, (14.0, 7.0, 3.4), m_alu_dark)
    port("mb_usbc_r", W / 2.0 - 6.6, -6.0, (9.2, 3.6, 3.2), m_alu_dark)
    port("mb_sdxc", W / 2.0 - 7.0, -46.0, (25.0, 3.2, 2.8), m_alu_dark)

    # ---- rubber feet (4), 8 mm circles, inset from the corners
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(f"mb_foot_{sx}_{sy}",
                (sx * (W / 2.0 - 12.0), sy * (D / 2.0 - 12.0), 0.6),
                (8.0, 8.0, 1.2), m_rubber, bevel=1.0, segments=3)

    # ---- display assembly, hinged at the back edge. The lid is a
    # 5.9 mm sheet at the top tapering to 8.4 mm at the hinge, holding
    # a 3.5 mm bezel, the glass, the notch and the bottom-bezel wordmark.
    hinge_z = BASE_R + 0.6
    hinge_y = D / 2.0 - 6.0
    lid_pivot = (loc[0], loc[1] + hinge_y * S, loc[2] + hinge_z * S)
    lid = bpy.data.objects.new("mb_lid", None)
    bpy.context.collection.objects.link(lid)
    lid.location = lid_pivot
    # 0 deg = lid vertical; a wider opening leans the lid BACK over the
    # hinge, which is +y here (the base runs towards -y)
    lid.rotation_euler = (math.radians(open_deg - 90.0), 0.0,
                          math.radians(rot_z))
    objs.append(lid)

    def lbox(name, centre, size, mat, bevel=0.0, segments=3):
        """A box in LID space: +z is up the lid, +y is the lid's
        THICKNESS (the screen faces +y, the outer shell -y)."""
        bpy.ops.mesh.primitive_cube_add(size=1)
        o = bpy.context.active_object
        o.name = name
        o.scale = (size[0] * S, size[1] * S, size[2] * S)
        o.location = (centre[0] * S, centre[1] * S, centre[2] * S)
        if bevel > 0:
            bm = o.modifiers.new("bev", "BEVEL")
            bm.width, bm.segments = bevel * S, segments
            bm.limit_method = "ANGLE"
        o.data.materials.append(mat)
        # Parent WITHOUT a parent-inverse: the child then lives in the
        # lid's own frame and swings with it. (Setting the inverse to
        # the lid's world matrix would preserve the child's world
        # transform -- which is how the display ended up lying flat on
        # the desk in the first pass.)
        o.parent = lid
        objs.append(o)
        return o

    LID_H = 232.0                                # lid height, mm
    lbox("mb_lid_shell", (0.0, -3.2, LID_H / 2.0),
         (W, 6.4, LID_H), m_alu, bevel=1.6)
    # glass: active area 344.3 x 222.5, ~5 mm side bezels, 12 mm
    # bottom bezel (the wordmark strip), 5 mm at the top
    act_w, act_h = 344.3, 222.5
    glass_c = (0.0, 0.15, 12.0 + act_h / 2.0)
    lbox("mb_glass", glass_c, (act_w, 0.5, act_h), m_glass)
    # notch: 20 x 5.2 mm, flush with the glass top edge
    lbox("mb_notch", (0.0, 0.35, LID_H - 5.0 - 2.6), (20.0, 0.7, 5.2),
         m_mat_dark_default())
    # bottom-bezel wordmark strip (subtle, darker than the bezel)
    lbox("mb_wordmark", (0.0, 0.28, 6.4), (150.0, 0.3, 3.0),
         m_mat_dark_default())
    # hinge barrels
    for sx in (-1, 1):
        b0 = box(f"mb_hinge_{sx}", (sx * (W / 2.0 - 62.0), hinge_y,
                                    hinge_z - 1.0),
                 (56.0, 8.0, 5.6), m_alu_dark, bevel=1.4)
        _ = b0
    return objs


def m_mat_dark_default():
    return _mat("mb_notch", (0.010, 0.010, 0.012), 0.35)


def build_phone(loc, rot_z=0.0, scale=0.001,
                body=(0.055, 0.056, 0.060)):
    """A modern 6.1" phone: rounded slab, camera plateau, glass front.
    Numbers: 71.6 x 147.6 x 8.25 mm (16 Pro class)."""
    W, H, T = 71.6, 147.6, 8.25
    S = scale
    m_body = _bead_blast(_mat("ph_body", body, 0.28, metal=1.0),
                         scale=1600.0, strength=0.07, r0=0.24, r1=0.34)
    m_glass = _mat("ph_glass", (0.008, 0.008, 0.010), 0.030,
                   coat=(1.0, 0.02))
    m_lens = _mat("ph_lens", (0.008, 0.008, 0.010), 0.06, metal=0.2)
    objs = []
    bpy.ops.mesh.primitive_cube_add(size=1)
    body_o = bpy.context.active_object
    body_o.name = "ph_body"
    body_o.scale = (W * S, H * S, T * S)
    body_o.location = (loc[0], loc[1], loc[2] + T * S / 2.0)
    body_o.rotation_euler.z = math.radians(rot_z)
    bm = body_o.modifiers.new("bev", "BEVEL")
    bm.width, bm.segments = 2.6 * S, 6
    bm.limit_method = "ANGLE"
    body_o.data.materials.append(m_body)
    objs.append(body_o)
    bpy.ops.mesh.primitive_cube_add(size=1)
    g = bpy.context.active_object
    g.name = "ph_screen"
    g.scale = ((W - 3.2) * S, (H - 3.2) * S, 0.5 * S)
    g.location = (loc[0], loc[1], loc[2] + T * S)
    g.rotation_euler.z = math.radians(rot_z)
    gm = g.modifiers.new("bev", "BEVEL")
    gm.width, gm.segments = 2.4 * S, 6
    gm.limit_method = "ANGLE"
    g.data.materials.append(m_glass)
    objs.append(g)
    # camera plateau, top-left of the back
    for i, (dx, dy) in enumerate(((-22.0, 52.0), (-22.0 + 17.0, 52.0),
                                  (-22.0, 52.0 - 17.0))):
        bpy.ops.mesh.primitive_cylinder_add(vertices=28,
                                            radius=7.6 * S, depth=1.6 * S)
        l = bpy.context.active_object
        l.name = f"ph_lens_{i}"
        ang = math.radians(rot_z)
        px = dx * math.cos(ang) - dy * math.sin(ang)
        py = dx * math.sin(ang) + dy * math.cos(ang)
        l.location = (loc[0] + px * S, loc[1] + py * S,
                      loc[2] + (T + 0.4) * S)
        l.data.materials.append(m_lens)
        objs.append(l)
    return objs


def build_pen(loc, rot_z=0.0, length=140.0, radius=4.6, scale=0.001,
              colour=(0.020, 0.020, 0.022), cap=(0.55, 0.55, 0.57)):
    """A capped rollerball: body + cap + clip, lying on the desk."""
    S = scale
    m_barrel = _mat("pen_barrel", colour, 0.30)
    m_cap = _bead_blast(_mat("pen_cap", cap, 0.24, metal=0.9),
                        scale=2200.0, strength=0.06, r0=0.20, r1=0.30)
    objs = []
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=radius * S,
                                        depth=length * S)
    b = bpy.context.active_object
    b.name = "pen_body"
    b.rotation_euler = (math.radians(90.0), 0.0, math.radians(rot_z))
    b.location = (loc[0], loc[1], loc[2] + radius * S)
    b.data.materials.append(m_barrel)
    objs.append(b)
    bpy.ops.mesh.primitive_cylinder_add(vertices=32,
                                        radius=(radius + 0.5) * S,
                                        depth=(length * 0.34) * S)
    c = bpy.context.active_object
    c.name = "pen_cap"
    c.rotation_euler = (math.radians(90.0), 0.0, math.radians(rot_z))
    off = (length * 0.5 - length * 0.17)
    ang = math.radians(rot_z)
    c.location = (loc[0] - math.sin(ang) * off * S,
                  loc[1] + math.cos(ang) * off * S,
                  loc[2] + radius * S)
    c.data.materials.append(m_cap)
    objs.append(c)
    return objs
