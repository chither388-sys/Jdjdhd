#!/usr/bin/env python3
"""Sanity-checks the generated model JSON and Blockbench projects."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACES = {"north", "south", "east", "west", "up", "down"}
MODELS = [("sakura", "sakura_katana"), ("sakura", "sakura_katana_sheathed"), ("warrior", "warrior_greatsword")]

for ns, name in MODELS:
    m = json.load(open(os.path.join(ROOT, f"resourcepack/assets/{ns}/models/item", name + ".json")))
    b = json.load(open(os.path.join(ROOT, "blockbench", name + ".bbmodel")))
    els = m["elements"]
    for e in els:
        assert all(-16 <= v <= 32 for v in e["from"] + e["to"]), e["name"]
        assert all(a <= c for a, c in zip(e["from"], e["to"])), e["name"]
        assert set(e["faces"]) <= FACES and e["faces"], e["name"]
        for f in e["faces"].values():
            assert all(0 <= v <= 16 for v in f["uv"]), (e["name"], f)
            assert f["texture"][1:] in m["textures"], (e["name"], f)
    for t in m["textures"].values():
        tns, path = t.split(":")
        assert os.path.exists(os.path.join(ROOT, f"resourcepack/assets/{tns}/textures/{path}.png")), t
    assert len(b["elements"]) == len(els)
    assert sum(len(g["children"]) for g in b["outliner"]) == len(els)
    assert sorted(i for g in m["groups"] for i in g["children"]) == list(range(len(els)))
    groups = {g["uuid"] for g in b["outliner"]}
    assert all(a in groups for anim in b["animations"] for a in anim["animators"]), "animation targets a missing group"
    print(name, len(els), "cubes;", "groups", [g["name"] for g in b["outliner"]], ";",
          "textures", [t["name"] for t in b["textures"]], ";",
          "emissive cubes", sum(1 for e in els if e.get("light_emission")), ";",
          "angles", sorted({e["rotation"]["angle"] for e in els if "rotation" in e}), ";",
          "display", sorted(m["display"]))
