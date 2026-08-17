# vendor/vanilla-26.2

`offset.json`, `factor.json`, `jaggedness.json` for `minecraft:overworld`, taken
verbatim from Minecraft 26.2's **own** data dump — not transcribed, not guessed:

```sh
java -cp "versions/26.2/server-26.2.jar:$(find libraries -name '*.jar' | tr '\n' ':')" \
     net.minecraft.data.Main --all --output <dir>
# <dir>/data/minecraft/worldgen/density_function/overworld/{offset,factor,jaggedness}.json
```

The server jar was pulled from the Empire server (`/versions/26.2/server-26.2.jar`,
24,952,681 bytes), so these are the exact curves the production server would use if
Terralith were absent.

They are the reference the tuning blends toward. Re-dump them on any Minecraft
version bump — a stale copy would silently blend toward the wrong terrain.
