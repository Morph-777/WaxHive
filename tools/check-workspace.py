#!/usr/bin/env python3
"""Native GTK integration checks with an isolated, deterministic library."""
from pathlib import Path
from types import SimpleNamespace
import sys
import traceback

SOURCE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SOURCE))
import gi
gi.require_versions({"Adw": "1", "Gtk": "4.0", "Gst": "1.0", "Tsparql": "3.0", "Graphene": "1.0", "GdkPixbuf": "2.0"})
from gi.repository import Adw, Gio, GLib, GObject, GdkPixbuf, Graphene, Gst, Gtk, Tsparql
Gst.init(None)
Adw.init()
Gio.Resource._register(Gio.Resource.load(
    str(SOURCE / "builddir/data/org.gnome.Music.gresource")))

from gnomemusic.listnavigation import ListNavigation
from gnomemusic.corealbum import CoreAlbum
from gnomemusic.coreartist import CoreArtist
from gnomemusic.coredisc import CoreDisc
from gnomemusic.coremodel import CoreModel
from gnomemusic.coresong import CoreSong
from gnomemusic.musiclogger import MusicLogger
from gnomemusic.queue import Queue
from gnomemusic.search import Search
from gnomemusic.shufflelistmodel import ShuffleListModel
from gnomemusic.views.artistsview import ArtistsView
from gnomemusic.widgets.nowplayingpanel import QueueRow
from gnomemusic.widgets.albumwidget import AlbumWidget
from gnomemusic.widgets.preferencesdialog import PreferencesDialog
from gnomemusic.widgets.songwidget import SongWidget
from gnomemusic.utils import RepeatMode
from gnomemusic.player import Player
from gnomemusic.gstplayer import Playback
from gnomemusic.widgets.playertoolbar import PlayerToolbar

# Execute the production SPARQL against tagged, guest-performer and untagged albums.
connection = Tsparql.SparqlConnection.new(
    Tsparql.SparqlConnectionFlags.NONE, None,
    Tsparql.sparql_get_ontology_nepomuk(), None)
connection.update('''
INSERT DATA { GRAPH tracker:Audio {
  <urn:artist:owner> a nmm:Artist; nmm:artistName "Album Owner" .
  <urn:artist:guest> a nmm:Artist; nmm:artistName "Guest Performer" .
  <urn:album:tagged> a nmm:MusicAlbum; nie:title "Tagged Album";
    nmm:albumArtist <urn:artist:owner> .
  <urn:album:untagged> a nmm:MusicAlbum; nie:title "Untagged Album" .
  <urn:song:one> a nmm:MusicPiece; nmm:musicAlbum <urn:album:tagged>;
    nmm:artist <urn:artist:owner> .
  <urn:song:two> a nmm:MusicPiece; nmm:musicAlbum <urn:album:tagged>;
    nmm:artist <urn:artist:guest> .
  <urn:song:three> a nmm:MusicPiece; nmm:musicAlbum <urn:album:untagged>;
    nmm:artist <urn:artist:guest> .
} }
''', None)
def query_text(name):
    return (SOURCE / f"data/queries/{name}.rq").read_text().replace(
        "SERVICE <dbus:{bus_name}>", "").replace("{location_filter}", "")
cursor = connection.query(query_text("artists"), None)
artist_rows = []
while cursor.next(None):
    artist_rows.append(tuple(cursor.get_string(i)[0] for i in range(3)))
assert set(artist_rows) == {
    ("urn:artist:owner", "Album Owner", "1"),
    ("urn:gnome-music:unknown-album-artist", "", "1")}
statement = connection.query_statement(query_text("artist_albums"), None)
for owner, expected in (("urn:artist:owner", "urn:album:tagged"),
                        ("urn:gnome-music:unknown-album-artist", "urn:album:untagged")):
    statement.bind_string("artist", owner)
    cursor = statement.execute(None)
    assert cursor.next(None) and cursor.get_string(0)[0] == expected
    assert not cursor.next(None)
connection.close()

errors = []
def exception_hook(*args):
    errors.append(args[1])
    traceback.print_exception(*args)
