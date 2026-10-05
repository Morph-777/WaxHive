# Copyright 2025 The GNOME Music developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from __future__ import annotations
from random import sample
import typing

from gi.repository import Gio, GObject

from gnomemusic.musiclogger import MusicLogger

if typing.TYPE_CHECKING:
    from gnomemusic.coresong import CoreSong


class ShuffleListModel(GObject.GObject, Gio.ListModel):
    """Shuffles the underlying list model

    This works by keeping a local shuffle list and shuffling the
    values as needed.

    This is meant for the Queue and as such a position in the
    playlist is required for the shuffling. The model shuffles the
    items after the given position. When deshuffling it will only
    deshuffle the items that are still left in the queue.
    """

    __gtype_name__ = "ShuffleListModel"

    shuffled = GObject.Property(type=bool, default=False)

    def __init__(self, model: Gio.ListModel) -> None:
        """Initialize the list model

        :param Gio.ListModel model: Model to shuffle
        """
        super().__init__()

        self._log = MusicLogger()

        self._model = model
        self._model.connect("items-changed", self._on_items_changed)

        self._shuffle_values: list[int] = list(range(model.get_n_items()))

    def _on_items_changed(
            self, model: Gio.ListModel, position: int, removed: int,
            added: int) -> None:
        # FIXME: Deal with item changes during play
        old_count = len(self._shuffle_values)
        n_items = model.get_n_items()
        self._shuffle_values = list(range(0, n_items))
        self.items_changed(0, old_count, n_items)

    def do_get_item(self, position: int) -> CoreSong:
        if position >= len(self._shuffle_values):
            return None
        return self._model.get_item(self._shuffle_values[position])

    def do_get_n_items(self):
        return self._model.get_n_items()

    def get_song_position(self, song):
        for position, item in enumerate(self):
            if item == song:
                return position
        return 0

    def do_get_item_type(self):
        return self._model.get_item_type()

    def shuffle(
            self, position: int, initial_song_position: int | None = None,
            albums: bool = False) -> None:
        """Shuffle upcoming tracks or albums, preserving playback history."""
        self.props.shuffled = True
        if self._model.get_n_items() == 0:
            return

        if initial_song_position is not None:
            prefix = [initial_song_position]
            remaining = [i for i in range(self._model.get_n_items())
                         if i != initial_song_position]
        else:
            prefix = self._shuffle_values[:position + 1]
            remaining = self._shuffle_values[position + 1:]

        if albums:
            def album_key(index):
                song = self._model.get_item(index)
                return song.props.album_urn or (song.props.album, song.props.artist)

            def track_key(index):
                song = self._model.get_item(index)
                return (song.props.album_disc_number, song.props.track_number, index)

            current_album = album_key(prefix[-1])
            groups = {}
            for index in remaining:
                groups.setdefault(album_key(index), []).append(index)
            current_tail = sorted(groups.pop(current_album, []), key=track_key)
            if initial_song_position is not None:
                # Earlier tracks in the selected album remain playback history.
                earlier = [i for i in current_tail
                           if track_key(i) < track_key(initial_song_position)]
                prefix = earlier + prefix
                current_tail = [i for i in current_tail if i not in earlier]
            keys = sample(list(groups), len(groups))
            remaining = current_tail + [i for key in keys
                                        for i in sorted(groups[key], key=track_key)]
        else:
            remaining = sample(remaining, len(remaining))
        self._shuffle_values = prefix + remaining
        self.items_changed(0, len(self._shuffle_values), len(self._shuffle_values))

    def deshuffle(self, position: int | None = None) -> None:
        """Deshuffle the model

        :param int position: Deshuffle the remaining items from this
            position on
        """
        self.props.shuffled = False

        if position is not None:
            list_before = list(self._shuffle_values[:position])
            list_position = list(self._shuffle_values[position:position + 1])
            list_after = sorted(self._shuffle_values[position + 1:])
            self._shuffle_values = list_before + list_position + list_after
        else:
            self._shuffle_values = sorted(self._shuffle_values)

        self._log.debug(f"Deshuffled order: {self._shuffle_values}")
        self.items_changed(0, len(self._shuffle_values), len(self._shuffle_values))
