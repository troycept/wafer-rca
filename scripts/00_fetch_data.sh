#!/usr/bin/env bash
# Fetch WM-811K from the MIR Lab mirror (no Kaggle account needed).
# ~344 MB zip -> data/raw/LSWMD.pkl
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RAW="$ROOT/data/raw"
mkdir -p "$RAW"

if [[ ! -f "$RAW/MIR-WM811K.zip" ]]; then
  curl -L --fail -o "$RAW/MIR-WM811K.zip" http://mirlab.org/dataSet/public/MIR-WM811K.zip
fi

if [[ ! -f "$RAW/LSWMD.pkl" ]]; then
  unzip -j -o "$RAW/MIR-WM811K.zip" '*LSWMD.pkl' -d "$RAW"
fi

ls -lh "$RAW/LSWMD.pkl"