sys.excepthook = exception_hook

class FixturePlayer(GObject.GObject):
    __gsignals__ = {"song-changed": (GObject.SignalFlags.RUN_FIRST, None, ())}
    current_song = GObject.Property(type=CoreSong)

    def play(self, song):
        for item in context.props.coremodel.props.queue:
            item.props.state = SongWidget.State.UNPLAYED
            if item == song:
                item.props.state = SongWidget.State.PLAYING
                self.props.current_song = item
        self.emit("song-changed")

gtk_app = Adw.Application(application_id="org.gnome.Music.WorkspaceTest",
                          flags=Gio.ApplicationFlags.NON_UNIQUE)
gtk_app.register(None)
window = Adw.ApplicationWindow(application=gtk_app, default_width=1280,
                               default_height=800, title="Music — Layout Test")
settings = Gio.Settings.new("org.gnome.Music")
context = SimpleNamespace(props=SimpleNamespace(
    window=window, settings=settings, log=MusicLogger(), search=Search(),
    player=FixturePlayer(), coregrilo=SimpleNamespace(writeback_tracker=lambda *args: None)))
context.props.coremodel = CoreModel(context)

def artist(name, album_titles):
    item = CoreArtist(context, {"id": name, "artist": name,
                               "albumCount": len(album_titles)})
    item._thumbnail = "generic"
    albums = Gio.ListStore.new(CoreAlbum)
    for number, title in enumerate(album_titles):
        album = CoreAlbum(context, {"id": name + title, "artist": name,
                                  "title": title, "publicationDate": str(2020 + number)})
        album._thumbnail = "generic"
        discs = Gio.ListStore.new(CoreDisc)
        disc = CoreDisc(context, album, 1)
        songs = Gio.ListStore.new(CoreSong)
        for track in range(1, 5):
            song = CoreSong(context, {
                "id": f"{name}-{title}-{track}", "title": f"Track {track}",
                "artist": name, "album": title, "album_urn": name + title,
                "trackNumber": track, "albumDiscNumber": 1, "duration": 210,
                "url": "file:///fixture.wav"})
            song._thumbnail = "generic"
            songs.append(song)
        disc._model = Gtk.SortListModel.new(songs, None)
        discs.append(disc)
        album._model = Gtk.SortListModel.new(discs, None)
        album.props.duration = 840
        albums.append(album)
    item._model = Gtk.SortListModel.new(albums, None)
    return item

first = artist("Aster", ["Morning Light", "Open Fields", "Quiet Hours"])
second = artist("Harbor", ["Tides", "A Very Long Album Title (Expanded Anniversary Edition With Additional Recordings) — " + "LongWord" * 12])
artists = Gio.ListStore.new(CoreArtist)
artists.append(first)
artists.append(second)
third = artist("Horizon", ["Sky"])
artists.append(third)
context.props.coremodel._artists_model_proxy.append(artists)
settings.set_string("selected-album-artist", "Harbor")
view = ArtistsView(context)
assert view._artist_album.props.coreartist is second, "Restore selected artist"
assert not view._sidebar.get_single_click_activate(), "No select-on-hover"
# Give the actual CoreArtist model unsorted albums to exercise chronological sorting.
album_store = Gio.ListStore.new(CoreAlbum)
for album in reversed(list(first.props.model)):
    album_store.append(album)
context.props.coremodel._albums_model_proxy.append(album_store)
context.props.coregrilo.get_artist_albums = lambda item, model: model.set_filter(
    Gtk.CustomFilter.new(lambda album: album.props.artist == item.props.artist))
first._model = first._get_artist_album_model()
first._thumbnail = None
assert first.props.thumbnail == "generic"
assert first._cover_album is first.props.model[0], "Use oldest album artwork"
view._on_artist_activated(view._sidebar, 0)
assert settings.get_string("selected-album-artist") == "Aster"
assert context.props.coremodel.props.queue.get_n_items() == 0, "Browsing must not queue"
album_row = view._artist_album._listbox.get_row_at_index(0)
album_widget = album_row.get_child()
song = first.props.model[0].props.model[0].props.model[1]
# Queue songs are independent copies; give them local fallback art in this fixture.
context.props.coremodel.connect(
    "queue-loaded", lambda *args: [setattr(s, "_thumbnail", "generic")
                                   for s in context.props.coremodel.props.queue])
