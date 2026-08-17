#!/usr/bin/env python3
"""
Answer the seed caveat directly: at the exact coordinates SERVER.md recorded for
the draft world, what biome and ground height does each variant produce?
Also reports how much of the map keeps its dominant biome, and the world spawn.
"""
import sys, glob, gzip, collections
import numpy as np
import nbt

# from SERVER.md, "The new world / Worldgen verification" table
LANDMARKS = [
    ("spawn",                        0,     0),
    ("terralith:moonlight_valley",   256,  -224),
    ("terralith:yellowstone",       -288,   512),
    ("terralith:alpine_highlands",   320,   512),
    ("terralith:skylands_autumn",    928, -1824),
    ("terralith:amethyst_rainforest", -832, -2368),
    ("towns_and_towers village",     240,   448),
    ("warfront vostok_forward_base", 784,   704),
]

C = dict(CX=0, CZ=1, OF05=7)


def index(path):
    z = np.load(path, allow_pickle=True)
    ch, cb, names = z["chunks"], z["chunk_biomes"], list(z["biome_names"])
    g = {(int(a), int(b)): int(v) for a, b, v in
         zip(ch[:, 0], ch[:, 1], ch[:, C["OF05"]])}
    b = {(int(a), int(b)): names[int(k)] for a, b, k in cb}
    return g, b


def spawn_of(run):
    p = f"runs/{run}/world/level.dat"
    try:
        root = nbt.parse_nbt(gzip.open(p, "rb").read())
    except Exception as e:
        return f"(unreadable: {e})"
    d = root.get("Data", root)
    sp = d.get("spawn") or {}
    packs = (d.get("DataPacks") or {}).get("Enabled")
    return f"spawn={sp.get('pos')}  packs={packs}"


def main(pairs):
    idx = {lab: index(p) for lab, p in pairs}
    labs = [l for l, _ in pairs]
    print("LANDMARKS recorded for the draft world — biome and ground height per variant")
    w = max(len(l) for l in labs)
    print(f"{'coordinate':<34}" + "".join(f"{l:<40}" for l in labs))
    print("-" * (34 + 40 * len(labs)))
    for name, x, z in LANDMARKS:
        cx, cz = x >> 4, z >> 4
        row = f"{name+f' [{x},{z}]':<34}"
        for l in labs:
            g, b = idx[l]
            bi = b.get((cx, cz), "—")
            gy = g.get((cx, cz))
            row += f"{(bi.replace('minecraft:','mc:')+f'  y{gy}' if gy is not None else '(not generated)'):<40}"
        print(row)
    print()
    if len(labs) == 2:
        ga, ba = idx[labs[0]]
        gb, bb = idx[labs[1]]
        common = set(ba) & set(bb)
        same = sum(1 for k in common if ba[k] == bb[k])
        print(f"dominant biome unchanged in {100*same/len(common):.1f}% of "
              f"{len(common):,} shared chunks  ({labs[0]} vs {labs[1]})")
        chg = collections.Counter()
        for k in common:
            if ba[k] != bb[k]:
                chg[(ba[k], bb[k])] += 1
        print("\nlargest biome shifts:")
        for (a, b), n in chg.most_common(12):
            print(f"   {100*n/len(common):5.2f}%  {a}  ->  {b}")


if __name__ == "__main__":
    pairs = [tuple(a.split("=")) for a in sys.argv[1:]]
    main([(l, p) for l, p in pairs])
