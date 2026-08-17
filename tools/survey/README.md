# tools/survey — measure terrain instead of eyeballing it

This is the evidence pipeline behind the tuning, kept in the repo so the
before/after can be re-run rather than taken on trust. Everything reads Anvil
region files directly; nothing depends on being in-game.

Zero third-party dependencies except **numpy**. `nbt.py` is a small Anvil + NBT
reader written for this (stdlib `zlib`/`struct` only).

## The one-minute version

```sh
# 1. survey any world's region files into a .npz
python3 survey.py '<world>/dimensions/minecraft/overworld/region/*.mca' before.npz

# 2. compare worlds generated from the SAME seed over the SAME area
python3 compare.py "Terralith=before.npz" "Tuned=after.npz"
```

## What each script does

| Script | Answers |
|---|---|
| `survey.py` | Reads region files → per-chunk ground height, water depth, and 16 surface biome samples. Writes a `.npz`. Everything else consumes that. |
| `census.py` | Biome-category percentages + physical water coverage for one world. Set `TERRALITH_DIR` to an unpacked Terralith jar so the grouping uses Terralith's own tag files. |
| `compare.py` | The money table — several worlds side by side. |
| `paired.py` | Chunk-for-chunk diff of two worlds: how many chunks rose, fell, stayed. This is what proves a change is one-directional. |
| `perbiome.py` | Per-biome measured ground height and relief. Answers "is `terralith:highlands` actually flat now?" |
| `landmarks.py` | Reads specific recorded coordinates back out of each world. This is the seed-caveat check. |
| `spline.py` | Evaluates Minecraft's cubic splines straight from the shipped JSON, so terrain can be reasoned about without generating anything. |
| `run-test.sh` | Generates a throwaway test world: boots a local Fabric server, Chunky-pregens a square, saves and stops. |

## Definitions the numbers rest on

- **Ground height** is the 5th percentile of the `OCEAN_FLOOR` heightmap over a
  chunk's 256 columns. The low percentile makes it effectively tree-free — some
  column in a 16×16 always misses the canopy.
- **Local relief** is the largest ground-height change to any of a chunk's four
  neighbours: blocks of rise or fall per 16 blocks travelled. Chunks missing a
  neighbour are excluded rather than guessed.
- **Water** is counted from fluid columns, never from biome names, so it can be
  cross-checked against the biome census independently.
- **Surface biome** is sampled at the game's own 4×4 biome-cell resolution,
  16 per chunk, at `max(WORLD_SURFACE, sea level)` so ocean columns report the
  ocean rather than whatever cave biome sits on the floor.

## Generating test worlds

`run-test.sh <name> <radius-blocks> [datapack-dir]` needs a server skeleton —
a directory holding `fabric-server-launch.jar`, `libraries/`, `versions/` and a
`mods/` set. Point at it with `SKEL_DIR`:

```sh
SKEL_DIR=~/mc-test-skeleton TEST_PORT=25599 ./run-test.sh tuned 2300 ../../src
```

Every run uses the same `SEED` (default `-160353759327030922`) so variants are
directly comparable. It binds to `127.0.0.1` on `TEST_PORT` — set that to
something other than 25565 so it can never collide with a real client or server.

Two things worth knowing, both learned the hard way:

- **Set `-Dmax.bg.threads`.** Without it, Chunky pregen ran at 8 chunks/sec; with
  12 worldgen threads it ran at 87. Same machine, 10× difference.
- **Verify pregen finished by reading the log, not by trusting the command.**
  The script polls for `Task finished for`. `chunky cancel` in particular does
  *not* stop a task — it asks for confirmation and keeps generating.

## Rig fidelity

Before trusting any before/after from a local rig, prove the rig reproduces
production. Survey the real world's region files and `paired.py` them against a
local baseline at the same seed. For this work that came out at **100.0 % biome
match and 97.2 % identical ground height across 51,605 shared chunks** — which
is also what established that the structure mods contribute nothing to terrain.
