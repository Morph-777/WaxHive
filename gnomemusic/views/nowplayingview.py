# Copyright 2026 The GNOME Music developers
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from gettext import gettext as _
from gi.repository import Adw, GObject

from gnomemusic.widgets.nowplayingpanel import NowPlayingPanel


class NowPlayingView(Adw.Bin):
    __gtype_name__ = "NowPlayingView"
    title = GObject.Property(type=str, default=_("Now Playing"))
    icon_name = GObject.Property(
        type=str, default="media-playback-start-symbolic")

    def __init__(self, application):
        super().__init__(name="now-playing")
        clamp = Adw.Clamp(maximum_size=720)
        clamp.set_child(NowPlayingPanel(application))
        self.set_child(clamp)
