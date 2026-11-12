#!/usr/bin/env python3
"""Generates the Warrior Greatsword model, Blockbench project and preview sheet.

Reuses the canvas, model and export helpers from build_katana.py.
Run:  python3 tools/build_greatsword.py   (add --legacy-rotation for 22.5 degree steps)
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_katana as k
from build_katana import Canvas, F, Model, flipu, hsh, mix

NS, NAME = "warrior", "warrior_greatsword"
k.NS = NS
k.TEXTURES = [("0", NAME, 128, 0, False)]
k.DISPLAY = {
    "thirdperson_righthand": {"rotation": [0, -90, 10], "translation": [0, 10.35, 0.25], "scale": [0.95] * 3},
    "firstperson_righthand": {"rotation": [0, -90, -20], "translation": [1.13, 8.1, 1.5], "scale": [0.75] * 3},
    "gui": {"rotation": [0, 0, -45], "translation": [0, 0, 0], "scale": [0.46] * 3},
    "ground": {"rotation": [0, 0, -45], "translation": [0, 2, 0], "scale": [0.5] * 3},
    "fixed": {"rotation": [0, 180, -45], "translation": [0, 0, 0], "scale": [0.5] * 3},
}

# ---------------------------------------------------------------- palette
STEEL, STEEL_L, STEEL_D = (146, 151, 158), (188, 192, 198), (88, 92, 102)
EDGE = (214, 218, 222)
RUST = (120, 76, 50)
IRON, IRON_L, IRON_D = (82, 80, 84), (124, 121, 120), (48, 46, 52)
LEATHER, LEATHER_L, LEATHER_D = (62, 42, 30), (100, 72, 50), (36, 24, 18)
CLOTH, CLOTH_D = (116, 42, 36), (70, 24, 24)

# ---------------------------------------------------------------- blade layout
Y0, Y_TIP = -0.5, 30.5
FULLER_END, TAPER_Y = 22.0, 24.5
SEGMENTS = [(-0.5, 5.75, 4.6), (5.75, 12.0, 4.4), (12.0, 18.25, 4.2), (18.25, 24.5, 4.0)]  # y0, y1, width
TIP = [(24.5, 26.5, 3.5, 0.38), (26.5, 28.25, 2.5, 0.32), (28.25, 29.75, 1.5, 0.26), (29.75, 30.5, 0.5, 0.2)]
# chips in the cutting edges: side, height on the blade, depth and length in texels
NICKS = [("l", 3.2, 2, 3), ("r", 6.4, 1, 2), ("l", 9.0, 1, 2), ("r", 9.9, 1, 2), ("r", 12.6, 2, 3),
         ("l", 14.6, 2, 2), ("l", 16.1, 1, 3), ("r", 19.0, 2, 3), ("l", 21.3, 1, 2), ("r", 22.9, 1, 2)]


def vb(y):
    """Texture row of blade height y (4 texels per model pixel, tip at the top)."""
    return 124 - 4 * y


# ---------------------------------------------------------------- texture regions (texels)
R_STEEL = (28, 2, 30, 4)
R_GRIP, R_GRIP_E = (32, 0, 40, 24), (40, 0, 46, 24)
R_IRON, R_IRON_S = (48, 0, 60, 8), (48, 10, 52, 14)
R_QUIL_IN, R_QUIL_OUT = (32, 28, 44, 36), (44, 28, 56, 36)
R_GBLOCK, R_CAP = (32, 38, 44, 44), (46, 38, 50, 44)
R_POMMEL, R_STUD = (32, 48, 42, 56), (44, 48, 50, 54)
R_LANGET, R_LUG = (32, 58, 40, 68), (44, 58, 48, 62)
R_RISER = (32, 70, 40, 72)
R_CLOTH, R_CLOTH_E, R_CLOTH_BAND = (62, 0, 68, 24), (62, 0, 63, 20), (62, 26, 70, 30)


def iron(x, y, seed=0):
    n = hsh(x + seed * 17, y + seed * 31)
    col = mix(IRON, IRON_L, n * 0.45)
    if n > 0.9:
        col = mix(col, RUST, 0.6)
    if n < 0.08:
        col = IRON_D
    return col


def paint():
    cv = Canvas(128, 128)
    nick = {}
    for side, y, depth, rows in NICKS:
        r0 = int((Y_TIP - y) * 4)
        for j in range(rows):
            nick[(side, r0 + j)] = 1 if depth == 2 and rows > 2 and j in (0, rows - 1) else depth

    def steel(c, r, base):
        n = hsh(c, r)
        col = mix(base, STEEL_L if n > 0.5 else STEEL_D, abs(n - 0.5) * 0.5)
        if hsh(c // 2 + 40, r // 3) > 0.9:
            col = mix(col, RUST, 0.45)
        if hsh(c // 3 + 90, r // 5) < 0.07:
            col = mix(col, STEEL_D, 0.5)
        if (c * 2 + r) % 29 == 0 and hsh(r // 7, 5) > 0.4:  # scratches
            col = mix(col, EDGE, 0.6)
        if r > 112 and hsh(c // 2, r // 2 + 200) > 0.55:    # rust creeping up from the guard
            col = mix(col, RUST, 0.5)
        return col

    # blade strip: columns 0-1 and 18-19 are the edges, 2-6 / 13-17 the flats, 7-12 the fuller
    for r in range(124):
        y = Y_TIP - (r + 0.5) / 4
        for c in range(20):
            if y < TAPER_Y:
                side = "l" if c < 2 else "r" if c > 17 else None
                di = c if c < 2 else 19 - c
                if side:
                    if nick.get((side, r), 0) > di:
                        continue
                    near = max(nick.get((side, r - 1), 0), nick.get((side, r + 1), 0)) > di
                    col = (STEEL_D if near else mix(EDGE, (255, 255, 255), 0.3 * hsh(c, r)) if di == 0
                           else mix(EDGE, STEEL, 0.45))
                elif 7 <= c <= 12 and y < FULLER_END - (0.5 if c in (7, 12) else 0):
                    col = steel(c, r, mix((62, 66, 76), (118, 123, 131), (c - 7) / 5))
                    if y > FULLER_END - 0.5:
                        col = mix(col, STEEL_D, 0.5)
                else:
                    col = steel(c, r, mix(STEEL, EDGE, 0.5) if c in (2, 17) else STEEL_L if c in (6, 13) else STEEL)
            else:
                half = 2 * next(w for a, b, w, _ in TIP if a <= y < b)
                d = abs(c + 0.5 - 10)
                if d > half:
                    continue
                col = (mix(EDGE, (255, 255, 255), 0.3 * hsh(c, r)) if d > half - 1.5
                       else steel(c, r, STEEL_L if d < 1 else STEEL))
            cv.set(c, 2 + r, col)
        # side strips: chipped edge faces (left, right), flat shoulders, clean edge
        if not nick.get(("l", r)):
            cv.set(22, 2 + r, EDGE)
        if not nick.get(("r", r)):
            cv.set(23, 2 + r, EDGE)
        cv.set(24, 2 + r, STEEL_D)
        cv.set(25, 2 + r, mix(STEEL_D, STEEL, 0.4))
        cv.set(26, 2 + r, EDGE)
    cv.rect(28, 2, 30, 4, mix(STEEL, STEEL_D, 0.3))

    def leather(x, y):
        t = (x + 2 * y) % 8
        col = LEATHER_D if t == 0 else LEATHER_L if t == 1 else mix(LEATHER, LEATHER_D, hsh(x, y) * 0.5)
        if hsh(x // 2 + 7, y // 3) > 0.85:  # palm wear
            col = mix(col, LEATHER_L, 0.5)
        return col
    cv.rect(32, 0, 46, 24, leather)
    cv.rect(48, 0, 60, 8, iron)
    cv.rect(48, 10, 52, 14, lambda x, y: iron(x, y, 3))

    def quillon(x, y):
        col = iron(x, y, 5)
        if y == 0:
            col = mix(col, IRON_L, 0.6)
        if y == 7:
            col = IRON_D
        if y == 4 and 2 <= x <= 21:
            col = IRON_D
        if y == 3 and 2 <= x <= 21:
            col = mix(col, IRON_L, 0.4)
        if x > 17 and hsh(x, y + 60) > 0.6:
            col = mix(col, RUST, 0.5)
        return col
    cv.rect(32, 28, 56, 36, quillon)
    cv.rect(32, 38, 44, 44, lambda x, y: IRON_D if x in (0, 11) or y == 5 else
            mix(iron(x, y, 7), IRON_L, 0.5 if y == 0 else 0))
    cv.rect(46, 38, 50, 44, lambda x, y: mix(iron(x, y, 9), IRON_L, 0.5 if y in (0, 1) else 0))

    def pommel(x, y):
        d = abs(x + 0.5 - 5) / 5 + abs(y + 0.5 - 4) / 4
        col = iron(x, y, 11)
        if 0.55 < d < 0.8:
            col = IRON_D
        elif d < 0.3:
            col = mix(col, IRON_L, 0.6)
        return mix(col, IRON_D, 0.4) if y == 7 else col
    cv.rect(32, 48, 42, 56, pommel)
    cv.rect(44, 48, 50, 54, lambda x, y: IRON_L if (x, y) in ((2, 2), (3, 2), (2, 3)) else
            mix(iron(x, y, 13), IRON_L, 0.3))

    def langet(x, y):
        if (x in (2, 5)) and y in (2, 7):
            return IRON_L
        return IRON_D if x in (0, 7) or y == 0 else iron(x, y, 15)
    cv.rect(32, 58, 40, 68, langet)
    cv.rect(44, 58, 48, 62, lambda x, y: mix(iron(x, y, 17), STEEL, 0.4))
    cv.rect(32, 70, 40, 72, lambda x, y: LEATHER_D if y else mix(LEATHER, LEATHER_L, 0.6))

    def cloth(x, y):
        if y > 19 + hsh(x, 3) * 5 or (y > 8 and hsh(x // 2, y // 2 + 50) > 0.93):
            return (0, 0, 0, 0)  # frayed end and moth holes
        col = mix(CLOTH, CLOTH_D, hsh(x, y) * 0.5 + y / 40)
        return mix(col, CLOTH_D, 0.5) if x % 3 == 0 else col
    cv.rect(62, 0, 68, 24, cloth)
    cv.rect(62, 26, 70, 30, lambda x, y: mix(CLOTH, CLOTH_D, hsh(x, y + 9) * 0.6 + (0.3 if y == 3 else 0)))
    return cv


# ---------------------------------------------------------------- model
def build():
    m = Model(NAME)
    small = F(s=R_IRON_S, e=R_IRON_S, u=R_IRON_S)

    m.group("pommel", [8, -12, 8])
    m.box("pommel", "pommel_core", [6.9, -14, 7.1], [9.1, -12.2, 8.9], F(s=R_POMMEL, e=R_POMMEL, u=R_IRON))
    m.box("pommel", "pommel_cap", [7.3, -14.5, 7.4], [8.7, -14, 8.6], small)
    m.box("pommel", "pommel_collar", [7.2, -12.2, 7.3], [8.8, -11.8, 8.7], small)
    m.box("pommel", "pommel_stud", [7.5, -13.6, 6.95], [8.5, -12.6, 9.05],
          F(s=R_STUD, e=R_IRON_S, u=R_IRON_S), ("z", 45, [8, -13.1, 8]))

    m.group("handle", [8, -7, 8])
    grip, riser = F(s=R_GRIP, e=R_GRIP_E), F(s=R_RISER, e=R_RISER, u=R_RISER)
    ring = F(s=(48, 0, 60, 3), e=(48, 0, 60, 3), u=R_IRON_S)
    m.box("handle", "grip_lower", [7.3, -11.8, 7.4], [8.7, -7.2, 8.6], grip)
    m.box("handle", "grip_riser_lower", [7.22, -9.65, 7.32], [8.78, -9.35, 8.68], riser)
    m.box("handle", "grip_ring_middle", [7.15, -7.2, 7.25], [8.85, -6.7, 8.75], ring)
    m.box("handle", "grip_upper", [7.3, -6.7, 7.4], [8.7, -2.4, 8.6], grip)
    m.box("handle", "grip_riser_upper", [7.22, -4.75, 7.32], [8.78, -4.45, 8.68], riser)
    m.box("handle", "grip_ring_top", [7.15, -2.4, 7.25], [8.85, -2.0, 8.75], ring)

    # crossguard: straight inner quillons, outer halves canted towards the blade
    m.group("guard", [8, -1.25, 8])
    cant = 12 if k.FREE_ROT else 22.5
    m.box("guard", "guard_block", [6.6, -2.0, 7.0], [9.4, -0.5, 9.0], F(s=R_GBLOCK, e=R_GBLOCK, u=R_IRON))
    m.box("guard", "guard_rivet", [7.6, -1.65, 6.9], [8.4, -0.85, 9.1], F(s=R_STUD, e=R_IRON_S, u=R_IRON_S))
    m.box("guard", "langet", [7.0, -0.5, 7.45], [9.0, 1.6, 8.55], F(s=R_LANGET, e=R_IRON_S, u=R_IRON_S))
    for side, sx in (("left", -1), ("right", 1)):
        def span(a, b):  # distances from the centre line, mirrored for the right side
            return sorted((8 + sx * a, 8 + sx * b))
        def face(r):
            return r if sx < 0 else flipu(r)
        rot = ("z", sx * cant, [8 + sx * 4.4, -1.25, 8])
        (x0, x1) = span(1.4, 4.4)
        m.box("guard", f"quillon_{side}_inner", [x0, -1.8, 7.25], [x1, -0.7, 8.75],
              F(s=face(flipu(R_QUIL_IN)), e=R_IRON_S, u=face(flipu(R_QUIL_IN))))
        (x0, x1) = span(4.3, 6.8)
        m.box("guard", f"quillon_{side}_outer", [x0, -1.7, 7.35], [x1, -0.8, 8.65],
              F(s=face(flipu(R_QUIL_OUT)), e=R_IRON_S, u=face(flipu(R_QUIL_OUT))), rot)
        (x0, x1) = span(6.5, 7.3)
        m.box("guard", f"quillon_{side}_cap", [x0, -1.95, 7.2], [x1, -0.55, 8.8], F(s=R_CAP, e=R_CAP, u=R_CAP), rot)

    m.group("blade", [8, Y0, 8])
    m.box("blade", "fuller", [7.25, Y0, 7.72], [8.75, FULLER_END, 8.28], F(s=(7, vb(FULLER_END), 13, vb(Y0))))
    m.box("blade", "blade_core_upper", [7.25, FULLER_END, 7.55], [8.75, TAPER_Y, 8.45],
          F(s=(7, vb(TAPER_Y), 13, vb(FULLER_END)), d=R_STEEL))
    for i, (y0, y1, w) in enumerate(SEGMENTS):
        v1, v2 = vb(y1), vb(y0)
        l, r = 8 - w / 2, 8 + w / 2
        shoulder = (24, v1, 26, v2)
        m.box("blade", f"blade_{i + 1}_flat_left", [l + 0.5, y0, 7.55], [7.25, y1, 8.45],
              F(s=(2, v1, 7, v2), e=shoulder, u=R_STEEL))
        m.box("blade", f"blade_{i + 1}_flat_right", [8.75, y0, 7.55], [r - 0.5, y1, 8.45],
              F(s=(13, v1, 18, v2), e=shoulder, u=R_STEEL))
        m.box("blade", f"blade_{i + 1}_edge_left", [l, y0, 7.85], [l + 0.5, y1, 8.15],
              F(s=(0, v1, 2, v2), w=(22, v1, 23, v2), u=R_STEEL))
        m.box("blade", f"blade_{i + 1}_edge_right", [r - 0.5, y0, 7.85], [r, y1, 8.15],
              F(s=(18, v1, 20, v2), e=(23, v1, 24, v2), u=R_STEEL))
    for j, (y0, y1, w, zh) in enumerate(TIP):
        v1, v2 = vb(y1), vb(y0)
        m.box("blade", f"tip_{j + 1}", [8 - w / 2, y0, 8 - zh], [8 + w / 2, y1, 8 + zh],
              F(s=(10 - 2 * w, v1, 10 + 2 * w, v2), e=(26, v1, 27, v2), u=R_STEEL))
    lug = F(s=R_LUG, e=R_LUG, u=R_LUG)
    m.box("blade", "parry_lug_left", [4.9, 3.0, 7.7], [5.8, 3.9, 8.3], lug)
    m.box("blade", "parry_lug_right", [10.2, 3.0, 7.7], [11.1, 3.9, 8.3], lug)

    # tattered favour tied under the guard
    m.group("cloth", [8.9, -3.0, 8])
    m.box("cloth", "cloth_band", [7.2, -3.4, 7.3], [8.8, -2.7, 8.7], F(s=R_CLOTH_BAND, e=R_CLOTH_BAND, u=R_CLOTH_BAND))
    m.box("cloth", "cloth_tail_long", [8.75, -5.4, 7.85], [9.35, -3.0, 8.15],
          F(s=R_CLOTH, e=R_CLOTH_E), ("z", 22.5, [9.05, -3.0, 8]))
    m.box("cloth", "cloth_tail_short", [8.8, -4.6, 8.2], [9.3, -3.1, 8.4],
          F(s=(62, 8, 68, 24), e=R_CLOTH_E), ("z", 45, [9.05, -3.1, 8.3]))
    return m


def idle_animation(m):
    """Stored in the Blockbench project only; Java item models cannot play it."""
    frames = [(0, 0, 0), (1, 4, 10), (2, 0, 0), (3, -4, -10), (4, 0, 0)]
    keys = [{"channel": "rotation", "data_points": [{"x": str(x), "y": "0", "z": str(z)}],
             "uuid": k.uid(NAME, "kf", "cloth", str(t)), "time": t, "color": -1, "interpolation": "catmullrom"}
            for t, x, z in frames]
    return [{"uuid": k.uid(NAME, "anim", "idle"), "name": "idle", "loop": "loop", "override": False, "length": 4,
             "snapping": 24, "selected": False, "anim_time_update": "", "blend_weight": "", "start_delay": "",
             "loop_delay": "",
             "animators": {k.uid(NAME, "group", "cloth"): {"name": "cloth", "type": "bone", "keyframes": keys}}}]


def preview(mj, texs):
    cv = Canvas(1000, 800, (40, 40, 44, 255))
    side = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    quarter = k.mm(k.rotm("x", 14), k.rotm("y", -52))
    s = k.DISPLAY["gui"]["scale"][0]
    gui = k.mm([[s * (i == j) for j in range(3)] for i in range(3)], k.rotm("z", -45))
    k.render(cv, 0, 0, 300, 800, mj, texs, side, 16, 0)
    k.render(cv, 300, 0, 300, 800, mj, texs, quarter, 16, 0)
    k.render(cv, 600, 0, 400, 500, mj, texs, side, 24, 0, shift=(0, 13))  # hilt close-up
    k.render(cv, 600, 500, 400, 300, mj, texs, gui, 16, 0)
    return cv


def main():
    base = paint()
    pngs = {NAME: k.png_bytes(base.px, 128, 128)}
    k.write(f"resourcepack/assets/{NS}/textures/item/{NAME}.png", pngs[NAME])

    m = build()
    mj = k.model_json(m)
    mj["credit"] = "Warrior Greatsword - generated by tools/build_greatsword.py"
    k.write(f"resourcepack/assets/{NS}/models/item/{NAME}.json", mj)
    bb = k.bbmodel(m, pngs)
    bb["unhandled_root_fields"] = {"credit": "Warrior Greatsword"}
    bb["animations"] = idle_animation(m)
    k.write(f"blockbench/{NAME}.bbmodel", json.dumps(bb))
    k.write(f"resourcepack/assets/{NS}/items/{NAME}.json",
            {"model": {"type": "minecraft:model", "model": f"{NS}:item/{NAME}"}})

    lo = [min(min(c["frm"][i], c["to"][i]) for c in m.cubes()) for i in range(3)]
    hi = [max(max(c["frm"][i], c["to"][i]) for c in m.cubes()) for i in range(3)]
    print(f"{NAME}: {len(m.cubes())} cubes, groups {list(m.groups)}, bounds {k.r4(lo)} .. {k.r4(hi)}")

    sheet = preview(mj, {"#0": ([base], 128)})
    k.write(f"preview/{NAME}_preview.png", k.png_bytes(sheet.px, sheet.w, sheet.h))
    big = Canvas(512, 512, (40, 40, 44, 255))
    big.rect(0, 0, 512, 512, lambda x, y: base.px[y // 4][x // 4] if base.px[y // 4][x // 4][3] else (40, 40, 44, 255))
    k.write(f"preview/{NAME}_texture_4x.png", k.png_bytes(big.px, 512, 512))


if __name__ == "__main__":
    main()
