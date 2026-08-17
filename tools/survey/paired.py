#!/usr/bin/env python3
"""Paired chunk-for-chunk comparison of two worlds generated from the same seed."""
import sys
import numpy as np

C = dict(CX=0, CZ=1, H05=2, H50=3, H95=4, HMIN=5, HMAX=6,
         OF05=7, OF50=8, OF95=9, WETCOLS=10, DEPTH50=11)


def load(p):
    z = np.load(p, allow_pickle=True)
    ch = z["chunks"]
    key = {(int(a), int(b)): i for i, (a, b) in enumerate(zip(ch[:, 0], ch[:, 1]))}
    return ch, key, z


def relief(ch, key):
    g = ch[:, C["OF05"]].astype(float)
    out = np.full(len(ch), np.nan)
    for i in range(len(ch)):
        a, b = int(ch[i, 0]), int(ch[i, 1])
        d = []
        for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            j = key.get((a + da, b + db))
            if j is not None:
                d.append(abs(g[i] - g[j]))
        if len(d) == 4:
            out[i] = max(d)
    return g, out


def main(pa, pb, la, lb):
    cha, ka, _ = load(pa)
    chb, kb, _ = load(pb)
    common = sorted(set(ka) & set(kb))
    ia = np.array([ka[k] for k in common])
    ib = np.array([kb[k] for k in common])
    ga, ra = relief(cha, ka)
    gb, rb = relief(chb, kb)
    ga, ra = ga[ia], ra[ia]
    gb, rb = gb[ib], rb[ib]
    wa = cha[ia, C["WETCOLS"]].astype(float) / 256
    wb = chb[ib, C["WETCOLS"]].astype(float) / 256
    m = ~np.isnan(ra) & ~np.isnan(rb)
    print(f"paired chunks: {len(common):,}  (with neighbours: {m.sum():,})")
    d = gb[m] - ga[m]
    print(f"\nGROUND HEIGHT  {lb} minus {la}")
    print(f"   mean {d.mean():+.2f}   median {np.median(d):+.1f}   "
          f"p5 {np.percentile(d,5):+.0f}  p95 {np.percentile(d,95):+.0f}")
    print(f"   chunks lowered: {100*(d<-1).mean():.1f}%   unchanged(±1): "
          f"{100*(np.abs(d)<=1).mean():.1f}%   raised: {100*(d>1).mean():.1f}%")
    print(f"\nLOCAL RELIEF   {la}: mean {ra[m].mean():.2f}   {lb}: mean {rb[m].mean():.2f}"
          f"   ({100*(rb[m].mean()/ra[m].mean()-1):+.1f}%)")
    print(f"OPEN WATER     {la}: {100*(wa>=0.9).mean():.2f}%   "
          f"{lb}: {100*(wb>=0.9).mean():.2f}%")
    print(f"MEAN WATER     {la}: {100*wa.mean():.2f}%   {lb}: {100*wb.mean():.2f}%")
    for lab, g_, r_, w_ in ((la, ga, ra, wa), (lb, gb, rb, wb)):
        land = (w_ < 0.25) & m
        rr = r_[land]
        print(f"\n{lab}: land chunks {land.sum():,}")
        for lo, hi, nm in ((0, 3, "flat (<3)"), (3, 6, "gently rolling (3-6)"),
                           (6, 12, "rolling (6-12)"), (12, 25, "hilly (12-25)"),
                           (25, 1e9, "mountainous (>25)")):
            print(f"     {nm:<24}{100*((rr>=lo)&(rr<hi)).mean():6.2f}%")
        print(f"     median land y {np.median(g_[land]):.0f}   p90 {np.percentile(g_[land],90):.0f}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
