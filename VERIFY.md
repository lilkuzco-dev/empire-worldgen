# Empire Worldgen 0.1.0 verification

Verified from release commit `842dec2` on 2026-08-18.

- `python3 tools/build-pack.py 0.75 src`: regenerated every tracked source file with no diff.
- The JAR contains only `fabric.mod.json`, `pack.mcmeta`, the three vendored vanilla reference
  density functions, and the three Lithostitched wrapping modifiers.
- Server-side load check with Minecraft 26.2, Fabric API, Terralith 2.6.4,
  Lithostitched 1.8.0+beta3, and the current empire mod set: PASS (58 top-level mods plus 109
  bundled libraries).
- Release: <https://github.com/lilkuzco-dev/empire-worldgen/releases/tag/v0.1.0>
- Release asset SHA-512:
  `bf85432377dba9a81bffb3750be0850dc15c8753b5fbe73818e3319dec90833daf41b1b01c562edadf5fefb07e4efe60f7d334b100a59e3552a3af003582b72d`
- The downloaded GitHub asset was byte-for-byte identical to the local build.
- Root manifest commit: `212a97d`; entry is `side: server`.
- `tools/postship-check.sh`: PASS after independently downloading and hashing the server-only
  release asset; client convergence remained a zero-change plan.

No world was reset and no live server was deployed. The terrain changes apply only to chunks
generated after the mod is present on a server.
