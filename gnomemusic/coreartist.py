# Copyright 2025 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
from typing import Any, Dict
import typing

from gettext import gettext as _
from gi.repository import Gtk, GObject

from gnomemusic.corealbum import CoreAlbum
import gnomemusic.utils as utils
if typing.TYPE_CHECKING:
    from gnomemusic.application import Application


class CoreArtist(GObject.GObject):
    """Artist information object

    Contains all relevant information about an artist.
    """

    album_count = GObject.Property(type=int, default=0)
    artist = GObject.Property(type=str)
    id = GObject.Property(type=str)

    def __init__(
            self, application: Application,
            cursor_dict: Dict[str, Any]) -> None:
        """Initiate the CoreArtist object

        :param Application application: The application object
        :param Dict[str, Any] cursor_dict: Dict with Tsparql keys
        """
        super().__init__()

        self._application = application
        self._coregrilo = application.props.coregrilo
        self._coremodel = application.props.coremodel
        self._model = None
        self._thumbnail = None
        self._cover_album = None
        self._cover_album_id = 0
        self._cover_model_id = 0

        self.update(cursor_dict)

    def update(self, cursor_dict: Dict[str, Any]) -> None:
        self.props.album_count = utils.get_int_from_cursor_dict(cursor_dict, "albumCount")
        self.props.id = cursor_dict.get("id")
        self.props.artist = (cursor_dict.get("albumArtist")
                             or cursor_dict.get("artist")
                             or _("Unknown Album Artist"))

    def _get_artist_album_model(self):
        albums_model_filter = Gtk.FilterListModel.new(
            self._coremodel.props.albums)
        albums_model_filter.set_filter(Gtk.AnyFilter())

        def oldest_first(a, b, *args):
            def key(album):
                year = album.props.year
                return (not bool(year), year or "", album.props.title.casefold(),
                        album.props.id)
            return (key(a) > key(b)) - (key(a) < key(b))

        albums_sorter = Gtk.CustomSorter.new(oldest_first)
        albums_model_sort = Gtk.SortListModel.new(
            albums_model_filter, albums_sorter)

        self._coregrilo.get_artist_albums(self, albums_model_filter)

        return albums_model_sort

    @GObject.Property(type=Gtk.SortListModel, default=None)
    def model(self):
        if self._model is None:
            self._model = self._get_artist_album_model()

        return self._model

    @GObject.Property(type=str, default=None)
    def thumbnail(self):
        """Artist art thumbnail retrieval

        :return: The artist art uri or "generic"
        :rtype: string
        """
        if self._thumbnail is None:
            self._thumbnail = "generic"
            model = self.props.model
            self._cover_model_id = model.connect("items-changed", self._update_cover)
            self._update_cover()

        return self._thumbnail

    @thumbnail.setter  # type: ignore
    def thumbnail(self, value):
        """Artist art thumbnail setter

        :param string value: uri or "generic"
        """
        self._thumbnail = value

    def _update_cover(self, *args):
        model = self.props.model
        oldest = model.get_item(0) if model.get_n_items() else None
        if oldest is not self._cover_album:
            if self._cover_album is not None and self._cover_album_id:
                self._cover_album.disconnect(self._cover_album_id)
            self._cover_album = oldest
            self._cover_album_id = 0
            if oldest is not None:
                self._cover_album_id = oldest.connect("notify::thumbnail", self._update_cover)
        self.props.thumbnail = oldest.props.thumbnail if oldest else "generic"
