# Copyright (c) 2016 The GNOME Music Developers
#
# GNOME Music is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# GNOME Music is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with GNOME Music; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
#
# The GNOME Music authors hereby grant permission for non-GPL compatible
# GStreamer plugins to be used and distributed together with GStreamer
# and GNOME Music.  This permission is above and beyond the permissions
# granted by the GPL license by which GNOME Music is covered.  If you
# modify this code, you may extend this exception to your version of the
# code, but you are not obligated to do so.  If you do not wish to do so,
# delete this exception statement from your version.

from __future__ import annotations
import typing

from gettext import gettext as _
from gi.repository import Adw, Gio, GObject, Gtk

from gnomemusic.widgets.artistalbumswidget import ArtistAlbumsWidget
from gnomemusic.widgets.artisttile import ArtistTile
from gnomemusic.widgets.nowplayingpanel import NowPlayingPanel
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application


@Gtk.Template(resource_path="/org/gnome/Music/ui/ArtistsView.ui")
class ArtistsView(Adw.Bin):
    """Main view of all available artists

    Consists of a list of artists on the left side and an overview of
    all albums by this artist on the right side.
    """

    __gtype_name__ = "ArtistsView"

    icon_name = GObject.Property(
        type=str, default="music-artist-symbolic",
        flags=GObject.ParamFlags.READABLE)
    title = GObject.Property(
        type=str, default=_("Music"), flags=GObject.ParamFlags.READABLE)

    _artist_view = Gtk.Template.Child()
    _sidebar = Gtk.Template.Child()
    _split_view = Gtk.Template.Child()
    _playback_split = Gtk.Template.Child()
    _artists_button = Gtk.Template.Child()
    _artist_heading = Gtk.Template.Child()

    def __init__(self, application: Application) -> None:
        """Initialize

        :param GtkApplication application: The application object
        """
        super().__init__()

        self.props.name = "artists"
        self._window = application.props.window
        self._settings = application.props.settings
        self._pending_artist = self._settings.get_string("selected-album-artist")
        self._artist_album = ArtistAlbumsWidget(application)
        self._artist_view.props.child = self._artist_album
        self._playback_split.set_sidebar(NowPlayingPanel(application))
        self._add_resize_edge(self._split_view, Gtk.Align.END, 1)
        self._add_resize_edge(self._playback_split, Gtk.Align.START, -1)
        for key, split in (("artist-sidebar-fraction", self._split_view),
                           ("playback-sidebar-fraction", self._playback_split)):
            self._settings.bind(key, split, "sidebar-width-fraction",
                                Gio.SettingsBindFlags.DEFAULT)
        self._split_view.bind_property(
            "collapsed", self._artists_button, "visible",
            GObject.BindingFlags.SYNC_CREATE)
        for width, split in ((1100, self._playback_split), (700, self._split_view)):
            breakpoint = Adw.Breakpoint.new(
                Adw.BreakpointCondition.parse(f"max-width: {width}px"))
            breakpoint.add_setter(split, "collapsed", True)
            breakpoint.add_setter(split, "show-sidebar", False)
            if width == 700:
                breakpoint.add_setter(self._artist_album, "narrow", True)
                # The window uses only its most specific matching breakpoint.
                if hasattr(self._window, "headerbar"):
                    breakpoint.add_setter(self._window.props.headerbar, "compact", True)
                    breakpoint.add_setter(
                        self._window._player_toolbar, "compact", True)
                breakpoint.add_setter(self._playback_split, "collapsed", True)
                breakpoint.add_setter(self._playback_split, "show-sidebar", False)
            self._window.add_breakpoint(breakpoint)

        # This indicates if the current list has been empty and has
        # had no user interaction since.
        self._untouched_list = True

        self._coremodel = application.props.coremodel
        self._model = self._coremodel.props.artists_sort

        self._selection_model = Gtk.SingleSelection.new(self._model)
        self._sidebar.props.model = self._selection_model
        artist_item_factory = Gtk.SignalListItemFactory()
        artist_item_factory.connect("setup", self._on_list_view_setup)
        artist_item_factory.connect("bind", self._on_list_view_bind)
        self._sidebar.props.factory = artist_item_factory

        self._selection_model.connect_after(
            "items-changed", self._on_model_items_changed)
        self._selection_model.connect("notify::selected-item", self._selection_changed)
        self._on_model_items_changed(self._selection_model, 0, 0, 0)

    def _on_list_view_setup(
            self, factory: Gtk.SignalListItemFactory,
            list_item: Gtk.ListItem) -> None:
        list_item.props.child = ArtistTile()

    def _on_list_view_bind(
            self, factory: Gtk.SignalListItemFactory,
            list_item: Gtk.ListItem) -> None:
        coreartist = list_item.props.item
        artist_tile = list_item.props.child
        artist_tile.props.coreartist = coreartist

    def _on_model_items_changed(
            self, model: Gtk.SingleSelection, position: int, removed: int,
            added: int) -> None:
        if model.get_n_items() == 0:
            self._untouched_list = True
            self._artist_album.props.coreartist = None
        elif self._pending_artist:
            for index, artist in enumerate(model):
                if artist.props.artist == self._pending_artist:
                    self._selection_model.set_selected(index)
                    self._pending_artist = ""
                    self._untouched_list = False
                    self._selection_changed()
                    break
            if self._untouched_list:
                self._untouched_list = False
                self._selection_changed()
        elif self._untouched_list is True:
            self._untouched_list = False
            self._selection_model.set_selected(0)
            self._selection_changed()

    @Gtk.Template.Callback()
    def _on_artist_activated(
            self, sidebar: Gtk.ListView, position: int) -> None:
        """Initializes new artist album widgets"""
        self._pending_artist = ""
        self._selection_model.set_selected(position)
        self._selection_changed()
        self._split_view.set_show_sidebar(not self._split_view.get_collapsed())

    def _selection_changed(self, *args):
        coreartist = self._selection_model.get_selected_item()
        self._artist_album.props.coreartist = coreartist
        if coreartist is None:
            return
        self._artist_heading.set_label(coreartist.props.artist)
        self._artist_view.get_vadjustment().set_value(0)
        if not self._pending_artist:
            self._settings.set_string("selected-album-artist", coreartist.props.artist)

    @Gtk.Template.Callback()
    def _show_artists(self, button):
        self._split_view.set_show_sidebar(True)

    def _add_resize_edge(self, split, align, direction):
        """A small GTK drag target beside the sidebar's scrollable content."""
        child = split.get_sidebar()
        split.set_sidebar(None)
        overlay = Gtk.Overlay()
        if align == Gtk.Align.END:
            child.set_margin_end(6)
            split.set_max_sidebar_width(420)
        else:
            child.set_margin_start(6)
            split.set_max_sidebar_width(520)
        overlay.set_child(child)
        edge = Gtk.Box(width_request=6, halign=align, vexpand=True)
        edge.set_cursor_from_name("col-resize")
        overlay.add_overlay(edge)
        split.set_sidebar(overlay)
        drag = Gtk.GestureDrag()
        initial_width = [0]
        initial_pointer = [None]

        def begin(gesture, x, y):
            initial_width[0] = overlay.get_width()
            event = gesture.get_last_event(gesture.get_current_sequence())
            initial_pointer[0] = event.get_position()[1] if event else None

        def update(gesture, dx, dy):
            if split.get_collapsed():
                return
            event = gesture.get_last_event(gesture.get_current_sequence())
            if event and initial_pointer[0] is not None:
                dx = event.get_position()[1] - initial_pointer[0]
            width = max(split.get_min_sidebar_width(), min(
                split.get_max_sidebar_width(), initial_width[0] + direction * dx))
            split.set_sidebar_width_fraction(width / max(1, split.get_width()))

        drag.connect("drag-begin", begin)
        drag.connect("drag-update", update)
        edge.add_controller(drag)
