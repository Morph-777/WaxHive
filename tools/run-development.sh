#!/usr/bin/env bash
set -euo pipefail
music_source="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$music_source/builddir/data" "$music_source/builddir/config"
glib-compile-resources "$music_source/data/org.gnome.Music.gresource.xml" \
    --sourcedir="$music_source/data" \
    --target="$music_source/builddir/data/org.gnome.Music.gresource"
cp "$music_source/data/org.gnome.Music.gschema.xml" "$music_source/builddir/data/"
glib-compile-schemas --strict "$music_source/builddir/data"
music_backend=keyfile
music_entry="$music_source/tools/development.py"
music_renderer=()
if [[ "${1:-}" == "--smoke-test" ]]; then
    music_backend=memory
    music_renderer=(--env=GSK_RENDERER=cairo)
elif [[ "${1:-}" == "--check-workspace" ]]; then
    music_backend=memory
    music_renderer=(--env=GSK_RENDERER=cairo)
    music_entry="$music_source/tools/check-workspace.py"
    shift
fi
exec flatpak run --filesystem="$music_source" "${music_renderer[@]}" \
    --env=GSETTINGS_SCHEMA_DIR="$music_source/builddir/data" \
    --env=GSETTINGS_BACKEND="$music_backend" \
    --env=XDG_CONFIG_HOME="$music_source/builddir/config" \
    --command=python3 org.gnome.Music "$music_entry" "$@"
