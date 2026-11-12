#!/usr/bin/env python3
"""Generates the Sakura Katana resource pack, Blockbench projects and preview sheet.

Pure standard library. Run from anywhere:  python3 tools/build_katana.py
Pass --legacy-rotation to restrict element rotations to 22.5 degree steps
(for clients older than 1.21.11); the blade curve is then stepped instead of smooth.
"""
import base64, json, math, os, struct, sys, uuid, zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NS = "sakura"
FREE_ROT = "--legacy-rotation" not in sys.argv
PACK_FORMAT = 75  # Java Edition 1.21.11

# ---------------------------------------------------------------- palette
HA, HAMON, HIRA = (250, 240, 246), (255, 206, 226), (216, 198, 212)
RIDGE, SPINE, SPINE_D = (242, 232, 240), (170, 154, 174), (138, 124, 150)
ETCH = (192, 118, 154)
CRIM, CRIM_D, CRIM_L = (150, 24, 58), (104, 14, 42), (194, 52, 88)
SAME = (250, 216, 228)
GOLD, GOLD_L, GOLD_D = (232, 184, 74), (255, 228, 142), (168, 116, 40)
PEARL, PEARL_S = (251, 245, 241), (224, 208, 214)
PINK, PINK_D, PINK_L = (255, 183, 213), (232, 120, 166), (255, 228, 240)
LACQ, LACQ_L = (50, 14, 34), (118, 38, 78)
WHITE = (255, 242, 248)


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def hsh(x, y):
    n = (x * 73856093) ^ (y * 19349663)
    n = (n ^ (n >> 13)) * 1274126177
    return ((n ^ (n >> 16)) & 255) / 255.0


# ---------------------------------------------------------------- canvas / png
class Canvas:
    def __init__(self, w, h, fill=(0, 0, 0, 0)):
        self.w, self.h = w, h
        self.px = [[fill] * w for _ in range(h)]

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y][x] = tuple(c) if len(c) == 4 else (c[0], c[1], c[2], 255)

    def rect(self, x0, y0, x1, y1, fn):
        for y in range(y0, y1):
            for x in range(x0, x1):
                self.set(x, y, fn(x - x0, y - y0) if callable(fn) else fn)


def png_bytes(rows, w, h):
    raw = b"".join(b"\x00" + bytes(c for p in row for c in p) for row in rows)

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def frames_png(frames):
    rows = [r for f in frames for r in f.px]
    return png_bytes(rows, frames[0].w, len(rows))


# ---------------------------------------------------------------- petal shapes
def petal_in(u, v):
    """u across [-1,1], v from root (0) to notched tip (1)."""
    if v < 0 or v > 1:
        return False
    wd = math.sqrt(max(0.0, 1 - ((v - 0.58) / 0.58) ** 2)) * min(1.0, 0.3 + v / 0.3)
    if abs(u) > wd:
        return False
    return not (v > 0.8 and abs(u) < (v - 0.8) * 1.1)


def draw_petal(cv, cx, cy, hw, ln, ang, col):
    dx, dy = math.cos(ang), math.sin(ang)
    r = int(ln + hw + 2)
    for y in range(int(cy) - r, int(cy) + r + 1):
        for x in range(int(cx) - r, int(cx) + r + 1):
            px, py = x + 0.5 - cx, y + 0.5 - cy
            v, u = (px * dx + py * dy) / ln, (-px * dy + py * dx) / hw
            if petal_in(u, v):
                cv.set(x, y, col(u, v) if callable(col) else col)


def draw_blossom(cv, cx, cy, r, col, center=None):
    for k in range(5):
        draw_petal(cv, cx, cy, r * 0.5, r, -math.pi / 2 + k * 2 * math.pi / 5, col)
    if center:
        cv.set(int(cx), int(cy), center)


def hamon(s):
    """Hamon boundary (texel column from the edge) at blade arclength s: petal-edge scallops."""
    return 1.3 + 1.9 * abs(math.sin(s * math.pi / 2.2)) ** 0.8


HAMON_S = (2.6, 18.0)

# ---------------------------------------------------------------- texture regions (texels)
H_NS, H_EW = (0, 0, 12, 24), (12, 0, 20, 24)
R_GOLD, R_GOLD_E, R_GOLDF = (0, 26, 12, 30), (12, 26, 16, 30), (0, 31, 4, 34)
R_HABAKI, R_HABAKI_E = (0, 36, 16, 44), (0, 36, 6, 44)
R_POMMEL, R_PEARL, R_PEARL2 = (0, 46, 14, 55), (16, 46, 20, 50), (16, 50, 20, 53)
R_CORD, R_TUFT, R_TUFT_TIP = (0, 58, 3, 74), (6, 58, 12, 70), (6, 70, 12, 74)
R_CRIM, R_PINKSW = (0, 76, 2, 78), (8, 76, 10, 78)
R_TPETAL_P, R_TPETAL_W = (14, 58, 22, 66), (14, 68, 22, 76)
R_STEEL = (50, 2, 52, 4)
R_CENTER, R_PINKSIDE = (76, 0, 88, 12), (76, 14, 80, 18)
R_LACQ = (114, 2, 116, 4)
PV = (56, 0)   # tsuba petal, tip up, 16x20
PH = (56, 22)  # tsuba petal, tip right, 20x16


