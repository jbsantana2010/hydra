#!/usr/bin/env bash
set -euo pipefail

RUFLO_VERSION="3.6.30"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUFLO_DIR="$ROOT_DIR/ruflo"

mkdir -p "$RUFLO_DIR"
cd "$RUFLO_DIR"

if [ ! -f package.json ]; then
  cat > package.json <<JSON
{
  "name": "hydra-ruflo-zone-a",
  "private": true,
  "version": "0.1.0",
  "description": "Local Ruflo install for HYDRA Zone A artifact generation only.",
  "scripts": {
    "ruflo": "ruflo"
  },
  "dependencies": {}
}
JSON
fi

npm install "ruflo@$RUFLO_VERSION" --save-exact

echo "Ruflo $RUFLO_VERSION installed in $RUFLO_DIR"
echo "Boundary reminder: Ruflo is Zone A only. No Gumroad credentials, publishing, spending, or final approvals."