album_widget._song_activated(None, SongWidget(song))
queue = context.props.coremodel.props.queue
assert queue.get_n_items() == 12, "Whole selected artist queue"
assert all(s.props.artist == "Aster" for s in queue)
panel = view._playback_split.get_sidebar().get_child()
assert panel._queue_stack.get_visible_child_name() == "queue"
assert panel._title.get_label() == "Track 2"
view._on_artist_activated(view._sidebar, 1)
long_metadata = view._artist_album._listbox.get_row_at_index(1).get_child()
long_metadata._artist_label.set_label("A Long Artist Name, Another Artist, And Several Guest Artists" * 3)
long_metadata._artist_label.set_visible(True)
long_metadata._composer_label.set_label("Jeff Bass, Luis Resto, Marshall Mathers, A Composer With A Very Long Name" * 2)
long_metadata._composer_label.set_visible(True)
assert queue.get_n_items() == 12 and all(s.props.artist == "Aster" for s in queue)
assert panel._title.get_label() == "Track 2", "Playback independent of browser"

# GTK factories recycle rows: the old song must no longer drive the new row.
row = QueueRow()
row.bind(queue[0], 0)
row.bind(queue[1], 1)
queue[0].props.state = SongWidget.State.PLAYING
assert row._title.get_label() == "Track 2"
row.unbind()
row.unbind()

notifications = []
queue.connect("items-changed", lambda *args: notifications.append(args[1:]))
queue.shuffle(0, 1, albums=True)
assert notifications, "Shuffle must notify live queue views"
assert len({s.props.id for s in queue}) == 12
album_sequence = [s.props.album for s in queue]
assert len([i for i, name in enumerate(album_sequence)
            if i == 0 or name != album_sequence[i - 1]]) == 3
for album_name in set(album_sequence):
    assert [s.props.track_number for s in queue if s.props.album == album_name] == [1, 2, 3, 4]
prefix = queue._shuffle_values[:3]
queue.shuffle(2)
assert queue._shuffle_values[:3] == prefix, "Preserve played history"
queue.deshuffle()
assert [s.props.track_number for s in queue] == [1, 2, 3, 4] * 3
assert queue.get_item(12) is None, "Gio.ListModel end-of-model contract"
existing = Gio.ListStore.new(CoreSong)
existing.append(song)
assert ShuffleListModel(existing).get_item(0) is song

# Exercise real Queue sequencing, including selecting a middle album track.
engine = Queue(context)
for item in queue:
    item.props.validation = CoreSong.Validation.SUCCEEDED
song.props.validation = CoreSong.Validation.SUCCEEDED
engine.props.repeat_mode = RepeatMode.SHUFFLE_ALBUMS
assert engine.set_song(song) == song
assert engine.props.current_song == song
assert engine.next()
assert engine.props.current_song.props.track_number == 3
assert engine.props.current_song.props.album == song.props.album
assert engine.previous()
assert engine.props.current_song == song
engine.props.repeat_mode = RepeatMode.SHUFFLE
assert all(item.props.artist == "Aster" for item in queue)
context.props.player.play(song)

# A long queue verifies real scrolling rather than only scroll_to calls.
for index in range(80):
    item = CoreSong(context, {
        "id": f"follow-{index}", "title": f"Queue track {index + 13}",
        "artist": "Aster", "album": "Morning Light", "duration": 210,
        "trackNumber": index + 13, "albumDiscNumber": 1})
    item._thumbnail = "generic"
    item.props.validation = CoreSong.Validation.SUCCEEDED
    context.props.coremodel._queue_model.append(item)