def paint_base():
    cv = Canvas(128, 128)

    # handle wrap: crimson braid crossing over pale ray skin diamonds
    def wrap(cxm, half):
        def fn(x, y):
            d = abs(x + 0.5 - cxm) / half + abs((y % 8) + 0.5 - 4) / 4
            if d < 0.55:
                return mix(SAME, PINK, 0.5 if (x + y) % 2 else 0.0)
            if d < 0.72:
                return CRIM_D
            diag = (x + y) if ((x + 0.5 < cxm) == ((y % 8) < 4)) else (x - y)
            return CRIM_L if diag % 3 == 0 else CRIM
        return fn
    cv.rect(0, 0, 12, 24, wrap(6, 6))
    cv.rect(12, 0, 20, 24, lambda x, y: wrap(4, 4)(x, y + 4))

    gold_rows = [GOLD_L, mix(GOLD_L, GOLD, 0.6), GOLD, GOLD_D]
    cv.rect(0, 26, 16, 30, lambda x, y: mix(gold_rows[y], GOLD_L, 0.5 if x in (3, 4) else 0))
    cv.rect(0, 31, 4, 34, lambda x, y: mix(GOLD, GOLD_L, hsh(x, y) * 0.4))
    cv.rect(0, 36, 16, 44, lambda x, y: GOLD_D if (x + y) % 4 == 0 else mix(GOLD_L, GOLD, y / 7))

    # pommel: pearl cap with a single engraved petal
    cv.rect(0, 46, 14, 55, lambda x, y: mix(PEARL, PEARL_S, y / 9 + (0.3 if x in (0, 13) else 0)))
    draw_petal(cv, 7, 54, 3.4, 7.5, -math.pi / 2, PINK_D)
    draw_petal(cv, 7, 53.2, 2.2, 5.6, -math.pi / 2, lambda u, v: mix(PINK, PINK_L, v))
    cv.rect(16, 46, 20, 50, lambda x, y: mix(PEARL, PEARL_S, y / 5))
    cv.rect(16, 50, 20, 53, lambda x, y: mix(PEARL_S, GOLD_L, 0.25 + y / 6))

    # tassel
    cv.rect(0, 58, 3, 74, lambda x, y: CRIM_L if (x + y) % 3 == 0 else CRIM)
    cv.rect(6, 58, 12, 74, lambda x, y: mix(CRIM if x % 2 else CRIM_D, PINK, (y - 9) / 6))
    cv.rect(0, 76, 2, 78, CRIM)
    cv.rect(8, 76, 10, 78, PINK)
    draw_petal(cv, 18, 66, 3.6, 8, -math.pi / 2, lambda u, v: mix(PINK_D, PINK_L, v * 1.1))
    draw_petal(cv, 18, 76, 3.6, 8, -math.pi / 2, lambda u, v: mix(PINK, WHITE, v * 1.4))

    # blade strip: column 0 is the cutting edge, row 0 is the tip (4 texels per model pixel)
    for row in range(80):
        s = (80 - row - 0.5) / 4
        for c in range(8):
            n = hsh(c, row)
            if c >= 6:
                col = mix(SPINE, SPINE_D, (c - 6) * 0.6 + n * 0.2)
            elif c == 5:
                col = RIDGE
            elif s < HAMON_S[0]:
                col = mix(HIRA, (198, 180, 198), n * 0.3)
            elif s >= HAMON_S[1]:
                col = mix(HA, (255, 255, 255), n * 0.4)
            else:
                h = int(hamon(s))
                col = (mix(HA, (255, 252, 254), n * 0.5) if c < h else HAMON if c == h
                       else mix(HIRA, (204, 186, 206), n * 0.35))
            cv.set(32 + c, 2 + row, col)
    for c in range(5):
        cv.set(32 + c, 2 + 80 - int(HAMON_S[0] * 4) - 1, mix(HIRA, SPINE, 0.6))  # machi
        cv.set(32 + c, 2 + 80 - int(HAMON_S[1] * 4), mix(HA, SPINE, 0.35))       # yokote
    draw_blossom(cv, 34.6, 76.4, 2.6, ETCH, PINK_L)  # ricasso etching
    cv.rect(42, 2, 44, 82, lambda x, y: mix(SPINE, SPINE_D, x * 0.5 + hsh(x, y) * 0.3))
    cv.rect(45, 2, 46, 82, (255, 250, 252))
    cv.rect(47, 2, 48, 82, RIDGE)
    cv.rect(50, 2, 52, 4, mix(HIRA, SPINE, 0.3))

    # tsuba petal (tip up) and its transposed copy (tip right)
    def petal_tex(x, y):
        v, u = 1 - (y + 0.5) / 20, (x + 0.5 - 8) / 8
        col = mix(PINK_D, PINK_L, v ** 0.8)
        if abs(u) > 0.8:
            col = mix(col, PINK_D, 0.35)
        if abs(u) < 0.1 and v < 0.75:
            col = mix(col, PINK_D, 0.4)
        if v > 0.85 and abs(u) < (v - 0.85) * 2.2 + 0.07:
            col = mix(PINK_D, CRIM_L, 0.3)
        if v < 0.34 and (abs(u) < 0.1 or abs(abs(u) - 0.25 - v * 0.6) < 0.09):
            col = GOLD
        if abs(v - 0.4) < 0.04 and abs(u) < 0.14:
            col = GOLD_L
        return col
    cv.rect(PV[0], PV[1], PV[0] + 16, PV[1] + 20, petal_tex)
    cv.rect(PH[0], PH[1], PH[0] + 20, PH[1] + 16, lambda x, y: petal_tex(y, 19 - x))

    def center_tex(x, y):
        dx, dy = x + 0.5 - 6, y + 0.5 - 6
        r, a = math.hypot(dx, dy) / 6, math.atan2(dy, dx)
        if r < 0.3:
            return GOLD_L
        if r < 0.55:
            return GOLD if int((a + math.pi) * 5 / math.pi) % 2 else GOLD_D
        if abs(r - 0.78) < 0.1 and math.cos(a * 5) > 0.55:
            return GOLD_L
        return mix(PINK_D, PINK, min(1, (r - 0.55) * 1.6))
    cv.rect(76, 0, 88, 12, center_tex)
    cv.rect(76, 14, 80, 18, lambda x, y: mix(PINK, PINK_D, y / 3))

    # saya: dark cherry lacquer with gold blossoms
    cv.rect(96, 2, 106, 86, lambda x, y: mix(LACQ, LACQ_L, math.exp(-((x - 3) ** 2) / 2.5) * 0.8 + hsh(x, y) * 0.06))
    for k in range(6):
        cy = 12 + 13 * k
        draw_blossom(cv, 99.5 + (3.2 if k % 2 else 0), cy, 3.2, GOLD, GOLD_L)
        draw_petal(cv, 103.5 - (5 if k % 2 else 0), cy + 6.5, 1.1, 2.6, k * 1.9, mix(GOLD, GOLD_D, 0.3))
    cv.rect(108, 2, 112, 86, lambda x, y: mix(LACQ, LACQ_L, 0.5 if x == 1 else 0.05))
    cv.rect(114, 2, 116, 4, LACQ)
    return cv


