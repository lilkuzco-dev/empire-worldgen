# empire-worldgen — Terralith terrain rebalance

A **data-only Fabric mod** (no Java, no Gradle). It contains three
`lithostitched:wrap_density_function` modifiers and three vanilla reference
density functions. Nothing else.

## What problem it solves

Measured on the draft world (seed `-160353759327030922`, 83,521 chunks around
spawn, terrain read straight out of the region files):

| | vanilla, same seed | Terralith as shipped |
|---|---|---|
| 90th-percentile land ground y | 89 | **110** |
| flat land (<3 blocks relief / 16) | 18.85 % | **17.05 %** |
| mountainous land (>25) | 6.24 % | **8.46 %** |
| plains-family biomes | 22.09 % | **7.50 %** |

Diffing Terralith's own worldgen JSON against the 26.2 server jar's data dump
shows exactly where that comes from. Terralith's `offset` spline is
**bit-identical to vanilla for erosion < −0.375** — every mountain, peak and
massif is pure vanilla shape. What it changes is the **high-erosion half**,
which is the band vanilla reserves for flat lowlands:

| erosion band | Terralith minus vanilla, mean land surface height |
|---|---|
| −1.000 … −0.375  (mountains) | **+0.0 blocks** |
| −0.375 … +0.050 | −7.1 |
| +0.050 … +0.450 | **+13.8** |
| +0.450 … +0.550 | **+47.5** |
| +0.550 … +1.000 | **+27.2** |

It also drops `factor` (6.5 → 2.5, rougher) and raises `jaggedness` (0 → 0.7,
spikier) in that same band. So the connective tissue is not just missing — it
was converted into elevated, rough ground.

## What it does

Where Terralith is **more aggressive than vanilla**, blend back toward vanilla
by a fixed fraction `F`. Where Terralith is equal or gentler, change nothing.

```
offset'     = min(TL, lerp(F, TL, VN))    # can only lower ground
factor'     = max(TL, lerp(F, TL, VN))    # can only smooth  (higher factor = smoother)
jaggedness' = min(TL, lerp(F, TL, VN))    # can only de-spike
```

The `min`/`max` is the whole safety story. Each quantity is **one-directional by
construction** — target height can only fall, factor can only rise, jaggedness
can only fall — and all three are no-ops in the mountain band where Terralith
and vanilla already agree. Terralith's deeper ocean basins (Terralith is *lower*
than vanilla there) are preserved for the same reason.

The resulting surface still rises on about 1 % of chunks: that is the smoothing
term filling hollows, not new hills. The world's highest ground is y 245 at
every strength, unchanged from Terralith.

## Choosing F

`F` is set at build time. **Shipped default F = 0.75**, ruled 2026-08-17.

Measured on 83,521 chunks per variant — same seed, same 4600×4600 area, terrain
read out of the region files:

| | vanilla | Terralith | F = 0.50 | **F = 0.75** | F = 1.00 |
|---|---|---|---|---|---|
| open flat/gentle ground | 27.78 % | 26.26 % | 28.10 % | **29.55 %** | 30.75 % |
| hilly land (12–25) | 11.83 % | 13.46 % | 11.89 % | **10.73 %** | 10.24 % |
| mountainous land (>25) | 3.92 % | 5.51 % | 4.02 % | **3.78 %** | 3.60 % |
| open water | 27.16 % | 25.94 % | 26.78 % | **27.21 %** | 27.72 % |
| connective : feature | 3.90× | 3.07× | 3.82× | **4.33×** | 4.67× |
| median land ground y | 67 | 72 | 70 | **69** | 67 |
| p99 land ground y | 125 | 183 | 145 | **143** | 144 |
| highest ground y | 170 | 245 | 245 | **245** | 245 |

F = 0.50 only returns to vanilla parity (3.82× against vanilla's 3.90×) — it
removes Terralith's excess without producing any surplus. F = 0.75 clears
vanilla on every openness measure while keeping a quarter of the lowland lift
and the full mountain range above it. F = 1.00 goes past the balance: median
land y falls to exactly vanilla's 67, and rolling land drops to 16.73 %, *below*
vanilla's 17.88 % — the middle of the range starts hollowing out.

**What F does not change: the biome-category breakdown.** Flat plains-family is
7.50 % and ocean 19.72 % at F = 0, 0.50, 0.75 and 1.00 alike. The tuning moves
ground height; biome choice is decided by climate parameters it does not touch.
What changes is the ground under those biomes — `terralith:highlands` goes from
8.3 relief at y 70 to **5.9 at y 66**, flatter than `minecraft:plains` itself,
and `minecraft:jungle` from 19.6 at y 85 to **13.1 at y 73**. Moving the
category table would need a `lithostitched:replace_fully` biome remap, which
trades away Terralith biomes; deliberately not done.

## Build

```sh
python3 tools/build-pack.py 0.75 src         # regenerate src/ at blend F
cd src && zip -qr ../empire_worldgen-0.1.0.jar .
```

`src/` is generated, not hand-edited — `F` is a single number on the command
line. The vanilla reference curves live in `vendor/vanilla-26.2/`; see the
PROVENANCE note there for how to re-dump them on a Minecraft version bump.

## Where it lives in the pipeline

`deploy-server.sh` mirrors **`/mods` only**, and the world-reset checklist
deletes **`/world` only**. A jar in `mods.json` therefore survives both, and is
covered by the parity check. A `world/datapacks/` entry would be destroyed by
the reset, and a hand-placed `/config` file would be invisible to the manifest.
So this ships as an `extra_mods` entry, `side: server` (matching `terralith`).

## Ship steps (SHIPPING.md)

1. build the jar
2. `gh release create v0.1.0` with the jar attached
3. add to `mods.json` `extra_mods` with `shasum -a 512` of the exact file
4. `tools/postship-check.sh` must pass — `node tools/load-check.js --side server`
   already passes with this jar staged (its only dependency, `lithostitched`,
   is present as Terralith's own dependency)
5. the terrain only exists in **chunks generated after this lands**, so it must
   be in the manifest *before* the world reset