real_player = Player(context)
transport = PlayerToolbar()
transport.props.player = real_player
real_player.props.duration = 210.
real_player.props.state = Playback.PAUSED
real_player.props.volume = 0.125
assert not hasattr(transport, "_cover_image"), "No cover in bottom bar"
volume = transport._volume_button
volume._set_adjustment()
assert abs(volume._adjustment.get_value() - 0.5) < 0.0001
volume._adjustment.set_value(0.8)
assert abs(real_player.props.volume - 0.512) < 0.0001, "Live cubic volume binding"
volume._adjustment.set_value(0.5)
assert volume._on_scroll(None, 0., 1.)
assert abs(volume._adjustment.get_value() - 0.49) < 0.0001
progress = transport._progress_scale
scroll = next(controller for controller in progress.observe_controllers()
              if isinstance(controller, Gtk.EventControllerScroll)
              and controller.get_propagation_phase() == Gtk.PropagationPhase.CAPTURE)
position = progress.get_value()
assert scroll.emit("scroll", 0., 1.)
assert progress.get_value() == position
assert not hasattr(panel, "_favorite"), "No track-info star"
assert panel._details.get_first_child() is panel._title, "No track-info heading"

# A disc starts empty and receives its indexed tracks asynchronously.
# Its duration must reach the album even when the model initially has no items.
duration_songs = Gio.ListStore.new(CoreSong)
for index, seconds in enumerate((90, 210)):
    duration_songs.append(CoreSong(context, {
        "id": f"duration-{index}", "title": "Duration fixture", "artist": "Aster",
        "trackNumber": index + 1, "duration": seconds}))
context.props.coremodel._songs_model_proxy.append(duration_songs)
context.props.coregrilo.get_album_discs = lambda album, store: store.append(CoreDisc(context, album, 1))
def load_duration_disc(disc, model):
    def populate():
        model.set_filter(Gtk.CustomFilter.new(lambda song: song.props.id.startswith("duration-")))
        return GLib.SOURCE_REMOVE
    GLib.idle_add(populate)
context.props.coregrilo.get_album_disc = load_duration_disc
duration_album = CoreAlbum(context, {"id": "duration-album", "title": "Duration Album",
                                    "artist": "Aster", "publicationDate": "2026"})
duration_album._thumbnail = "generic"
duration_widget = AlbumWidget(context)
duration_widget.props.corealbum = duration_album
assert duration_widget._released_label.get_label() == "2026", "No invented minute while loading"
preferences = PreferencesDialog(context)
assert not preferences._rounded_artwork_row.props.active
art = panel._paintable
invalidations = []
art.connect("invalidate-contents", lambda *args: invalidations.append(True))
preferences._rounded_artwork_row.props.active = True
assert settings.get_boolean("rounded-artwork") and art._radius() > 0
assert invalidations, "Artwork changes immediately with Preferences"
preferences._rounded_artwork_row.props.active = False
assert art._radius() == 0

