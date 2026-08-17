#!/usr/bin/env python3
"""
Side-by-side comparison of two or more surveyed worlds.

    python3 compare.py "Vanilla=vanilla.npz" "Terralith=baseline.npz" "Tuned=tuned050.npz"

Only meaningful when every world was generated from the SAME seed over the SAME
area -- that is what makes the differences causal rather than geographic.
"""
import sys, os, collections
import numpy as np

import census
from census import classify, C


def stats(path):
    z = np.load(path, allow_pickle=True)
    ch, names, counts = z["chunks"], list(z["biome_names"]), z["biome_counts"]
    tot = counts.sum()
    g = ch[:, C["OF05"]].astype(float)
    wet = ch[:, C["WETCOLS"]].astype(float) / 256
    key = {(int(a), int(b)): i for i, (a, b) in enumerate(zip(ch[:, 0], ch[:, 1]))}
    loc = np.full(len(ch), np.nan)
    for i in range(len(ch)):
        a, b = int(ch[i, 0]), int(ch[i, 1])
        d = [abs(g[i] - g[key[(a + da, b + db)]])
             for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)) if (a + da, b + db) in key]
        if len(d) == 4:
            loc[i] = max(d)
    fam = collections.Counter()
    for n, c in zip(names, counts):
        fam[classify(n)] += int(c)
    land = (wet < 0.25) & ~np.isnan(loc)
    r = loc[land]
    return dict(fam={k: 100 * v / tot for k, v in fam.items()},
                openwater=100 * (wet >= 0.9).mean(), meanwater=100 * wet.mean(),
                relief=np.nanmean(loc),
                flat=100 * (r < 3).mean(), gentle=100 * ((r >= 3) & (r < 6)).mean(),
                rolling=100 * ((r >= 6) & (r < 12)).mean(),
                hilly=100 * ((r >= 12) & (r < 25)).mean(), mtn=100 * (r >= 25).mean(),
                medy=np.median(g[land]), p90y=np.percentile(g[land], 90),
                maxy=g.max(), nchunk=len(ch))


FAMS = ["ocean", "river", "beach/shore", "flat (plains-family)",
        "elevated 'highlands' (Terralith plains-family)", "moderate/other",
        "mountainous/high-relief"]


def main(pairs):
    S = {l: stats(p) for l, p in pairs}
    labs = [l for l, _ in pairs]
    W = max(14, max(len(l) for l in labs) + 2)

    def row(name, key, fmt="{:.2f}%"):
        print(f"  {name:<40}" + "".join(f"{fmt.format(S[l][key]):>{W}}" for l in labs))

    print("=" * (42 + W * len(labs)))
    print(f"WORLD COMPARISON — {S[labs[0]]['nchunk']:,} chunks in the first world")
    print("=" * (42 + W * len(labs)))
    print(f"  {'':<40}" + "".join(f"{l:>{W}}" for l in labs))
    print("\n  BIOME CATEGORY (share of surface area)")
    for f in FAMS:
        print(f"    {f:<38}" + "".join(f"{S[l]['fam'].get(f, 0.0):>{W-1}.2f}%" for l in labs))
    print("\n  PHYSICAL WATER (no biome names used)")
    row("open-water chunks (>=90% fluid)", "openwater")
    row("mean fraction of chunk under water", "meanwater")
    print("\n  LAND TERRAIN RELIEF (tree-free, blocks per 16)")
    row("mean local relief", "relief", "{:.2f}")
    row("flat            (<3)", "flat")
    row("gently rolling  (3-6)", "gentle")
    row("rolling         (6-12)", "rolling")
    row("hilly           (12-25)", "hilly")
    row("mountainous     (>25)", "mtn")
    print("\n  LAND ELEVATION")
    row("median land ground y", "medy", "{:.0f}")
    row("90th-percentile land ground y", "p90y", "{:.0f}")
    row("highest ground y seen", "maxy", "{:.0f}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    main([tuple(a.split("=", 1)) if "=" in a else (a, a) for a in args])
