#!/usr/bin/env python3
"""Biome census + terrain-class breakdown, as real percentages."""
import sys, json, glob, os, collections
import numpy as np

SEA = 63
C = dict(CX=0, CZ=1, H05=2, H50=3, H95=4, HMIN=5, HMAX=6,
         OF05=7, OF50=8, OF95=9, WETCOLS=10, DEPTH50=11)

# unpacked Terralith jar; its own biome tags drive the category grouping
TL = os.environ.get("TERRALITH_DIR", "./tl")

# ---- resolve Terralith's own tag files into concrete biome sets -----------
def load_tags():
    tags = {}
    for p in glob.glob(f"{TL}/data/*/tags/worldgen/biome/**/*.json", recursive=True):
        rel = p.split("/data/", 1)[1]
        ns, rest = rel.split("/tags/worldgen/biome/", 1)
        key = f"{ns}:{rest[:-5]}"
        try:
            d = json.load(open(p))
        except Exception:
            continue
        tags[key] = [v if isinstance(v, str) else v.get("id") for v in d.get("values", [])]
    return tags


def resolve(tag, tags, seen=None):
    seen = seen or set()
    if tag in seen:
        return set()
    seen.add(tag)
    out = set()
    for v in tags.get(tag, []):
        if v is None:
            continue
        if v.startswith("#"):
            out |= resolve(v[1:], tags, seen)
        else:
            out.add(v)
    return out


TAGS = load_tags()
MOUNTAIN = resolve("terralith:reference/mountain", TAGS)
PEAK = resolve("terralith:reference/mountain_peak", TAGS)
SLOPE = resolve("terralith:reference/mountain_slope", TAGS)
WINDSWEPT = resolve("terralith:reference/windswept", TAGS)
HIGHLANDS = resolve("terralith:highlands", TAGS)
CLIFFS = resolve("terralith:cliffs", TAGS)
VOLCANIC = resolve("terralith:volcanic", TAGS)
TL_PLAINS = resolve("terralith:reference/plains", TAGS)

VANILLA_MOUNTAIN = {
    "minecraft:jagged_peaks", "minecraft:frozen_peaks", "minecraft:stony_peaks",
    "minecraft:snowy_slopes", "minecraft:windswept_hills", "minecraft:windswept_gravelly_hills",
    "minecraft:windswept_forest", "minecraft:windswept_savanna", "minecraft:grove",
    "minecraft:meadow", "minecraft:cherry_grove",
}
# meadow / cherry_grove sit on mountain terrain in vanilla 1.18+ but are gently
# sloped; kept separate below.
GENTLE_HIGH = {"minecraft:meadow", "minecraft:cherry_grove"}

VANILLA_FLAT = {
    "minecraft:plains", "minecraft:sunflower_plains", "minecraft:snowy_plains",
    "minecraft:desert", "minecraft:savanna", "minecraft:savanna_plateau",
    "minecraft:swamp", "minecraft:mangrove_swamp", "minecraft:ice_spikes",
    "minecraft:mushroom_fields",
}
VANILLA_MODERATE = {
    "minecraft:forest", "minecraft:birch_forest", "minecraft:old_growth_birch_forest",
    "minecraft:dark_forest", "minecraft:flower_forest", "minecraft:taiga",
    "minecraft:snowy_taiga", "minecraft:old_growth_pine_taiga",
    "minecraft:old_growth_spruce_taiga", "minecraft:jungle", "minecraft:sparse_jungle",
    "minecraft:bamboo_jungle", "minecraft:badlands", "minecraft:wooded_badlands",
    "minecraft:eroded_badlands", "minecraft:cherry_grove",
}


def classify(name):
    n = name.split(":", 1)[1] if ":" in name else name
    if "ocean" in n:
        return "ocean"
    if n in ("river", "frozen_river", "warm_river"):
        return "river"
    if "beach" in n or "shore" in n:
        return "beach/shore"
    if name.startswith("minecraft:") and ("cave" in n or n in
                                          ("lush_caves", "dripstone_caves", "deep_dark")):
        return "cave(surface-exposed)"
    if "cave" in n:
        return "cave(surface-exposed)"
    if name in PEAK or name in SLOPE or name in WINDSWEPT or name in CLIFFS or name in VOLCANIC:
        return "mountainous/high-relief"
    if name in VANILLA_MOUNTAIN and name not in GENTLE_HIGH:
        return "mountainous/high-relief"
    if name in VANILLA_FLAT:
        return "flat (plains-family)"
    if name in TL_PLAINS or name in HIGHLANDS:
        return "elevated 'highlands' (Terralith plains-family)"
    if name in VANILLA_MODERATE or name in GENTLE_HIGH:
        return "moderate/other"
    return "moderate/other"


def report(label, path):
    z = np.load(path, allow_pickle=True)
    ch = z["chunks"]; names = list(z["biome_names"]); counts = z["biome_counts"]
    tot = counts.sum()
    print("=" * 78)
    print(f"{label}: {len(ch):,} fully-generated chunks, {tot:,} surface biome samples")
    print("-" * 78)

    fam = collections.Counter()
    for n, c in zip(names, counts):
        fam[classify(n)] += int(c)
    print("BIOME-CATEGORY BREAKDOWN (share of surveyed surface area)")
    for k, v in fam.most_common():
        print(f"   {k:<48} {100*v/tot:6.2f}%")

    print()
    print("TOP 20 INDIVIDUAL BIOMES")
    order = np.argsort(-counts)
    for i in order[:20]:
        print(f"   {names[i]:<44} {100*counts[i]/tot:6.2f}%   [{classify(names[i])}]")

    print()
    nsMod = sum(int(c) for n, c in zip(names, counts) if not n.startswith("minecraft:"))
    print(f"   modded-namespace biomes: {100*nsMod/tot:.2f}%   "
          f"vanilla-namespace: {100*(tot-nsMod)/tot:.2f}%")
    print(f"   distinct biomes present: {len(names)}")

    # ---- physical water measure (biome-independent) ----------------------
    wet = ch[:, C["WETCOLS"]].astype(float) / 256.0
    print()
    print("PHYSICAL WATER COVERAGE (columns with >=2 blocks of fluid, no biome names used)")
    print(f"   mean fraction of every chunk under water:  {100*wet.mean():.2f}%")
    print(f"   chunks >=90% water (open water):           {100*(wet>=0.90).mean():.2f}%")
    print(f"   chunks >=50% water:                        {100*(wet>=0.50).mean():.2f}%")
    print(f"   chunks with no water at all:               {100*(wet==0).mean():.2f}%")
    return z


if __name__ == "__main__":
    for a in (sys.argv[1:] or ["live.npz"]):
        report(a, a)
        print()
