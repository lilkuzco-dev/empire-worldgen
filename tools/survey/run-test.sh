#!/usr/bin/env bash
# run-test.sh <variant-name> <radius-blocks> [datapack-dir]
#
# Boots a throwaway local Fabric 26.2 server in runs/<variant>/, pregenerates a
# square of <radius> blocks around 0,0 with Chunky, then saves and stops cleanly.
# Every run uses the SAME seed so variants are directly comparable.
#
# Cleanup law: we record the exact PID we launched and only ever kill that PID.
set -uo pipefail

SCRATCH="${WORK_DIR:-$(cd "$(dirname "$0")" && pwd)}"
# a server skeleton: fabric-server-launch.jar, libraries/, versions/, mods/
SKEL="${SKEL_DIR:-$SCRATCH/tsrv}"
VARIANT="$1"
RADIUS="$2"
DATAPACK="${3:-}"
SEED="${SEED:--160353759327030922}"
JAVA_HOME="${JAVA_HOME:-$HOME/jdks/jdk-25.0.4+7/Contents/Home}"
RUN="$SCRATCH/runs/$VARIANT"

rm -rf "$RUN"
mkdir -p "$RUN/mods" "$RUN/config"
# share the heavy immutable bits, copy the light mutable bits
ln -s "$SKEL/libraries" "$RUN/libraries"
ln -s "$SKEL/versions"  "$RUN/versions"
cp "$SKEL/fabric-server-launch.jar" "$RUN/"
cp "$SKEL"/mods/*.jar "$RUN/mods/"
# MODS_EXCLUDE="pattern|pattern" removes jars, for isolating a mod's effect
if [ -n "${MODS_EXCLUDE:-}" ]; then
  for j in "$RUN"/mods/*.jar; do
    case "$(basename "$j")" in
      *) if echo "$(basename "$j")" | grep -qiE "$MODS_EXCLUDE"; then
           rm -f "$j"; echo "[harness] excluded $(basename "$j")"
         fi ;;
    esac
  done
fi
echo "eula=true" > "$RUN/eula.txt"

cat > "$RUN/server.properties" <<EOF
server-ip=127.0.0.1
server-port=${TEST_PORT:-25599}
level-name=world
level-seed=$SEED
level-type=minecraft\\:normal
online-mode=false
white-list=false
max-players=1
view-distance=3
simulation-distance=3
spawn-protection=0
sync-chunk-writes=false
enable-rcon=false
pause-when-empty-seconds=-1
motd=terrain test $VARIANT
EOF

# variant datapack: a real mod-style jar dropped in mods/ so it loads exactly
# the way the shipped tuning will
if [ -n "$DATAPACK" ] && [ -d "$DATAPACK" ]; then
  ( cd "$DATAPACK" && zip -q -r "$RUN/mods/zz-tuning.jar" . )
  echo "[harness] tuning pack applied: $(unzip -l "$RUN/mods/zz-tuning.jar" | tail -1)"
fi

FIFO="$RUN/cmd.fifo"
mkfifo "$FIFO"
# a permanent dummy writer keeps the fifo from EOF-ing between our writes
sleep 100000 > "$FIFO" &
HOLDER=$!

cd "$RUN"
"$JAVA_HOME/bin/java" -Xmx8G -XX:+UseG1GC -Dmax.bg.threads=12 -jar fabric-server-launch.jar nogui \
    < "$FIFO" > server.log 2>&1 &
SERVER_PID=$!
echo "$SERVER_PID" > "$RUN/server.pid"
echo "[harness] variant=$VARIANT server pid=$SERVER_PID holder pid=$HOLDER radius=$RADIUS"

# ---- wait for boot ----------------------------------------------------------
for _ in $(seq 1 120); do
  grep -q 'Done (.*)! For help' server.log && break
  sleep 2
done
if ! grep -q 'Done (.*)! For help' server.log; then
  echo "[harness] FAILED to boot"; kill "$SERVER_PID" 2>/dev/null; kill "$HOLDER" 2>/dev/null; exit 1
fi
echo "[harness] booted: $(grep -o 'Done ([^)]*)' server.log | tail -1)"
grep -iE 'Seed:' server.log | tail -2

# ---- pregen -----------------------------------------------------------------
{
  echo "chunky world minecraft:overworld"
  echo "chunky center 0 0"
  echo "chunky shape square"
  echo "chunky radius $RADIUS"
  echo "chunky quiet 30"
  echo "chunky start"
} > "$FIFO"

START=$(date +%s)
# Verify by EFFECT, not reply text: poll until the completion line appears.
while true; do
  if grep -q 'Task finished for' server.log; then
    echo "[harness] pregen complete after $(( $(date +%s) - START ))s"; break
  fi
  if ! kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "[harness] server died during pregen"; break
  fi
  if [ $(( $(date +%s) - START )) -gt 5400 ]; then
    echo "[harness] TIMEOUT, pausing pregen"; echo "chunky pause" > "$FIFO"; sleep 10; break
  fi
  sleep 15
done
tail -3 server.log

# ---- clean shutdown ---------------------------------------------------------
{ echo "save-all flush"; } > "$FIFO"
sleep 10
{ echo "stop"; } > "$FIFO"
for _ in $(seq 1 60); do
  kill -0 "$SERVER_PID" 2>/dev/null || break
  sleep 2
done
if kill -0 "$SERVER_PID" 2>/dev/null; then
  echo "[harness] stop did not exit the JVM; killing recorded pid $SERVER_PID"
  kill "$SERVER_PID"
fi
kill "$HOLDER" 2>/dev/null
rm -f "$FIFO"

N=$(find "$RUN/world/dimensions/minecraft/overworld/region" -name '*.mca' -size +8k 2>/dev/null | wc -l | tr -d ' ')
echo "[harness] DONE variant=$VARIANT  non-empty region files: $N"
