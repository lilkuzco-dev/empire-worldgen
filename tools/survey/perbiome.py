#!/usr/bin/env python3
"""Per-biome measured terrain: how high and how rough is each biome, really?"""
import sys, collections
import numpy as np

C = dict(CX=0, CZ=1, H05=2, H50=3, H95=4, HMIN=5, HMAX=6,
         OF05=7, OF50=8, OF95=9, WETCOLS=10, DEPTH50=11)


def build(path):
    z = np.load(path, allow_pickle=True)
    ch = z["chunks"]; cb = z["chunk_biomes"]; names = list(z["biome_names"])
    g = ch[:, C["OF05"]].astype(float)
    wet = ch[:, C["WETCOLS"]].astype(float) / 256.0
    pos = {(int(a), int(b)): i for i, (a, b) in enumerate(zip(ch[:, 0], ch[:, 1]))}
    # tree-free local relief: max |Δ ground| to the 4 neighbours
    loc = np.full(len(ch), np.nan)
    for i in range(len(ch)):
        a, b = int(ch[i, 0]), int(ch[i, 1])
        d = []
        for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            j = pos.get((a + da, b + db))
            if j is not None:
                d.append(abs(g[i] - g[j]))
        if len(d) == 4:
            loc[i] = max(d)
    # attach dominant biome per chunk
    bidx = np.full(len(ch), -1, dtype=np.int32)
    for a, b, k in cb:
        j = pos.get((int(a), int(b)))
        if j is not None:
            bidx[j] = k
    return ch, names, g, loc, wet, bidx


def report(label, path, top=26):
    ch, names, g, loc, wet, bidx = build(path)
    print("=" * 96)
    print(label)
    print(f"{'biome':<40}{'%area':>7}{'ground y':>10}{'relief':>9}{'p90 rel':>9}{'water%':>8}")
    print("-" * 96)
    n = len(ch)
    rows = []
    for k, nm in enumerate(names):
        m = bidx == k
        c = int(m.sum())
        if c < 40:
            continue
        lm = loc[m]; lm = lm[~np.isnan(lm)]
        if len(lm) < 20:
            continue
        rows.append((c / n, nm, np.median(g[m]), lm.mean(),
                     np.percentile(lm, 90), 100 * wet[m].mean()))
    rows.sort(reverse=True)
    for share, nm, gy, rel, r90, w in rows[:top]:
        print(f"{nm:<40}{100*share:7.2f}{gy:10.0f}{rel:9.1f}{r90:9.1f}{w:8.1f}")
    print()
    # ---- the headline: how much of the land is genuinely flat? -----------
    land = wet < 0.25
    ok = ~np.isnan(loc)
    sel = land & ok
    rel = loc[sel]
    print(f"LAND chunks (<25% water) with neighbours: {sel.sum():,} of {n:,}")
    for lo, hi, nm in ((0, 3, "flat        (<3 blocks / 16)"),
                       (3, 6, "gently rolling (3-6)"),
                       (6, 12, "rolling      (6-12)"),
                       (12, 25, "hilly        (12-25)"),
                       (25, 1e9, "mountainous  (>25)")):
        f = ((rel >= lo) & (rel < hi)).mean()
        print(f"   {nm:<32}{100*f:6.2f}% of land")
    print(f"   median land ground y: {np.median(g[sel]):.0f}   "
          f"p90: {np.percentile(g[sel],90):.0f}")
    print()


if __name__ == "__main__":
    args = sys.argv[1:] or ["live.npz"]
    for a in args:
        lab, _, path = a.partition("=")
        report(lab, path or lab)
