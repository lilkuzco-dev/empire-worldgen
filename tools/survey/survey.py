#!/usr/bin/env python3
"""
Survey a Minecraft world's generated chunks from region files.

Per FULL chunk it records:
  - h05/h50/h95 of MOTION_BLOCKING_NO_LEAVES (visible surface; water counts as
    surface, leaves do not -- only trunks poke up, and those are a minority of
    columns so h05 is effectively a tree-free ground estimate)
  - the 16 biome-cell samples at the surface

Outputs a .npz for downstream analysis.
"""
import sys, os, glob, math, collections
import numpy as np
import nbt

MIN_Y = -64
SEA = 63


def hm_to_y(raw):
    # heightmap stores (topmost_y + 1) - MIN_Y
    return np.asarray(raw, dtype=np.int32) + (MIN_Y - 1)


def survey_region(path):
    rows = []          # (cx, cz, h05, h50, h95, hmin, hmax)
    biome_hits = collections.Counter()
    biome_by_chunk = []  # (cx, cz, dominant_biome)
    for _lx, _lz, root in nbt.iter_chunks(path):
        if root.get("Status") != "minecraft:full":
            continue
        hm = root.get("Heightmaps") or {}
        packed = hm.get("MOTION_BLOCKING_NO_LEAVES") or hm.get("MOTION_BLOCKING")
        surf_packed = hm.get("WORLD_SURFACE") or packed
        if not packed:
            continue
        h = nbt.unpack_heightmap(packed)
        if h is None or len(h) != 256:
            continue
        hy = hm_to_y(h)
        sh = nbt.unpack_heightmap(surf_packed)
        shy = hm_to_y(sh) if sh and len(sh) == 256 else hy

        of = hm.get("OCEAN_FLOOR")
        ofy = hm_to_y(nbt.unpack_heightmap(of)) if of else hy
        if len(ofy) != 256:
            ofy = hy
        # water depth per column = visible surface (incl. fluid) - solid floor
        depth = np.maximum(hy - ofy, 0)

        cx = root.get("xPos"); cz = root.get("zPos")
        rows.append((cx, cz,
                     int(np.percentile(hy, 5)), int(np.percentile(hy, 50)),
                     int(np.percentile(hy, 95)), int(hy.min()), int(hy.max()),
                     int(np.percentile(ofy, 5)), int(np.percentile(ofy, 50)),
                     int(np.percentile(ofy, 95)),
                     int((depth >= 2).sum()), int(np.percentile(depth, 50))))

        # ---- biome sampling: 16 cells (4x4) at the surface -------------
        secs = root.get("sections") or []
        sec_by_y = {}
        for s in secs:
            sec_by_y[s.get("Y")] = s
        local = collections.Counter()
        for zc in range(4):
            for xc in range(4):
                x = xc * 4 + 1
                z = zc * 4 + 1
                y = int(shy[z * 16 + x])
                y = max(y, SEA)          # in oceans, sample at water surface
                sy = y >> 4
                sec = sec_by_y.get(sy)
                if sec is None:
                    continue
                b = sec.get("biomes") or {}
                pal = b.get("palette") or []
                if not pal:
                    continue
                if len(pal) == 1:
                    name = pal[0]
                else:
                    data = b.get("data") or []
                    nbits = max(1, (len(pal) - 1).bit_length())
                    idxs = nbt.unpack_indices(data, nbits, 64)
                    bi = ((y & 15) >> 2) * 16 + ((z & 15) >> 2) * 4 + ((x & 15) >> 2)
                    name = pal[idxs[bi]] if bi < len(idxs) and idxs[bi] < len(pal) else pal[0]
                biome_hits[name] += 1
                local[name] += 1
        if local:
            biome_by_chunk.append((cx, cz, local.most_common(1)[0][0]))
    return rows, biome_hits, biome_by_chunk


def main(region_glob, out):
    files = sorted(glob.glob(region_glob))
    files = [f for f in files if os.path.getsize(f) > 8192]
    print(f"{len(files)} region files", file=sys.stderr)
    all_rows = []
    hits = collections.Counter()
    chunk_biomes = []
    for i, f in enumerate(files):
        r, b, cb = survey_region(f)
        all_rows.extend(r); hits.update(b); chunk_biomes.extend(cb)
        if (i + 1) % 10 == 0:
            print(f"  {i+1}/{len(files)}  chunks={len(all_rows)}", file=sys.stderr)
    arr = np.array(all_rows, dtype=np.int32)
    names = sorted(hits)
    name_idx = {n: i for i, n in enumerate(names)}
    cb = np.array([(c[0], c[1], name_idx[c[2]]) for c in chunk_biomes], dtype=np.int32)
    np.savez_compressed(out, chunks=arr, chunk_biomes=cb,
                        biome_names=np.array(names),
                        biome_counts=np.array([hits[n] for n in names], dtype=np.int64))
    print(f"saved {out}: {len(arr)} full chunks, {sum(hits.values())} biome samples",
          file=sys.stderr)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
