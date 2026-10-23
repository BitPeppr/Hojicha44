#!/usr/bin/env bash
# Fetch the pinned KLP Lame keycap STEP sources (CC-BY-SA-4.0).
# Idempotent; writes to /tmp/kbd-renders/keycaps (scratch — the build
# regenerates mesh assets from these on every run).
set -euo pipefail
DIR="${KEYCAP_DIR:-/tmp/kbd-renders/keycaps}"
mkdir -p "$DIR"
BASE="https://raw.githubusercontent.com/braindefender/KLP-Lame-Keycaps/master/STEP/Choc%20Stem%20%2B%20Choc%20Size"
for v in Saddle Saddle_Tilted Saddle_Homing Normal_Tilted Thumb; do
  f="$DIR/klp_${v}.step"
  if [ -s "$f" ]; then echo "have $f"; continue; fi
  curl -sL -o "$f" "$BASE/Choc_Stem_Choc_Size_${v}.step"
  echo "fetched $f ($(stat -f%z "$f") bytes)"
done
curl -s "https://api.github.com/repos/braindefender/KLP-Lame-Keycaps/commits/master" \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print('pinned commit:', d['sha'], '|', d['commit']['committer']['date'])" \
  > "$DIR/PINNED_SOURCE.txt"
cat "$DIR/PINNED_SOURCE.txt"
