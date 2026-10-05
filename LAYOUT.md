# GNOME Music library workspace

This checkout starts from GNOME Music master. It adapts the browsing layout
from the connected Foobee conversation using GTK 4 and libadwaita.

Music opens by default, with three columns:

- Album artists from album tags, oldest-album artwork and album counts.
  Albums without an album-artist tag appear under Unknown Album Artist.
  Click or use the keyboard to select an artist; hovering does not select.
- The selected artist's albums in chronological order, with cover art and
  metadata beside each album's compact track rows. Album titles wrap fully in
  a fixed desktop column, including artist and composer credits, and albums
  use the available center width. Covers align with the left edge of the text. Double-click
  a track to play. Right-click a track to open its menu; the Menu key or
  Shift+F10 also opens it. Keyboard activation remains available.
- The actual playback queue, continuously numbered, followed by track
  information with a regular-size bold title and full-width square artwork.
  Only the information text scrolls; artwork remains fully visible and sits
  at the bottom of the panel, above the transport bar. Long information fields
  abbreviate within the panel and expose their full text as tooltips. Click the artwork to open a
  larger libadwaita dialog.

Selecting an artist changes the browser without starting playback or creating
a playlist. Playback starts an artist-scoped queue that continues independently
when another artist is browsed. Queue rows follow playback and shuffle order.
The playback menu offers Shuffle Tracks and Shuffle Albums; album shuffle
keeps disc and track order within each album and finishes the current album
before moving to another. Both operate on the active queue. When started from
Music, that queue belongs to the selected album artist.

Typing letters in a focused list selects matching entries; repeated letters
cycle through matches. Ctrl+F opens search. The progress bar ignores scrolling;
the volume slider adjusts by one percent of its range per scroll step. Artwork
uses sharp corners by default. Preferences → Appearance → Rounded Artwork
Corners changes all album and artist artwork immediately and remembers the
choice. Scrollbar handles have no dark outline, and the bottom bar has no
raised shadow.

The header offers Music and Playlists on the three-column desktop, plus search
and the standard
application menu. The album grid remains available through Alt+1. Alt+2 opens
Music, Alt+3 opens Playlists and Alt+4 opens Now Playing. The full-width bottom
transport remains visible when nothing is playing, with playback disabled until
a track is chosen. It has transport controls, track text and time above
the progress bar, with a permanently visible volume slider beside the progress
bar. The bottom bar does not show artwork.

Drag the six-pixel boundaries at the album-artist and playback columns to change
their width. Both column widths are saved in settings and restored on launch.
A native vertical GTK splitter sizes the queue and track-information
sections independently; its position is also saved. GTK scrollers handle mouse wheels, trackpads and scrollbar
dragging. Colors, typography, favorites and symbolic icons follow GNOME's theme
and accent rather than the previous application's custom palette.

Below 1100 pixels, the playback sidebar collapses; the Now Playing page remains
available. Below 700 pixels, the artist list also collapses behind the sidebar
button, and header navigation becomes a menu. Now Playing is available when
the playback sidebar is collapsed. The narrow transport places volume beside
the playback buttons. Album content becomes vertical
only at this narrow breakpoint; the desktop arrangement stays horizontal. The selected artist is remembered between launches; playback itself
is not restored automatically.

## Run on this machine

The installed `org.gnome.Music` Flatpak supplies the GTK, libadwaita, LocalSearch,
Grilo and GStreamer dependencies. The development launcher compiles resources
and schemas, then loads Python code directly from this checkout:

```bash
cd /var/home/morph/PROJECTS/gnome-musicbee/gnome-music
bash tools/run-development.sh
```

The development app uses `org.gnome.Music.LayoutDev` and separate settings in
`builddir/config`. It does not replace the installed Music application. It reads
the same indexed music library; changes to favorites still affect library
metadata. A standard Meson build remains supported in an environment with the
dependencies listed in `meson.build`.

## Validation

```bash
bash tools/run-development.sh --check-workspace
bash tools/run-development.sh --smoke-test
```

The integration check uses a deterministic fixture library and memory-only
settings. It checks artist restoration, independent browsing/playback, artist
queue scope, row recycling, queue notifications, album shuffle and playback
history, next/previous behavior, resizing, adaptive layouts, artwork dialogs and
empty playback. It also executes the album-artist queries against tagged and
untagged fixtures, checks oldest-album covers, compact rows, real queue scrolling,
full-width square artwork and the live volume binding. Additional checks cover
long artist/composer credits, bottom anchoring, narrow volume placement and
restoring the saved split positions in a newly created view. It also verifies
asynchronous album-duration aggregation, right-click track menus and live
artwork preference changes. Focus colors are verified by comparing rendered header and transport pixels
between focused and backdrop states, including both sliders and track text. It renders previews to `builddir/workspace-wide.png` and
`builddir/workspace-narrow.png`.

The smoke test launches the full application against the indexed library,
checks desktop and 360-pixel layouts, and saves `builddir/music-library-wide.png`
and `builddir/music-library-narrow.png`. It uses memory-only settings.

The installed runtime logs a theme preference warning and embedded JPEG artwork
conversion warnings for two existing albums. The layout and smoke checks pass;
those runtime warnings remain. A full Meson/package build has not been run on
the host, which lacks the GTK development packages and Meson.
