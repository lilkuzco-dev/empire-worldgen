#!/usr/bin/env python3
"""
Build the Empire worldgen tuning datapack-mod.

WHAT IT DOES, in one sentence: where Terralith's terrain is MORE aggressive than
vanilla's, pull it back toward vanilla by a fixed fraction; where Terralith is
already equal or gentler, change nothing at all.

Measured basis (see the divergence map): Terralith's offset spline is bit-identical
to vanilla for erosion < -0.375 -- i.e. every mountain, peak and massif -- and
raises the high-erosion band (vanilla's flat lowlands) by +14 to +48 blocks while
dropping `factor` and raising `jaggedness` there. So a one-directional blend
touches ONLY the lowlands and provably cannot flatten a single mountain.

  offset'     = min(TL, lerp(F, TL, VN))   # only ever lowers
  factor'     = max(TL, lerp(F, TL, VN))   # only ever smooths (higher factor = smoother)
  jaggedness' = min(TL, lerp(F, TL, VN))   # only ever de-spikes
"""
import json, os, shutil, sys, copy

HERE = os.path.dirname(os.path.abspath(__file__))
VN = os.path.join(HERE, "..", "vendor", "vanilla-26.2")
NS = "empire_worldgen"
F = float(sys.argv[1]) if len(sys.argv) > 1 else 0.75
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "..", "src")

MARK = {"type": "lithostitched:wrapped_marker"}


def lerp(f, vanilla_ref):
    """lerp(f, terralith, vanilla) = (1-f)*TL + f*VN"""
    return {
        "type": "minecraft:add",
        "argument1": {"type": "minecraft:mul", "argument1": round(1.0 - f, 6),
                      "argument2": MARK},
        "argument2": {"type": "minecraft:mul", "argument1": round(f, 6),
                      "argument2": vanilla_ref},
    }


def modifier(target, vanilla_ref, direction):
    return {
        "type": "lithostitched:wrap_density_function",
        "target_function": target,
        "wrapper_function": {
            "type": f"minecraft:{direction}",
            "argument1": MARK,
            "argument2": lerp(F, vanilla_ref),
        },
    }


def main():
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    dfd = f"{OUT}/data/{NS}/worldgen/density_function/vanilla"
    modd = f"{OUT}/data/{NS}/lithostitched/worldgen_modifier"
    os.makedirs(dfd); os.makedirs(modd)

    json.dump({
        "schemaVersion": 1, "id": NS, "version": "0.1.0",
        "name": "Empire Worldgen Tuning",
        "description": ("Pulls Terralith's high-erosion lowlands back toward vanilla "
                        "terrain so flat plains and moderate ground return as connective "
                        "tissue. Mountains, peaks and ocean basins are untouched. "
                        f"Blend strength {F}. Data-only."),
        "authors": ["Lil Kuzco Empire"], "license": "MIT", "environment": "*",
        "depends": {"fabricloader": ">=0.19", "lithostitched": ">=1.7.12"},
    }, open(f"{OUT}/fabric.mod.json", "w"), indent=2)

    json.dump({"pack": {"id": NS, "min_format": 107, "max_format": 107,
                        "description": "Empire worldgen tuning"}},
              open(f"{OUT}/pack.mcmeta", "w"), indent=2)

    # vanilla reference curves, copied verbatim out of the 26.2 server jar's own
    # data dump. They read the SAME continents/erosion/ridges inputs Terralith
    # feeds them, so this is vanilla's mapping of Terralith's climate.
    for nm in ("offset", "factor", "jaggedness"):
        shutil.copyfile(f"{VN}/{nm}.json", f"{dfd}/{nm}.json")

    for nm, direction in (("offset", "min"), ("factor", "max"), ("jaggedness", "min")):
        json.dump(modifier(f"minecraft:overworld/{nm}", f"{NS}:vanilla/{nm}", direction),
                  open(f"{modd}/soften_{nm}.json", "w"), indent=2)

    print(f"built {OUT} with blend F={F}")
    for root, _d, fs in os.walk(OUT):
        for f in fs:
            print("   ", os.path.relpath(os.path.join(root, f), OUT))


if __name__ == "__main__":
    main()