def paint_emissive(nframes=8):
    """Hamon glow, laid out exactly like the base sheet so it works as an emissive layer."""
    frames = []
    for f in range(nframes):
        cv = Canvas(128, 128)
        for row in range(80):
            s = (80 - row - 0.5) / 4
            if not (HAMON_S[0] <= s < HAMON_S[1]):
                continue
            wave = 0.5 + 0.5 * math.sin(2 * math.pi * (s / 6 - f / nframes))
            h = int(hamon(s))
            cv.set(32 + h, 2 + row, mix((255, 150, 198), (255, 250, 253), wave))
            if wave > 0.6 and h > 1:
                cv.set(32 + h - 1, 2 + row, mix((255, 196, 222), (255, 236, 244), wave))
        frames.append(cv)
    return frames


PET_TIP_A, PET_TIP_B = (10, 5), (16, 5)  # blade tip inside each 32x32 petal region


def paint_petals(nframes=16):
    frames = []
    for f in range(nframes):
        cv = Canvas(64, 64)
        for k in range(10):
            b = k >= 5
            t = (f / nframes + (k % 5) / 5 + (0.1 if b else 0)) % 1
            sway = 2.2 * math.sin(2 * math.pi * (t * 1.5 + k * 0.31))
            if b:
                x = 32 + PET_TIP_B[0] + (11 * t) * (1 if k % 2 else -1) + sway
                y = PET_TIP_B[1] + 24 * t
            else:
                x = PET_TIP_A[0] + 15 * t + sway
                y = PET_TIP_A[1] + 24 * t
            size = min(1.0, 0.35 + t * 5) * (1 - max(0.0, t - 0.7) * 2.2)
            c0, c1 = ((PINK_D, PINK_L) if k % 2 else (PINK, WHITE))
            draw_petal(cv, x, y, 1.9 * size, 4.2 * size, 2 * math.pi * (t * 1.2 + k * 0.37),
                       lambda u, v, c0=c0, c1=c1: mix(c0, c1, v * 1.2))
        frames.append(cv)
    return frames


# ---------------------------------------------------------------- model
def flipu(r):
    return (r[2], r[1], r[0], r[3])


def flipv(r):
    return (r[0], r[3], r[2], r[1])


def F(s=None, e=None, u=None, n=None, w=None, d=None, tex=0):
    """Face map from texel rects. north mirrors south, west reuses east, down mirrors up."""
    out = {"north": n or (flipu(s) if s else None), "south": s, "east": e, "west": w or e,
           "up": u, "down": d or (flipv(u) if u else None)}
    return {k: (tex, r) for k, r in out.items() if r}


class Model:
    def __init__(self, name):
        self.name, self.groups = name, {}

    def group(self, g, origin):
        self.groups[g] = {"origin": origin, "cubes": []}

    def box(self, g, name, frm, to, faces, rot=None, light=0):
        self.groups[g]["cubes"].append(dict(name=name, frm=frm, to=to, faces=faces, rot=rot, light=light))

    def cubes(self):
        return [c for g in self.groups.values() for c in g["cubes"]]


