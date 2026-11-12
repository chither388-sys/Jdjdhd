#!/usr/bin/env python3
"""Sanity-checks the generated model JSON and Blockbench projects."""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACES = {"north", "south", "east", "west", "up", "down"}

for name in ("sakura_katana", "sakura_katana_sheathed"):
    m = json.load(open(os.path.join(ROOT, "resourcepack/assets/sakura/models/item", name + ".json")))
    b = json.load(open(os.path.join(ROOT, "blockbench", name + ".bbmodel")))
    els = m["elements"]
    for e in els:
        assert all(-16 <= v <= 32 for v in e["from"] + e["to"]), e["name"]
        assert all(a <= c for a, c in zip(e["from"], e["to"])), e["name"]
        assert set(e["faces"]) <= FACES and e["faces"], e["name"]
        for f in e["faces"].values():
            assert all(0 <= v <= 16 for v in f["uv"]), (e["name"], f)
            assert f["texture"][1:] in m["textures"], (e["name"], f)
    assert len(b["elements"]) == len(els)
    assert sum(len(g["children"]) for g in b["outliner"]) == len(els)
    assert sorted(i for g in m["groups"] for i in g["children"]) == list(range(len(els)))
    print(name, len(els), "cubes;", "groups", [g["name"] for g in b["outliner"]], ";",
          "textures", [t["name"] for t in b["textures"]], ";",
          "emissive cubes", sum(1 for e in els if e.get("light_emission")), ";",
          "angles", sorted({e["rotation"]["angle"] for e in els if "rotation" in e}))
print("display slots", sorted(m["display"]))
