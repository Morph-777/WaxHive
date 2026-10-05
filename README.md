# WaxHive

WaxHive is a personal fork of [GNOME Music](https://gitlab.gnome.org/GNOME/gnome-music), built with GTK 4 and libadwaita. Its desktop layout puts album artists on the left, albums and compact track lists in the center, and the playing queue and track information on the right. Panel sizes are remembered, artwork corners are configurable, and playback controls include an inline volume slider.

WaxHive has its own application identity, `io.github.Morph777.WaxHive`, launcher, and settings. It can be installed alongside GNOME Music. It uses the GNOME Music icon and credits the original contributors; this is an independent fork.

## Install on Bluefin or another Flatpak desktop

Download `WaxHive.flatpak` from [Releases](https://github.com/Morph-777/WaxHive/releases), then run:

```sh
flatpak install --user ./WaxHive.flatpak
flatpak run io.github.Morph777.WaxHive
```

The launcher appears as **WaxHive**. No package layering, distrobox, or checkout is needed to run it. The GNOME 51 runtime is downloaded from Flathub if necessary. Music in your Music folder is available inside the sandbox; the app uses the desktop's music index when available and includes its own indexer as a fallback.

For a library elsewhere, explicitly grant its directory:

```sh
flatpak override --user --filesystem=/path/to/music io.github.Morph777.WaxHive
```

Install a newer release with the same `flatpak install --user ./WaxHive.flatpak` command and choose to update the installed app. Bundle releases require this manual update step. There is no hosted automatic-update Flatpak repository yet.

## Build and install from source

```sh
git clone --recurse-submodules https://github.com/Morph-777/WaxHive.git
cd WaxHive
flatpak remote-add --user --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install --user flathub org.flatpak.Builder org.gnome.Sdk//51 org.gnome.Platform//51
bash tools/build-flatpak.sh
bash tools/install-flatpak.sh
```

The installer is written to `dist/WaxHive.flatpak`. A companion `WaxHive.Sources.flatpak` contains the application and bundled dependency sources; it is for source redistribution, not required to run WaxHive. Dependencies are pinned by the manifest, while the final application module builds this checkout. The installation helper copies development preferences once if WaxHive has no settings yet, preserving existing WaxHive preferences on later updates.

For an installed-app smoke test:

```sh
flatpak run --filesystem="$PWD" --env=GSETTINGS_BACKEND=memory --env=GSK_RENDERER=cairo \
  --command=python3 io.github.Morph777.WaxHive "$PWD/tools/check-installed.py"
```

The older development runner and fixture checks use the installed `org.gnome.Music` Flatpak:

```sh
bash tools/run-development.sh --check-workspace
bash tools/run-development.sh --smoke-test
```

## Maintenance

The `main` branch retains GNOME Music's Git history. The upstream project remains at `https://gitlab.gnome.org/GNOME/gnome-music.git`. Keep it as an `upstream` remote when pulling changes into this fork:

```sh
git remote add upstream https://gitlab.gnome.org/GNOME/gnome-music.git
git fetch upstream
git merge upstream/master
```

Resolve conflicts, run the checks, and rebuild before publishing. GitHub Actions builds a Flatpak for pushes and pull requests. Version tags beginning with `v` publish the bundle as a GitHub release. Change the Meson version and AppStream release entry together before tagging a new version. Please report WaxHive-specific issues in [this repository](https://github.com/Morph-777/WaxHive/issues).

## License and attribution

WaxHive preserves GNOME Music's [LICENSE](LICENSE), source copyright notices, and GStreamer exception. Application code is GNU GPL version 2 or later with that exception; other components and assets retain their existing licenses. See [NOTICE](NOTICE) for attribution. The build manifest identifies the source URLs and checksums of bundled dependencies. Public source and build instructions accompany each release.