def blade_chain(y0, n=6, seg=3.0, k=0.007):
    """Curved centreline: list of (x, y, tangent_deg, arclength) for n segments plus the tip piece."""
    out, x, y = [], 8.0, y0
    for i in range(n + 1):
        s0 = i * seg
        if FREE_ROT:
            th = math.atan(k * (s0 + (seg / 2 if i < n else 1.0)))
            out.append((x, y, math.degrees(th), s0))
            x, y = x + seg * math.sin(th), y + seg * math.cos(th)
        else:
            out.append((8.0 + k / 2 * s0 * s0, y0 + s0, 0.0, s0))
    return out


def build(sheathed):
    m = Model("sakura_katana_sheathed" if sheathed else "sakura_katana")

    m.group("pommel", [8, -4, 8])
    m.box("pommel", "kashira_cap", [7.15, -5.1, 7.4], [8.85, -4.0, 8.6], F(s=R_POMMEL, e=R_PEARL, u=R_PEARL))
    m.box("pommel", "kashira_tip", [7.4, -5.5, 7.55], [8.6, -5.1, 8.45], F(s=R_PEARL2, e=R_PEARL2, u=R_PEARL2))
    m.box("pommel", "tassel_ring", [7.75, -5.8, 7.8], [8.25, -5.5, 8.2], F(s=R_GOLDF, e=R_GOLDF, u=R_GOLDF))

    m.group("handle", [8, -0.5, 8])
    gold = F(s=R_GOLD, e=R_GOLD_E, u=R_GOLDF)
    wrap = F(s=H_NS, e=H_EW)
    m.box("handle", "band_bottom", [7.2, -4.0, 7.45], [8.8, -3.6, 8.55], gold)
    m.box("handle", "wrap_lower", [7.25, -3.6, 7.5], [8.75, -0.7, 8.5], wrap)
    m.box("handle", "band_middle", [7.2, -0.7, 7.45], [8.8, -0.4, 8.55], gold)
    m.box("handle", "wrap_upper", [7.25, -0.4, 7.5], [8.75, 2.5, 8.5], wrap)
    m.box("handle", "fuchi", [7.15, 2.5, 7.4], [8.85, 3.0, 8.6], gold)

    # tsuba: five two-part petals around a gold-inlaid centre
    m.group("tsuba", [8, 3.375, 8])
    m.box("tsuba", "tsuba_center", [6.9, 3.0, 6.9], [9.1, 3.75, 9.1], F(s=R_PINKSIDE, e=R_PINKSIDE, u=R_CENTER))
    split = 20 * 0.7 / 1.9
    pv_in, pv_tip = (PV[0], PV[1] + split, PV[0] + 16, PV[1] + 20), (PV[0] + 2.8, PV[1], PV[0] + 13.2, PV[1] + split)
    ph_in, ph_tip = (PH[0], PH[1], PH[0] + 20 - split, PH[1] + 16), (PH[0] + 20 - split, PH[1] + 2.8, PH[0] + 20, PH[1] + 13.2)
    for i in range(5):
        phi = 90 + 72 * i               # direction in the XZ plane, measured from +X towards +Z
        base = round(phi / 90) * 90
        theta = base - phi              # Ry(theta) turns a direction by -theta
        if not FREE_ROT:
            theta = round(theta / 22.5) * 22.5
        base %= 360
        for part, r0, r1, hw, yin in (("", 0.8, 2.0, 0.85, 0.06), ("_tip", 2.0, 2.7, 0.55, 0.1)):
            lo, hi = (8 + r0, 8 + r1) if base in (0, 90) else (8 - r1, 8 - r0)
            y0, y1 = 3.0 + yin + 0.012 * i, 3.75 - yin - 0.012 * i  # staggered: overlapping petals must not be coplanar
            if base in (0, 180):
                frm, to = [lo, y0, 8 - hw], [hi, y1, 8 + hw]
                up = ph_tip if part else ph_in
                up = up if base == 0 else flipu(up)
            else:
                frm, to = [8 - hw, y0, lo], [8 + hw, y1, hi]
                up = pv_tip if part else pv_in
                up = up if base == 270 else flipv(up)
            m.box("tsuba", f"petal_{i + 1}{part}", frm, to, F(s=R_PINKSIDE, e=R_PINKSIDE, u=up),
                  rot=("y", theta, [8, 3.375, 8]) if theta else None)

    def vb(s):
        return 82 - 4 * s

    if not sheathed:
        m.group("blade", [8, 3.75, 8])
        m.box("blade", "habaki", [6.9, 3.75, 7.6], [9.1, 4.75, 8.4], F(s=R_HABAKI, e=R_HABAKI_E, u=R_GOLDF))
        chain = blade_chain(4.5)
        for i, (px, py, th, s0) in enumerate(chain[:-1]):
            w = 2.0 - 0.07 * i
            e, y1 = px - w / 2, py + 3.03
            v1, v2 = vb(s0 + 3), vb(s0)
            rot = ("z", -th, [px, py, 8]) if th else None
            edge_w, spine_e = (45, v1, 46, v2), (42, v1, 44, v2)
            m.box("blade", f"blade_{i + 1}_edge", [e, py, 7.9], [e + 0.25, y1, 8.1],
                  F(s=(32, v1, 33, v2), w=edge_w, u=R_STEEL), rot)
            m.box("blade", f"blade_{i + 1}_body", [e + 0.25, py, 7.8], [e + w, y1, 8.2],
                  F(s=(33, v1, 32 + 4 * w, v2), e=spine_e, w=edge_w, u=R_STEEL), rot)
            m.box("blade", f"blade_{i + 1}_shinogi", [e + 1.25, py, 7.7], [e + 1.55, y1, 8.3],
                  F(s=(37, v1, 38.2, v2), e=(47, v1, 48, v2), u=R_STEEL), rot)
            m.box("blade", f"hamon_glow_{i + 1}", [e + 0.25, py, 7.78], [e + 1.25, y1, 8.22],
                  F(s=(33, v1, 37, v2), tex=1), rot, light=15)
        px, py, th, s0 = chain[-1]
        w = 1.58
        e = px - w / 2
        rot = ("z", -th, [px, py, 8]) if th else None
        for j, (lx, l0, l1, zh) in enumerate(((0.15, 0, 0.8, 0.15), (0.6, 0.8, 1.4, 0.12), (1.1, 1.4, 2.0, 0.1))):
            v1, v2 = vb(s0 + l1), vb(s0 + l0)
            m.box("blade", f"kissaki_{j + 1}", [e + lx, py + l0, 8 - zh], [e + w, py + l1 + 0.01, 8 + zh],
                  F(s=(32 + 4 * lx, v1, 32 + 4 * w, v2), e=(42, v1, 44, v2), w=(45, v1, 46, v2), u=R_STEEL), rot)
        a = math.radians(th)
        tx, ty = px + 2 * math.sin(a), py + 2 * math.cos(a)

        # animated emissive planes standing in for particles (item models cannot spawn real ones)
        m.group("petals", [tx, ty, 8])
        x0, yt = tx - PET_TIP_A[0] / 32 * 6, ty + PET_TIP_A[1] / 32 * 6
        m.box("petals", "petal_drift_side", [x0, yt - 6, 7.99], [x0 + 6, yt, 8.01],
              F(s=(0, 0, 32, 32), tex=2), light=15)
        m.box("petals", "petal_drift_front", [tx - 0.01, yt - 6, 5], [tx + 0.01, yt, 11],
              F(e=(32, 0, 64, 32), tex=2), light=15)
    else:
        m.group("saya", [8, 3.75, 8])

        def vs(s):
            return 86 - 4 * s
        chain = blade_chain(3.75)
        m.box("saya", "koiguchi", [6.65, 3.75, 7.4], [9.35, 4.3, 8.6], gold)
        for i, (px, py, th, s0) in enumerate(chain):
            rot = ("z", -th, [px, py, 8]) if th else None
            ln = 3.0 if i < 6 else 1.7
            m.box("saya", f"saya_{i + 1}", [px - 1.25, py, 7.45], [px + 1.25, py + ln + 0.03, 8.55],
                  F(s=(96, vs(s0 + ln), 106, vs(s0)), e=(108, vs(s0 + ln), 112, vs(s0)), u=R_LACQ), rot)
        m.box("saya", "kojiri", [px - 1.1, py + 1.7, 7.52], [px + 1.1, py + 2.6, 8.48], gold, rot)
        px, py, th, _ = chain[1]
        rot = ("z", -th, [px, py, 8]) if th else None
        m.box("saya", "sageo_band", [px - 1.3, py + 0.6, 7.4], [px + 1.3, py + 1.0, 8.6],
              F(s=(0, 58, 3, 62), e=(0, 58, 3, 62), u=R_CRIM), rot)
        m.box("saya", "kurigata", [px - 0.3, py + 0.3, 8.55], [px + 0.3, py + 1.3, 8.85],
              F(s=R_GOLDF, e=R_GOLDF, u=R_GOLDF), rot)
        ky = py + 0.5
        m.box("saya", "sageo_cord", [px - 0.15, ky - 1.8, 8.6], [px + 0.15, ky, 8.9],
              F(s=R_CORD, e=R_CORD, u=R_CRIM), ("z", -22.5, [px, ky, 8.75]))
        ex, ey = px - 1.8 * math.sin(math.radians(22.5)), ky - 1.8 * math.cos(math.radians(22.5))
        m.box("saya", "sageo_tuft", [ex - 0.3, ey - 1.2, 8.45], [ex + 0.3, ey, 9.05],
              F(s=(6, 58, 12, 74), e=(6, 58, 12, 74), u=R_PINKSW), ("z", -22.5, [ex, ey, 8.75]))

    # tassel trails from the pommel ring towards the edge side
    m.group("tassel", [8, -5.65, 8])
    m.box("tassel", "tassel_cord", [7.85, -7.3, 7.85], [8.15, -5.7, 8.15],
          F(s=R_CORD, e=R_CORD, u=R_CRIM), ("z", -22.5, [8, -5.7, 8]))
    kx, ky = 8 - 1.6 * math.sin(math.radians(22.5)), -5.7 - 1.6 * math.cos(math.radians(22.5))
    m.box("tassel", "tassel_knot", [kx - 0.27, ky - 0.27, 7.73], [kx + 0.27, ky + 0.27, 8.27],
          F(s=R_GOLDF, e=R_GOLDF, u=R_GOLDF), ("z", 45, [kx, ky, 8]))
    m.box("tassel", "tassel_tuft", [kx - 0.32, ky - 1.5, 7.68], [kx + 0.32, ky - 0.2, 8.32],
          F(s=R_TUFT, e=R_TUFT, u=R_CRIM), ("z", -45, [kx, ky, 8]))
    m.box("tassel", "tassel_tuft_tip", [kx - 0.24, ky - 1.9, 7.76], [kx + 0.24, ky - 1.5, 8.24],
          F(s=R_TUFT_TIP, e=R_TUFT_TIP, u=R_PINKSW), ("z", -45, [kx, ky, 8]))
    for nm, cx, cy, ang, r in (("pink", kx + 0.25, ky - 1.25, 22.5, R_TPETAL_P), ("white", kx - 1.45, ky - 0.35, -45, R_TPETAL_W)):
        m.box("tassel", f"tassel_petal_{nm}", [cx - 0.45, cy - 0.45, 7.98], [cx + 0.45, cy + 0.45, 8.02],
              F(s=r), ("z", ang, [cx, cy, 8]))
    return m