provider = Gtk.CssProvider()
provider.load_from_resource("/org/gnome/Music/style.css")
Gtk.StyleContext.add_provider_for_display(
    window.get_display(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
queue[0].props.state = SongWidget.State.UNPLAYED
toolbar = Adw.ToolbarView()
toolbar.add_css_class("music-workspace-toolbar")
header = Adw.HeaderBar()
header.add_css_class("music-header")
header.set_title_widget(Adw.WindowTitle(title="Music", subtitle="Album artists"))
toolbar.add_top_bar(header)
toolbar.set_content(view)
toolbar.add_bottom_bar(transport)
window.set_content(toolbar)
window.present()
window_paintable = Gtk.WidgetPaintable.new(window)
loop = GLib.MainLoop()

def capture(name):
    snapshot = Gtk.Snapshot.new()
    window_paintable.snapshot(snapshot, window.get_width(), window.get_height())
    node = snapshot.to_node()
    texture = window.get_renderer().render_texture(node, None)
    texture.save_to_png(str(SOURCE / f"builddir/{name}.png"))
    return texture

def narrow():
    try:
        assert view._artist_album._listbox.get_row_at_index(0).get_child()._workspace_root.get_orientation() == Gtk.Orientation.HORIZONTAL
        assert panel._cover.get_width() >= panel.get_width() - 2, (
            f"Artwork fills panel: cover={panel._cover.get_width()}, panel={panel.get_width()}, "
            f"details={panel._details.get_width()}, button={panel._artwork.get_width()}")
        assert abs(panel._cover.get_height() - panel._cover.get_width()) <= 1
        row = album_widget._disc_list_box.get_row_at_index(0)._list_box.get_row_at_index(0)
        assert row.get_height() <= 34, f"Compact desktop rows: {row.get_height()}"
        assert panel._list.get_parent().get_vadjustment().get_value() > 0, "Follow playing track"
        assert volume._scale.get_mapped(), "Volume slider always visible"
        albums = view._artist_album._listbox
        short = albums.get_row_at_index(0).get_child()
        long = albums.get_row_at_index(1).get_child()
        assert short._workspace_info.get_width() == long._workspace_info.get_width(), (short._workspace_info.get_width(), long._workspace_info.get_width())
        assert short._workspace_info.get_width() == 180
        for label in (long._title_label, long._artist_label, long._composer_label):
            assert not label.get_layout().is_ellipsized()
            assert label.get_layout().get_line_count() > 1
        assert short._cover_image.get_halign() == Gtk.Align.START
        _, cover_origin = panel._cover.compute_point(panel, Graphene.Point().init(0, 0))
        assert abs(cover_origin.y + panel._cover.get_height() - panel.get_height()) <= 1
        assert not long._title_label.get_layout().is_ellipsized()
        assert long._title_label.get_layout().get_line_count() > 1
        assert not long._play_button.get_parent().get_visible()
        assert panel._artwork.get_parent() is not panel._details
        assert duration_album.props.duration == 300
        assert duration_widget._released_label.get_label() == "2026, 5 minutes"
        track = short._disc_list_box.get_row_at_index(0)._list_box.get_row_at_index(0)
        assert not track._menu_button.get_visible()
        capture("workspace-wide")
        track._on_context_menu(None, 1, 40, 12)
        assert track.props.menu.get_visible(), "Right click opens the existing track menu"
        track.props.menu.popdown()
        navigation = ListNavigation()
        assert navigation.handle(view._sidebar, "h")
        assert view._selection_model.get_selected() == 2
        assert navigation.handle(view._sidebar, "h")
        assert view._selection_model.get_selected() == 1
        albums = view._artist_album._listbox
        short = albums.get_row_at_index(0).get_child()
        assert navigation.handle(short, "a")
        assert window.get_focus() == albums.get_row_at_index(1)
        track_rows = short._disc_list_box.get_row_at_index(0)._list_box
        assert navigation.handle(track_rows.get_row_at_index(0), "t")
        assert window.get_focus() == track_rows.get_row_at_index(1)
        assert navigation.handle(track_rows.get_row_at_index(3), "t")
        next_album = albums.get_row_at_index(1).get_child()
        assert window.get_focus() == next_album._disc_list_box.get_row_at_index(0)._list_box.get_row_at_index(0)
        sidebar = view._split_view.get_sidebar()
        before = sidebar.get_width()
        edge = sidebar.get_last_child()
        controllers = edge.observe_controllers()
        drag = next(controller for controller in controllers
                    if isinstance(controller, Gtk.GestureDrag))
        drag.emit("drag-begin", 0., 0.)
        drag.emit("drag-update", 50., 0.)
        assert view._split_view.get_sidebar_width_fraction() > before / view._split_view.get_width()
        saved = view._split_view.get_sidebar_width_fraction()
        assert abs(settings.get_double("artist-sidebar-fraction") - saved) < 0.0001
        view._playback_split.set_sidebar_width_fraction(0.3)
        panel._info_split.set_position(220)
        fresh_settings = Gio.Settings.new("org.gnome.Music")
        assert abs(fresh_settings.get_double("artist-sidebar-fraction") - saved) < 0.0001
        assert fresh_settings.get_double("playback-sidebar-fraction") == 0.3
        assert fresh_settings.get_int("queue-info-position") == 220
        restored_window = Adw.ApplicationWindow(application=gtk_app)
        restored_context = SimpleNamespace(props=SimpleNamespace(**vars(context.props)))
        restored_context.props.window = restored_window
        restored_context.props.settings = fresh_settings
        restored = ArtistsView(restored_context)
        assert abs(restored._split_view.get_sidebar_width_fraction() - saved) < 0.0001
        assert restored._playback_split.get_sidebar_width_fraction() == 0.3
        restored_panel = restored._playback_split.get_sidebar().get_child()
        assert restored_panel._info_split.get_position() == 220
        restored_window.set_content(restored)
        restored_window.destroy()
        window.unset_state_flags(Gtk.StateFlags.BACKDROP)
        GLib.timeout_add(400, focused_capture)
    except Exception:
        exception_hook(*sys.exc_info())
        loop.quit()
    return GLib.SOURCE_REMOVE

def focused_capture():
    try:
        capture("workspace-focused")
        window.set_state_flags(Gtk.StateFlags.BACKDROP, False)
        GLib.timeout_add(500, backdrop_check)
    except Exception:
        exception_hook(*sys.exc_info())
        loop.quit()
    return GLib.SOURCE_REMOVE


def backdrop_check():
    try:
        capture("workspace-inactive")
        focused = GdkPixbuf.Pixbuf.new_from_file(str(SOURCE / "builddir/workspace-focused.png"))
        inactive = GdkPixbuf.Pixbuf.new_from_file(str(SOURCE / "builddir/workspace-inactive.png"))
        # Exclude the user's custom window-control styling; compare application
        # chrome, including title text and both slider handles and troughs.
        for x, y, width, height in ((1, 1, window.get_width() - 101, header.get_height() - 1),
                                     (1, window.get_height() - transport.get_height(),
                                      window.get_width() - 2, transport.get_height() - 1)):
            before = focused.new_subpixbuf(x, y, width, height)
            after = inactive.new_subpixbuf(x, y, width, height)
            channels = before.get_n_channels()
            data_before, data_after = before.get_pixels(), after.get_pixels()
            for row in range(height):
                start_before = row * before.get_rowstride()
                start_after = row * after.get_rowstride()
                assert data_before[start_before:start_before + width * channels] == data_after[start_after:start_after + width * channels], f"Unchanged focus colors at bar row {y + row}"
        window.unset_state_flags(Gtk.StateFlags.BACKDROP)
        transport.props.compact = True
        window.set_default_size(560, 800)
        GLib.timeout_add(500, narrow_check)
    except Exception:
        exception_hook(*sys.exc_info())
        loop.quit()
    return GLib.SOURCE_REMOVE


def narrow_check():
    try:
        assert view._split_view.get_collapsed()
        assert view._playback_split.get_collapsed()
        assert view._artists_button.get_visible()
        assert volume.get_parent() is transport._controls_box
        capture("workspace-narrow")
        panel._show_artwork(None)
        panel._art_dialog.close()
        context.props.player.props.current_song = None
        context.props.player.emit("song-changed")
        assert not panel._details.get_visible()
        print("PASS: browsing, artist restoration, queue scope, playback independence,")
        print("row recycling, live model notifications, album shuffle, history,")
        print("real Queue next/previous, column resizing, wide/narrow layouts,")
        print("artwork dialog and empty playback state.")
        print("Desktop: strict album-artist queries, oldest cover, click selection,")
        print("compact rows, queue following, full-width cover, inline volume,")
        print("long-title alignment, repeated-letter navigation and scroll controls.")
        print("Album duration loading, right-click track menus and live artwork preference.")
        print("Identical focused/inactive header and transport rendering.")
    except Exception:
        exception_hook(*sys.exc_info())
    loop.quit()
    return GLib.SOURCE_REMOVE

def follow_last():
    context.props.player.play(queue.get_item(queue.get_n_items() - 1))
    GLib.timeout_add(600, narrow)
    return GLib.SOURCE_REMOVE

GLib.timeout_add(400, follow_last)
loop.run()
window.destroy()
sys.exit(bool(errors))
