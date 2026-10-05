#!/usr/bin/env bash
set -euo pipefail
wax_source="$(cd "$(dirname "$0")/.." && pwd)"
flatpak install --user --noninteractive "$wax_source/dist/WaxHive.flatpak"
python3 "$wax_source/tools/migrate-settings.py"