DISPLAY = {
    "thirdperson_righthand": {"rotation": [0, -90, 10], "translation": [0, 5.25, 0.25], "scale": [0.85] * 3},
    "firstperson_righthand": {"rotation": [0, -90, -20], "translation": [1.13, 4.15, 1.5], "scale": [0.68] * 3},
    "gui": {"rotation": [0, 0, -45], "translation": [0, 0, 0], "scale": [0.6] * 3},
    "ground": {"rotation": [0, 0, -45], "translation": [0, 2, 0], "scale": [0.5] * 3},
    "fixed": {"rotation": [0, 180, -45], "translation": [0, 0, 0], "scale": [0.8] * 3},
    "head": {"rotation": [0, 0, -45], "translation": [0, 13, 0], "scale": [0.8] * 3},
}

TEXTURES = [  # id, file, frame size, frametime (ticks), interpolate
    ("0", "sakura_katana", 128, 0, False),
    ("1", "sakura_katana_e", 128, 3, True),
    ("2", "sakura_petals", 64, 2, False),
]


def r4(v):
    return [round(x, 4) for x in v]


def model_json(m):
    used = sorted({t for c in m.cubes() for t, _ in c["faces"].values()})
    tex = {TEXTURES[t][0]: f"{NS}:item/{TEXTURES[t][1]}" for t in used}
    tex["particle"] = f"{NS}:item/{TEXTURES[0][1]}"
    elements, groups, idx = [], [], 0
    for gname, g in m.groups.items():
        groups.append({"name": gname, "origin": r4(g["origin"]), "color": 0,
                       "children": list(range(idx, idx + len(g["cubes"])))})
        idx += len(g["cubes"])
        for c in g["cubes"]:
            el = {"name": c["name"], "from": r4(c["frm"]), "to": r4(c["to"])}
            if c["rot"]:
                el["rotation"] = {"angle": round(c["rot"][1], 3), "axis": c["rot"][0], "origin": r4(c["rot"][2])}
            if c["light"]:
                el["light_emission"] = c["light"]
            el["faces"] = {f: {"uv": r4([x * 16 / TEXTURES[t][2] for x in r]), "texture": f"#{TEXTURES[t][0]}"}
                           for f, (t, r) in c["faces"].items()}
            elements.append(el)
    return {"credit": "Sakura Katana - generated by tools/build_katana.py", "texture_size": [128, 128],
            "textures": tex, "gui_light": "front", "elements": elements, "display": DISPLAY, "groups": groups}


