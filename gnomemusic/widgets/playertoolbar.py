# Copyright © 2025 The GNOME Music Developers
#
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from gettext import gettext as _
from gi.repository import GObject, Gtk

from gnomemusic.gstplayer import Playback
from gnomemusic.player import Player
from gnomemusic.widgets.repeatmodebutton import RepeatModeButton  # noqa: F401
from gnomemusic.widgets.smoothscale import SmoothScale  # noqa: F401
from gnomemusic.widgets.twolinetip import TwoLineTip
from gnomemusic.widgets.volumebutton import VolumeButton  # noqa: F401
import gnomemusic.utils as utils


@Gtk.Template(resource_path='/org/gnome/Music/ui/PlayerToolbar.ui')
class PlayerToolbar(Gtk.ActionBar):
    """Main Player widget object

    Contains the ui of playing a song with Music.
    """

    __gtype_name__ = 'PlayerToolbar'

    _artist_label = Gtk.Template.Child()
    _duration_label = Gtk.Template.Child()
    _next_button = Gtk.Template.Child()
    _play_button = Gtk.Template.Child()
    _play_pause_image = Gtk.Template.Child()
    _prev_button = Gtk.Template.Child()
    _progress_scale = Gtk.Template.Child()
    _progress_time_label = Gtk.Template.Child()
    _repeat_mode_button = Gtk.Template.Child()
    _song_info_box = Gtk.Template.Child()
    _title_label = Gtk.Template.Child()
    _volume_button = Gtk.Template.Child()
    _transport_box = Gtk.Template.Child()
    _controls_box = Gtk.Template.Child()

    def __init__(self):
        super().__init__()

        self._player = None

        self._tooltip = TwoLineTip()

    @GObject.Property(type=bool, default=False)
    def compact(self):
        return self._transport_box.get_orientation() == Gtk.Orientation.VERTICAL

    @compact.setter
    def compact(self, value):
        self._transport_box.set_orientation(
            Gtk.Orientation.VERTICAL if value else Gtk.Orientation.HORIZONTAL)
        self._transport_box.set_spacing(4 if value else 18)
        self._controls_box.set_halign(Gtk.Align.CENTER if value else Gtk.Align.START)
        parent = self._volume_button.get_parent()
        target = self._controls_box if value else self._progress_scale.get_parent()
        if parent is not target:
            parent.remove(self._volume_button)
            if value:
                target.append(self._volume_button)
            else:
                target.insert_child_after(self._volume_button, self._progress_scale)
        self._volume_button._scale.set_size_request(70 if value else 140, -1)
        self._artist_label.set_visible(not value)

    # FIXME: This is a workaround for not being able to pass the player
    # object via init when using Gtk.Builder.
    @GObject.Property(type=Player, default=None)
    def player(self):
        """The GstPlayer object used

        :return: player object
        :rtype: GstPlayer
        """
        return self._player

    @player.setter  # type: ignore
    def player(self, player):
        """Set the GstPlayer object used

        :param GstPlayer player: The GstPlayer to use
        """
        if (player is None
                or (self._player is not None
                    and self._player != player)):
            return

        self._player = player
        self._progress_scale.props.player = self._player

        self._player.connect('song-changed', self._update_view)
        self._player.connect(
            "notify::repeat-mode", self._on_repeat_mode_changed)
        self._player.connect('notify::state', self._sync_playing)
        self._repeat_mode_button.props.player = self._player

        self._player.bind_property(
            "volume", self._volume_button, "volume",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)

        self._player.bind_property(
            "mute", self._volume_button, "mute",
            GObject.BindingFlags.BIDIRECTIONAL
            | GObject.BindingFlags.SYNC_CREATE)
        self._update_view(self._player)

    @Gtk.Template.Callback()
    def _on_progress_value_changed(self, progress_scale):
        seconds = int(progress_scale.get_value() / 60)
        self._progress_time_label.set_label(utils.seconds_to_string(seconds))

    @Gtk.Template.Callback()
    def _on_prev_button_clicked(self, button):
        self._player.previous()

    @Gtk.Template.Callback()
    def _on_play_button_clicked(self, button):
        self._player.play_pause()

    @Gtk.Template.Callback()
    def _on_next_button_clicked(self, button):
        self._player.next()

    def _sync_playing(self, player, state):
        if (self._player.props.state == Playback.STOPPED
                and not self._player.props.has_next
                and not self._player.props.has_previous):
            self.props.revealed = True
            return

        self.props.revealed = True

        if self._player.props.state == Playback.PLAYING:
            icon_name = "media-playback-pause-symbolic"
            tooltip = _("Pause")
        else:
            icon_name = "media-playback-start-symbolic"
            tooltip = _("Play")

        if self._play_pause_image.props.icon_name != icon_name:
            self._play_pause_image.props.icon_name = icon_name

        self._play_button.set_tooltip_text(tooltip)

    def _sync_prev_next(self):
        self._next_button.props.sensitive = self._player.props.has_next
        self._prev_button.props.sensitive = self._player.props.has_previous

    def _update_view(self, player):
        """Update all visual elements on song change

        :param Player player: The main player object
        """
        coresong = player.props.current_song
        if coresong is None:
            self._title_label.set_label(_("Nothing Playing"))
            self._artist_label.set_label(_("Choose a track from your library"))
            self._duration_label.set_label("0:00")
            self._progress_time_label.set_label("0:00")
            self._play_button.set_sensitive(False)
            self._sync_prev_next()
            return
        self._duration_label.props.label = utils.seconds_to_string(
            coresong.props.duration)
        self._progress_time_label.props.label = "0:00"

        self._play_button.set_sensitive(True)
        self._sync_prev_next()

        artist = coresong.props.artist
        title = coresong.props.title

        self._title_label.props.label = title
        self._artist_label.props.label = artist

        self._tooltip.props.title = title
        self._tooltip.props.subtitle = artist


    @Gtk.Template.Callback()
    def _on_tooltip_query(self, widget, x, y, kb, tooltip, data=None):
        tooltip.set_custom(self._tooltip)

        return True

    def _on_repeat_mode_changed(
            self, player: Player, pspec: GObject.ParamSpec) -> None:
        self._sync_prev_next()
