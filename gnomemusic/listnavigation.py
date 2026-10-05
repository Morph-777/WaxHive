# Copyright 2026 The GNOME Music developers
# SPDX-License-Identifier: GPL-2.0-or-later WITH GStreamer-exception-2008

from gi.repository import GLib, Gtk


def item_title(item):
    """Read the displayed name from a model item or a bound row."""
    for prop in ("coresong", "corealbum", "playlist"):
        if item.find_property(prop):
            bound = getattr(item.props, prop)
            if bound is not None and bound is not item:
                return item_title(bound)
    for prop in ("title", "artist"):
        if item.find_property(prop):
            return getattr(item.props, prop) or ""
    if isinstance(item, Gtk.Widget):
        child = item.get_first_child()
        while child:
            title = item_title(child)
            if title:
                return title
            child = child.get_next_sibling()
    return ""


class ListNavigation:
    """Shared prefix navigation without activating a song or opening search."""

    def __init__(self):
        self._list = None
        self._prefix = ""
        self._time = 0

    def handle(self, focus, character):
        widget = focus
        while widget and not isinstance(widget, (Gtk.ListView, Gtk.GridView, Gtk.ListBox)):
            if isinstance(widget, Gtk.Editable):
                return False
            widget = widget.get_parent()
        if widget is None:
            return False
        now = GLib.get_monotonic_time()
        character = character.casefold()
        if widget is not self._list or now - self._time > 1000000 or self._prefix == character:
            self._prefix = character
        else:
            self._prefix += character
        self._list, self._time = widget, now

        if isinstance(widget, (Gtk.ListView, Gtk.GridView)):
            model = widget.get_model()
            rows = [model.get_item(i) for i in range(model.get_n_items())]
            current = next((i for i in range(len(rows)) if model.is_selected(i)), -1)
        else:
            rows = []
            row = widget.get_first_child()
            while row:
                if isinstance(row, Gtk.ListBoxRow):
                    rows.append(row)
                row = row.get_next_sibling()
            # Tracks span several disc list boxes in the album workspace.
            # Navigate that whole visible workspace, rather than one disc.
            ancestor = widget.get_parent()
            while ancestor and type(ancestor).__name__ != "ArtistAlbumsWidget":
                ancestor = ancestor.get_parent()
            if rows and rows[0].find_property("coresong") and ancestor:
                rows = []

                def collect(parent):
                    child = parent.get_first_child()
                    while child:
                        if child.find_property("coresong"):
                            rows.append(child)
                        else:
                            collect(child)
                        child = child.get_next_sibling()

                collect(ancestor)
            selected = widget.get_selected_row()
            current = next((i for i, row in enumerate(rows)
                            if row == selected or focus == row or focus.is_ancestor(row)), -1)
        for step in range(1, len(rows) + 1):
            index = (current + step) % len(rows)
            if item_title(rows[index]).casefold().startswith(self._prefix):
                if isinstance(widget, (Gtk.ListView, Gtk.GridView)):
                    model.select_item(index, True)
                    widget.scroll_to(index, Gtk.ListScrollFlags.FOCUS, None)
                else:
                    rows[index].get_parent().select_row(rows[index])
                    rows[index].grab_focus()
                break
        return True
