#!/usr/bin/env bash
# Usage: bash scripts/prepare-image-context.sh <empty-dest> [existing-tarball]
# No installs/builds/hooks. CI packs here; release publishing reuses its one pack.
set -euo pipefail
if [ "$#" -lt 1 ] || [ "$#" -gt 2 ]; then
  echo 'Usage: prepare-image-context.sh <empty-dest> [existing-tarball]' >&2
  exit 1
fi
project_root=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
context_dest=$1
mkdir -p -- "$context_dest"
if [ -n "$(ls -A -- "$context_dest")" ]; then
  echo 'Image build context must be empty; refusing to overwrite it.' >&2
  exit 1
fi
if [ "$#" -eq 2 ]; then
  cp -- "$2" "$context_dest/release.tgz"
else
  # npm's JSON output gives the exact filename, without a wildcard choosing an
  # unrelated tarball. Resolve the destination before changing directories.
  context_dest=$(cd -- "$context_dest" && pwd)
  cd -- "$project_root"
  packed_name=$(npm pack --ignore-scripts --json --pack-destination "$context_dest" |
    node --input-type=module -e '
      let text = "";
      for await (const chunk of process.stdin) text += chunk;
      const packed = JSON.parse(text);
      if (packed.length !== 1) throw new Error("Expected exactly one npm tarball");
      process.stdout.write(packed[0].filename);
    ')
  mv -- "$context_dest/$packed_name" "$context_dest/release.tgz"
fi
cp -- "$project_root/package-lock.json" "$context_dest/"