def uid(*parts):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, "sakura-katana/" + "/".join(parts)))


def bbmodel(m, pngs):
    used = sorted({t for c in m.cubes() for t, _ in c["faces"].values()})
    remap = {t: i for i, t in enumerate(used)}
    elements, outliner = [], []
    for gname, g in m.groups.items():
        children = []
        for c in g["cubes"]:
            rot = [0, 0, 0]
            if c["rot"]:
                rot["xyz".index(c["rot"][0])] = round(c["rot"][1], 3)
            faces = {f: {"uv": [0, 0, 0, 0], "texture": None} for f in ("north", "east", "south", "west", "up", "down")}
            for f, (t, r) in c["faces"].items():
                faces[f] = {"uv": r4(r), "texture": remap[t]}
            u = uid(m.name, "cube", c["name"])
            children.append(u)
            elements.append({"name": c["name"], "box_uv": False, "rescale": False, "locked": False,
                             "light_emission": c["light"], "render_order": "default", "allow_mirror_modeling": True,
                             "from": r4(c["frm"]), "to": r4(c["to"]), "autouv": 0, "color": 0,
                             "origin": r4(c["rot"][2]) if c["rot"] else r4(g["origin"]), "rotation": rot,
                             "faces": faces, "type": "cube", "uuid": u})
        outliner.append({"name": gname, "origin": r4(g["origin"]), "color": 0, "uuid": uid(m.name, "group", gname),
                         "export": True, "isOpen": False, "locked": False, "visibility": True, "autouv": 0,
                         "children": children})
    textures = []
    for t in used:
        tid, name, size, ft, interp = TEXTURES[t]
        data = pngs[name]
        textures.append({"path": "", "name": name + ".png", "folder": "item", "namespace": NS, "id": tid,
                         "width": size, "height": size, "uv_width": size, "uv_height": size, "particle": t == 0,
                         "layers_enabled": False, "sync_to_project": "", "render_mode": "default",
                         "render_sides": "auto", "frame_time": ft or 1, "frame_order_type": "loop", "frame_order": "",
                         "frame_interpolate": interp, "visible": True, "internal": True, "saved": False,
                         "uuid": uid(m.name, "texture", name),
                         "relative_path": f"../resourcepack/assets/{NS}/textures/item/{name}.png",
                         "source": "data:image/png;base64," + base64.b64encode(data).decode()})

    def animator(group, frames):
        return {"name": group, "type": "bone", "keyframes": [
            {"channel": "rotation", "data_points": [{"x": str(x), "y": "0", "z": str(z)}],
             "uuid": uid(m.name, "kf", group, str(t)), "time": t, "color": -1, "interpolation": "catmullrom"}
            for t, x, z in frames]}
    sway = {"tassel": [(0, 0, 0), (1, 3, 9), (2, 0, 0), (3, -3, -9), (4, 0, 0)]}
    if "blade" in m.groups:
        sway["blade"] = [(0, 0, 0), (1, 0, 1.5), (2, 0, 0), (3, 0, -1.5), (4, 0, 0)]
    animations = [{"uuid": uid(m.name, "anim", "idle"), "name": "idle", "loop": "loop", "override": False,
                   "length": 4, "snapping": 24, "selected": False, "anim_time_update": "", "blend_weight": "",
                   "start_delay": "", "loop_delay": "",
                   "animators": {uid(m.name, "group", g): animator(g, fr) for g, fr in sway.items()}}]
    return {"meta": {"format_version": "4.10", "model_format": "java_block", "box_uv": False},
            "name": m.name, "parent": "", "ambientocclusion": True, "front_gui_light": True,
            "visible_box": [1, 1, 0], "variable_placeholders": "", "variable_placeholder_buttons": [],
            "unhandled_root_fields": {"credit": "Sakura Katana"}, "resolution": {"width": 128, "height": 128},
            "elements": elements, "outliner": outliner, "textures": textures, "animations": animations,
            "display": DISPLAY}


