#!/usr/bin/env python3
"""Run the source checkout using the installed Music Flatpak's dependencies."""
from pathlib import Path
import sys
import traceback

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))

import gi
gi.require_versions({"Adw": "1", "Gtk": "4.0", "Gst": "1.0"})
from gi.repository import Adw, Gio, GLib, Gst

Gst.init(None)
Adw.init()
resource = Gio.Resource.load(str(SOURCE / "builddir/data/org.gnome.Music.gresource"))
Gio.Resource._register(resource)

from gnomemusic.application import Application
from gnomemusic.utils import View

# Separate instance and settings from the installed GNOME Music application.
app_id = "org.gnome.Music.LayoutSmoke" if "--smoke-test" in sys.argv else "org.gnome.Music.LayoutDev"
app = Application(app_id, "51.alpha-layout")
errors = []
def exception_hook(*args):
    errors.append(args[1])
    traceback.print_exception(*args)
sys.excepthook = exception_hook
if "--smoke-test" in sys.argv:
    def capture(name):
        from gi.repository import Gtk
        window = app.props.window
        paintable = Gtk.WidgetPaintable.new(window)
        snapshot = Gtk.Snapshot.new()
        paintable.snapshot(snapshot, window.get_width(), window.get_height())
        node = snapshot.to_node()
        if node is None:
            return False
        texture = window.get_renderer().render_texture(node, None)
        texture.save_to_png(str(SOURCE / f"builddir/{name}.png"))
        return True

    def finish():
        window = app.props.window
        print("SMOKE: window created; active view:",
              window.props.active_view.props.name if window.props.active_view else "empty")
        if window.props.active_view is not None:
            albums = window.views[View.ARTIST]._artist_album._listbox
            row = albums.get_row_at_index(0)
            if row is not None:
                album = row.get_child().props.corealbum
                total = sum(song.props.duration for disc in album.props.model for song in disc.props.model)
                assert album.props.duration == total, "Album duration matches indexed tracks"
                print("SMOKE: album metadata:", row.get_child()._released_label.get_label())
            page = window._stack.get_page(window.views[View.NOW_PLAYING])
            assert not page.get_visible(), "No redundant Now Playing tab on desktop"
            if not capture("music-library-wide"):
                return GLib.SOURCE_CONTINUE
            window.set_default_size(360, 760)
            GLib.timeout_add(750, finish_narrow)
        else:
            app.quit()
        return GLib.SOURCE_REMOVE

    narrow_attempts = 0
    def finish_narrow():
        global narrow_attempts
        narrow_attempts += 1
        if not capture("music-library-narrow"):
            if narrow_attempts < 5:
                return GLib.SOURCE_CONTINUE
            errors.append(RuntimeError("The narrow window did not render"))
            app.quit()
            return GLib.SOURCE_REMOVE
        window = app.props.window
        assert window._stack.get_page(window.views[View.NOW_PLAYING]).get_visible()
        assert window._player_toolbar._volume_button.get_parent() is window._player_toolbar._controls_box
        print("SMOKE: narrow width:", window.get_width())
        app.quit()
        return GLib.SOURCE_REMOVE

    def size_window():
        app.props.window.unmaximize()
        app.props.window.set_default_size(1280, 800)
        GLib.timeout_add_seconds(3, finish)
        return GLib.SOURCE_REMOVE
    GLib.timeout_add_seconds(5, size_window)
    sys.argv.remove("--smoke-test")
exit_code = app.run(sys.argv)
sys.exit(1 if errors else exit_code)
