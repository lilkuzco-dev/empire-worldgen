# Empire Worldgen verification

## 0.2.0

Released and deployed from commit `7bff9e1` on 2026-08-19.

- `python3 tools/build-pack.py 1.0 src`: the default and explicit-strength builds were
  byte-for-byte source-identical.
- All generated JSON parsed successfully, and `unzip -t` passed on the release JAR.
- Release: <https://github.com/lilkuzco-dev/empire-worldgen/releases/tag/v0.2.0>
- Release asset SHA-512:
  `a32d2aafc9eb11ad8c3caf3bfcdc6bff15565970e4471501da25148109590b2c04e72380f91b5be1c1b13542648c986d5c4585313a2bbfb7b47a7b94d3bac10a`
- An independent download of the GitHub asset was byte-for-byte identical to the local
  release artifact.
- Root manifest commit: `a933f72`; entry remains `side: server`.
- `tools/postship-check.sh`: PASS, including independent direct-URL hashing and full
  manifest dependency validation.
- Server deploy: PASS. The server completed a fresh boot, all 43 manifest mods appeared
  in the log, no mod-loading errors were present, and remote/staging filename-and-size
  parity was green.

Terrain appearance has not been verified in-game. The 1.0 blend applies only to chunks
generated after this deployment; existing chunks retain their previous terrain.

## 0.1.0

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
