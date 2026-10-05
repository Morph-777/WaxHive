# Copyright 2026 The GNOME Music developers
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from gettext import gettext as _

from gi.repository import Adw, Gio, GLib, GObject, Gtk, Pango

from gnomemusic.coverpaintable import CoverPaintable
from gnomemusic.utils import ArtSize, DefaultIconType, seconds_to_string
from gnomemusic.widgets.songwidget import SongWidget


class FullWidthCover(Gtk.Picture):
    """Request a square at the allocated width instead of shrinking sideways."""

    def do_get_request_mode(self):
        return Gtk.SizeRequestMode.HEIGHT_FOR_WIDTH

    def do_measure(self, orientation, for_size):
        if orientation == Gtk.Orientation.HORIZONTAL:
            return 0, 256, -1, -1
        side = max(1, for_size) if for_size >= 0 else 256
        return side, side, -1, -1


class QueueRow(Gtk.Box):
    """A recycled queue row; all song connections belong to one binding."""

    def __init__(self):
        super().__init__(spacing=4)
        self.add_css_class("queue-row")
        self._song = None
        self._bindings = []
        self._state_id = 0
        self._indicator = Gtk.Image(
            icon_name="media-playback-start-symbolic", width_request=12, pixel_size=12)
        self._number = Gtk.Label(xalign=0)
        self._number.set_margin_end(8)
        labels = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self._title = Gtk.Label(xalign=0, ellipsize=3)
        self._artist = Gtk.Label(xalign=0, ellipsize=3)
        self._artist.add_css_class("dim-label")
        self._artist.add_css_class("caption")
        labels.append(self._title)
        labels.append(self._artist)
        self._duration = Gtk.Label()
        self._duration.add_css_class("dim-label")
        for child in (self._indicator, self._number, labels, self._duration):
            self.append(child)

    def bind(self, song, position):
        self.unbind()
        self._song = song
        self._number.set_label(str(position + 1))
        self._duration.set_label(seconds_to_string(song.props.duration))
        for prop, label in (("title", self._title), ("artist", self._artist)):
            self._bindings.append(song.bind_property(
                prop, label, "label", GObject.BindingFlags.SYNC_CREATE))
        self._state_id = song.connect("notify::state", self._update_state)
        self._update_state()

    def unbind(self):
        if self._song is not None and self._state_id:
            self._song.disconnect(self._state_id)
        for binding in self._bindings:
            binding.unbind()
        self._bindings = []
        self._state_id = 0
        self._song = None

    def _update_state(self, *args):
        playing = self._song.props.state == SongWidget.State.PLAYING
        self._indicator.set_opacity(1 if playing else 0)
        if playing:
            self.add_css_class("playing")
        else:
            self.remove_css_class("playing")


