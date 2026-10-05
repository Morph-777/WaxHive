#!/usr/bin/env python3
"""Smoke-test the installed WaxHive modules and resources, not the checkout."""
import sys
import traceback
import gi

gi.require_versions({'Adw': '1', 'Gtk': '4.0', 'Gst': '1.0'})
from gi.repository import Adw, Gio, GLib, Gst
Gst.init(None)
Adw.init()
Gio.Resource._register(Gio.Resource.load('/app/share/io.github.Morph777.WaxHive/org.gnome.Music.gresource'))
import gnomemusic
assert gnomemusic.__file__.startswith('/app/'), gnomemusic.__file__
from gnomemusic.application import Application
from gnomemusic.utils import View
app = Application('io.github.Morph777.WaxHive', '0.1.1')
errors = []
def failed(*args):
    errors.append(args[1])
    traceback.print_exception(*args)
    app.quit()
sys.excepthook = failed

narrow_attempts = 0
def narrow():
    global narrow_attempts
    narrow_attempts += 1
    window = app.props.window
    if window.get_width() > 1100 and narrow_attempts < 10:
        return GLib.SOURCE_CONTINUE
    assert window._stack.get_page(window.views[View.NOW_PLAYING]).get_visible()
    assert window._player_toolbar._volume_button.get_parent() is window._player_toolbar._controls_box
    print('PASS: installed WaxHive narrow layout')
    app.quit()
    return GLib.SOURCE_REMOVE

def wide():
    window = app.props.window
    assert window.get_title() == 'WaxHive'
    assert app.props.settings.props.schema_id == 'io.github.Morph777.WaxHive'
    assert window.props.active_view is not None, 'Music library did not load'
    assert not window._stack.get_page(window.views[View.NOW_PLAYING]).get_visible()
    print('PASS: installed WaxHive resources, independent settings and desktop layout')
    window.set_default_size(360, 760)
    GLib.timeout_add_seconds(2, narrow)
    return GLib.SOURCE_REMOVE

def size():
    assert app.props.window is not None
    app.props.window.unmaximize()
    app.props.window.set_default_size(1280, 800)
    GLib.timeout_add_seconds(4, wide)
    return GLib.SOURCE_REMOVE

def timeout():
    errors.append(RuntimeError('Installed application smoke test timed out'))
    app.quit()
    return GLib.SOURCE_REMOVE
GLib.timeout_add_seconds(5, size)
GLib.timeout_add_seconds(30, timeout)
code = app.run([sys.argv[0]])
sys.exit(1 if errors else code)