# ---------------------------------------------------------------- software preview
def rotm(axis, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return {"x": [[1, 0, 0], [0, c, -s], [0, s, c]], "y": [[c, 0, s], [0, 1, 0], [-s, 0, c]],
            "z": [[c, -s, 0], [s, c, 0], [0, 0, 1]]}[axis]


def mm(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def mv(a, p):
    return [sum(a[i][k] * p[k] for k in range(3)) for i in range(3)]


def render(cv, ox, oy, W, H, model, texs, M, scale, frame, shift=(0, 0)):
    """Orthographic z-buffered render; M maps model coords (centred on 8,8,8) to x-right, y-up, z-to-camera."""
    zb = [[-1e9] * W for _ in range(H)]
    light = (0.3, 0.6, 0.74)
    for el in model["elements"]:
        (x1, y1, z1), (x2, y2, z2) = el["from"], el["to"]
        rot = el.get("rotation")

        def xf(p):
            if rot:
                o = rot["origin"]
                q = mv(rotm(rot["axis"], rot["angle"]), [p[i] - o[i] for i in range(3)])
                p = [q[i] + o[i] for i in range(3)]
            return mv(M, [p[i] - 8 for i in range(3)])
        corners = {
            "south": [(x1, y2, z2), (x2, y2, z2), (x2, y1, z2), (x1, y1, z2)],
            "north": [(x2, y2, z1), (x1, y2, z1), (x1, y1, z1), (x2, y1, z1)],
            "west": [(x1, y2, z1), (x1, y2, z2), (x1, y1, z2), (x1, y1, z1)],
            "east": [(x2, y2, z2), (x2, y2, z1), (x2, y1, z1), (x2, y1, z2)],
            "up": [(x1, y2, z1), (x2, y2, z1), (x2, y2, z2), (x1, y2, z2)],
            "down": [(x1, y1, z2), (x2, y1, z2), (x2, y1, z1), (x1, y1, z1)],
        }
        for face, fd in el["faces"].items():
            frames, tw = texs[fd["texture"]]
            tex = frames[frame % len(frames)].px
            u1, v1, u2, v2 = fd["uv"]
            P = [xf(p) for p in corners[face]]
            UV = [(u1, v1), (u2, v1), (u2, v2), (u1, v2)]
            a, b = [P[1][i] - P[0][i] for i in range(3)], [P[3][i] - P[0][i] for i in range(3)]
            n = [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]
            ln = math.sqrt(sum(c * c for c in n)) or 1
            shade = 1.0 if el.get("light_emission") else 0.62 + 0.38 * abs(sum(n[i] * light[i] for i in range(3))) / ln
            S = [(W / 2 + (p[0] + shift[0]) * scale, H / 2 - (p[1] + shift[1]) * scale, p[2]) for p in P]
            for tri in ((0, 1, 2), (0, 2, 3)):
                (ax, ay, az), (bx, by, bz), (cx, cy, cz) = (S[i] for i in tri)
                area = (bx - ax) * (cy - ay) - (by - ay) * (cx - ax)
                if abs(area) < 1e-9:
                    continue
                for py in range(max(0, int(min(ay, by, cy))), min(H, int(max(ay, by, cy)) + 1)):
                    for px in range(max(0, int(min(ax, bx, cx))), min(W, int(max(ax, bx, cx)) + 1)):
                        qx, qy = px + 0.5, py + 0.5
                        w0 = ((bx - qx) * (cy - qy) - (by - qy) * (cx - qx)) / area
                        w1 = ((cx - qx) * (ay - qy) - (cy - qy) * (ax - qx)) / area
                        w2 = 1 - w0 - w1
                        if w0 < 0 or w1 < 0 or w2 < 0:
                            continue
                        z = w0 * az + w1 * bz + w2 * cz
                        if z <= zb[py][px]:
                            continue
                        u = w0 * UV[tri[0]][0] + w1 * UV[tri[1]][0] + w2 * UV[tri[2]][0]
                        v = w0 * UV[tri[0]][1] + w1 * UV[tri[1]][1] + w2 * UV[tri[2]][1]
                        t = tex[min(tw - 1, max(0, int(v / 16 * tw)))][min(tw - 1, max(0, int(u / 16 * tw)))]
                        if t[3] < 128:
                            continue
                        zb[py][px] = z
                        cv.set(ox + px, oy + py, tuple(int(c * shade) for c in t[:3]))


def preview(models, texs):
    cv = Canvas(1260, 840, (38, 40, 54, 255))
    drawn, sheathed = models
    side = [[1, 0, 0], [0, 1, 0], [0, 0, 1]]
    quarter = mm(rotm("x", 14), rotm("y", -52))
    gui = mm([[DISPLAY["gui"]["scale"][0] * (i == j) for j in range(3)] for i in range(3)], rotm("z", -45))
    render(cv, 0, 0, 240, 840, drawn, texs, side, 24, 5)
    render(cv, 240, 0, 240, 840, drawn, texs, quarter, 24, 5)
    render(cv, 480, 0, 240, 840, sheathed, texs, side, 24, 0)
    render(cv, 720, 0, 240, 840, sheathed, texs, quarter, 24, 0)
    render(cv, 960, 0, 300, 300, drawn, texs, rotm("x", 90), 46, 0)
    render(cv, 960, 300, 300, 270, drawn, texs, gui, 16, 5)
    render(cv, 960, 570, 300, 270, sheathed, texs, gui, 16, 0)
    return cv


# ---------------------------------------------------------------- output
def write(path, data):
    path = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = "wb" if isinstance(data, bytes) else "w"
    with open(path, mode) as fh:
        fh.write(data if isinstance(data, (bytes, str)) else json.dumps(data, indent="\t") + "\n")


def main():
    base, emis, pet = paint_base(), paint_emissive(), paint_petals()
    pngs = {"sakura_katana": png_bytes(base.px, 128, 128), "sakura_katana_e": frames_png(emis),
            "sakura_petals": frames_png(pet)}
    tdir = f"resourcepack/assets/{NS}/textures/item/"
    for name, data in pngs.items():
        write(tdir + name + ".png", data)
    for _, name, _, ft, interp in TEXTURES:
        if ft:
            write(tdir + name + ".png.mcmeta", {"animation": {"frametime": ft, "interpolate": interp}})

    jsons = []
    for sheathed in (False, True):
        m = build(sheathed)
        mj = model_json(m)
        jsons.append(mj)
        write(f"resourcepack/assets/{NS}/models/item/{m.name}.json", mj)
        write(f"blockbench/{m.name}.bbmodel", json.dumps(bbmodel(m, pngs)))
        lo = [min(min(c["frm"][i], c["to"][i]) for c in m.cubes()) for i in range(3)]
        hi = [max(max(c["frm"][i], c["to"][i]) for c in m.cubes()) for i in range(3)]
        assert min(lo) >= -16 and max(hi) <= 32, "element outside the -16..32 model bounds"
        print(f"{m.name}: {len(m.cubes())} cubes, groups {list(m.groups)}, bounds {r4(lo)} .. {r4(hi)}")

    write(f"resourcepack/assets/{NS}/items/sakura_katana.json", {"model": {
        "type": "minecraft:select", "property": "minecraft:custom_model_data", "index": 0,
        "cases": [{"when": "sheathed",
                   "model": {"type": "minecraft:model", "model": f"{NS}:item/sakura_katana_sheathed"}}],
        "fallback": {"type": "minecraft:model", "model": f"{NS}:item/sakura_katana"}}})
    write("resourcepack/pack.mcmeta", {"pack": {
        "description": "Sakura Katana - 3D item model (1.21.11)",
        "min_format": PACK_FORMAT, "max_format": PACK_FORMAT}})

    texs = {"#0": ([base], 128), "#1": (emis, 128), "#2": (pet, 64)}
    sheet = preview(jsons, texs)
    write("preview/sakura_katana_preview.png", png_bytes(sheet.px, sheet.w, sheet.h))
    big = Canvas(512, 512, (38, 40, 54, 255))
    big.rect(0, 0, 512, 512, lambda x, y: base.px[y // 4][x // 4] if base.px[y // 4][x // 4][3] else (38, 40, 54, 255))
    write("preview/texture_sheet_4x.png", png_bytes(big.px, 512, 512))


if __name__ == "__main__":
    main()
