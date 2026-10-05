#!/usr/bin/env bash
set -euo pipefail
wax_source="$(cd "$(dirname "$0")/.." && pwd)"
cd "$wax_source"
git submodule update --init --recursive
mkdir -p builddir dist
flatpak run org.flatpak.Builder --user --force-clean --disable-rofiles-fuse \
    --bundle-sources --default-branch=stable --repo=builddir/flatpak-repo \
    builddir/flatpak-app io.github.Morph777.WaxHive.json
flatpak build-bundle builddir/flatpak-repo dist/WaxHive.flatpak \
    io.github.Morph777.WaxHive stable \
    --runtime-repo=https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak build-bundle --runtime builddir/flatpak-repo dist/WaxHive.Sources.flatpak \
    io.github.Morph777.WaxHive.Sources stable
printf 'Installer: %s/dist/WaxHive.flatpak\n' "$wax_source"