class NowPlayingPanel(Gtk.Box):
    """Playback queue and information, independent of library selection."""

    __gtype_name__ = "NowPlayingPanel"

    def __init__(self, application):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._player = application.props.player
        self._model = application.props.coremodel.props.queue
        self._follow_idle_id = 0
        self._art_dialog = None
        self.add_css_class("now-playing-panel")

        heading = Gtk.Label(label=_("Playing Tracks"), xalign=0)
        heading.add_css_class("heading")
        heading.set_margin_start(18)
        heading.set_margin_top(18)
        heading.set_margin_bottom(12)
        self.append(heading)

        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._setup_row)
        factory.connect("bind", self._bind_row)
        factory.connect("unbind", self._unbind_row)
        self._selection = Gtk.SingleSelection(
            model=self._model, autoselect=False, can_unselect=True)
        self._list = Gtk.ListView(model=self._selection, factory=factory)
        self._list.connect("activate", self._activate)
        self._list.connect("map", self._schedule_follow)
        scroller = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER, vexpand=True,
            min_content_height=120)
        scroller.set_child(self._list)
        self._queue_stack = Gtk.Stack(vexpand=True)
        self._queue_stack.add_named(scroller, "queue")
        empty = Adw.StatusPage(
            title=_("Nothing Playing"),
            description=_("Play a track to start an artist’s queue."),
            icon_name="music-note-outline-symbolic")
        empty.add_css_class("compact")
        self._queue_stack.add_named(empty, "empty")

        details = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=8,
            margin_top=12, margin_bottom=0)
        self._title = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END, selectable=True)
        self._title.add_css_class("heading")
        self._artist = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END, selectable=True)
        self._album = Gtk.Label(xalign=0, ellipsize=Pango.EllipsizeMode.END, selectable=True)
        self._album.add_css_class("dim-label")
        self._duration = Gtk.Label(xalign=0)
        self._duration.add_css_class("dim-label")
        self._cover = FullWidthCover(can_shrink=True, content_fit=Gtk.ContentFit.CONTAIN)
        self._paintable = CoverPaintable(
            self._cover, ArtSize.LARGE, DefaultIconType.ALBUM)
        self._cover.set_paintable(self._paintable)
        artwork = Gtk.Button(child=self._cover, tooltip_text=_("View Artwork"))
        artwork.set_vexpand(False)
        artwork.set_valign(Gtk.Align.END)
        artwork.add_css_class("flat")
        artwork.add_css_class("now-playing-artwork")
        artwork.connect("clicked", self._show_artwork)
        self._artwork = artwork
        for child in (self._title, self._artist, self._album, self._duration):
            if child is not self._duration:
                child.set_max_width_chars(1)
            child.set_margin_start(18)
            child.set_margin_end(18)
            details.append(child)

        self._details = details
        # A native GTK splitter keeps the queue and artwork independently sized.
        split = Gtk.Paned(orientation=Gtk.Orientation.VERTICAL, vexpand=True)
        split.set_start_child(self._queue_stack)
        application.props.settings.bind(
            "queue-info-position", split, "position",
            Gio.SettingsBindFlags.DEFAULT)
        details_scroll = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER, min_content_height=80,
            propagate_natural_height=True, vexpand=True)
        details_scroll.set_child(details)
        information = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        information.append(details_scroll)
        information.append(artwork)
        self._information = information
        self._info_split = split
        split.set_end_child(information)
        split.set_resize_start_child(True)
        split.set_resize_end_child(False)
        split.set_shrink_start_child(False)
        split.set_shrink_end_child(False)
        self.append(split)
        self._model.connect("items-changed", self._queue_changed)
        self._player.connect("song-changed", self._song_changed)
        self._queue_changed()
        self._song_changed()

    def _setup_row(self, factory, item):
        item.set_child(QueueRow())

    def _bind_row(self, factory, item):
        item.get_child().bind(item.get_item(), item.get_position())

    def _unbind_row(self, factory, item):
        item.get_child().unbind()

    def _activate(self, view, position):
        song = self._model.get_item(position)
        if song is not None:
            self._player.play(song)

    def _queue_changed(self, *args):
        self._queue_stack.set_visible_child_name(
            "queue" if self._model.get_n_items() else "empty")
        self._schedule_follow()

    def _song_changed(self, *args):
        song = self._player.props.current_song
        self._information.set_visible(song is not None)
        self._details.set_visible(song is not None)
        self._artwork.set_visible(song is not None)
        self._paintable.props.coreobject = song
        if song is None:
            return
        self._title.set_tooltip_text(song.props.title)
        self._artist.set_tooltip_text(song.props.artist)
        self._album.set_tooltip_text(song.props.album)
        self._title.set_label(song.props.title)
        self._artist.set_label(song.props.artist)
        self._album.set_label(song.props.album)
        self._duration.set_label(seconds_to_string(song.props.duration))
        self._schedule_follow()

    def _schedule_follow(self, *args):
        if not self._follow_idle_id:
            self._follow_idle_id = GLib.idle_add(self._follow_current_song)

    def _follow_current_song(self):
        self._follow_idle_id = 0
        song = self._player.props.current_song
        if song is not None and self._list.get_mapped():
            for position, item in enumerate(self._model):
                if item == song:
                    self._list.scroll_to(position, Gtk.ListScrollFlags.NONE, None)
                    break
        return GLib.SOURCE_REMOVE

    def _show_artwork(self, button):
        song = self._player.props.current_song
        if song is None:
            return
        self._art_dialog = Adw.Dialog(
            title=song.props.album, content_width=600, content_height=640)
        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        picture = Gtk.Picture(can_shrink=True)
        # Own paintable: changing tracks does not change an open artwork viewer.
        paintable = CoverPaintable(picture, ArtSize.LARGE, DefaultIconType.ALBUM)
        paintable.props.coreobject = song
        picture.set_paintable(paintable)
        picture.set_margin_start(24)
        picture.set_margin_end(24)
        picture.set_margin_top(24)
        picture.set_margin_bottom(24)
        toolbar.set_content(picture)
        self._art_dialog.set_child(toolbar)
        self._art_dialog.present(self)
