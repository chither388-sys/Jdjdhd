# Sakura Katana

A stylized 3D katana item model for Minecraft Java Edition 1.21.11, with a sheathed display variant.

![Preview](preview/sakura_katana_preview.png)

## Contents

| Path | What it is |
| --- | --- |
| `blockbench/sakura_katana.bbmodel` | Blockbench project (Java Block/Item), drawn katana, 55 cubes |
| `blockbench/sakura_katana_sheathed.bbmodel` | Blockbench project, katana in its saya, 38 cubes |
| `resourcepack/` | Ready-to-use resource pack (pack format 75) |
| `tools/build_katana.py` | Generator for everything above (Python 3, standard library only) |

Textures live in `resourcepack/assets/sakura/textures/item/`:

- `sakura_katana.png` – 128×128 base sheet
- `sakura_katana_e.png` – 128×128 emissive layer (hamon glow), 8 animated frames, same layout as the base sheet
- `sakura_petals.png` – 64×64 emissive drifting petals, 16 animated frames

Cube groups: `blade`, `tsuba`, `handle`, `pommel`, `tassel`, `petals` (and `saya` in the sheathed project).

## Using it in game

Copy `resourcepack/` into `.minecraft/resourcepacks/` (or zip its contents), enable it, then:

```
/give @s minecraft:netherite_sword[minecraft:item_model="sakura:sakura_katana"]
/give @s minecraft:netherite_sword[minecraft:item_model="sakura:sakura_katana",minecraft:custom_model_data={strings:["sheathed"]}]
```

## How the effects work

Vanilla item models cannot spawn particles or move cubes, so:

- **Hamon glow** – thin overlay cubes use the emissive texture with `light_emission: 15`, so the line stays lit in the dark and shimmers through an animated texture.
- **Petals** – two crossed emissive planes at the blade tip play an animated texture of drifting petals.
- **Blade and tassel sway** – stored as an `idle` animation in the Blockbench projects, keyed to the `blade` and `tassel` groups. The Java item format does not play it; convert the project (File → Convert Project) or use a plugin such as Animated Java to use it.

The blade curve and the five tsuba petals rely on free-angle element rotations, which need 1.21.11 and a current Blockbench. For older targets run `python3 tools/build_katana.py --legacy-rotation` to rebuild with 22.5° steps.

## Rebuilding

```
python3 tools/build_katana.py
```
