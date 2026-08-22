"""Thin Gtk.TextView presentation adapter for Graphium.

Line numbers use Gtk.TextView's native LEFT border window and draw only logical lines
intersecting the visible rectangle. Font/zoom use a view-local CSS provider. No document
state, history, background index or source-view dependency belongs here.
"""
from __future__ import annotations

import gi
gi.require_version("Gtk", "3.0")
gi.require_version("Pango", "1.0")
from gi.repository import Gtk, Pango


MIN_ZOOM_PERCENT = 50
MAX_ZOOM_PERCENT = 300
ZOOM_STEP_PERCENT = 10


class GraphiumTextView(Gtk.TextView):
    GUTTER_PADDING_LEFT = 4
    GUTTER_PADDING_RIGHT = 6

    def __init__(self) -> None:
        super().__init__()
        self._line_numbers_visible = False
        self._gutter_digits = 0
        self._base_font_family = "Monospace"
        self._base_font_size_points = 11.0
        self._zoom_percent = 100
        self._font_provider = Gtk.CssProvider()

        self.set_monospace(True)
        self.set_left_margin(6)
        self.set_right_margin(6)
        self.get_style_context().add_class("graphium-editor-view")
        self.get_style_context().add_provider(
            self._font_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
        self.get_buffer().connect("changed", self._on_buffer_changed)
        self._apply_font_css()

    @property
    def line_numbers_visible(self) -> bool:
        return self._line_numbers_visible

    @property
    def zoom_percent(self) -> int:
        return self._zoom_percent

    @property
    def base_font(self) -> tuple[str, float]:
        return self._base_font_family, self._base_font_size_points

    def set_line_numbers_visible(self, visible: bool) -> None:
        visible = bool(visible)
        if visible == self._line_numbers_visible:
            return
        self._line_numbers_visible = visible
        if visible:
            self._sync_gutter_width(force=True)
        else:
            self.set_border_window_size(Gtk.TextWindowType.LEFT, 0)
        self.queue_draw()

    def set_base_font(self, family: str, size_points: float) -> None:
        family = str(family).strip()
        size_points = float(size_points)
        if not family:
            raise ValueError("font family must not be empty")
        if size_points <= 0:
            raise ValueError("font size must be positive")
        self._base_font_family = family
        self._base_font_size_points = size_points
        self._apply_font_css()

    def set_zoom_percent(self, percent: int) -> None:
        percent = int(percent)
        percent = min(MAX_ZOOM_PERCENT, max(MIN_ZOOM_PERCENT, percent))
        if percent == self._zoom_percent:
            return
        self._zoom_percent = percent
        self._apply_font_css()

    def zoom_in(self) -> int:
        self.set_zoom_percent(self._zoom_percent + ZOOM_STEP_PERCENT)
        return self._zoom_percent

    def zoom_out(self) -> int:
        self.set_zoom_percent(self._zoom_percent - ZOOM_STEP_PERCENT)
        return self._zoom_percent

    def reset_zoom(self) -> int:
        self.set_zoom_percent(100)
        return self._zoom_percent

    @staticmethod
    def _css_quote(value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _apply_font_css(self) -> None:
        effective = self._base_font_size_points * self._zoom_percent / 100.0
        family = self._css_quote(self._base_font_family)
        css = (
            '.graphium-editor-view { '
            f'font-family: "{family}"; '
            f'font-size: {effective:.3f}pt; '
            '}\n'
        )
        self._font_provider.load_from_data(css.encode("utf-8"))
        if self._line_numbers_visible:
            self._sync_gutter_width(force=True)
        self.queue_draw()

    def _on_buffer_changed(self, _buffer) -> None:
        if self._line_numbers_visible:
            self._sync_gutter_width(force=False)

    def _sync_gutter_width(self, *, force: bool) -> None:
        line_count = max(1, self.get_buffer().get_line_count())
        digits = len(str(line_count))
        if not force and digits == self._gutter_digits:
            return
        self._gutter_digits = digits
        layout = self.create_pango_layout("9" * digits)
        width, _height = layout.get_pixel_size()
        self.set_border_window_size(
            Gtk.TextWindowType.LEFT,
            self.GUTTER_PADDING_LEFT + width + self.GUTTER_PADDING_RIGHT,
        )

    def do_draw(self, cr):
        result = Gtk.TextView.do_draw(self, cr)
        if not self._line_numbers_visible:
            return result
        left = self.get_window(Gtk.TextWindowType.LEFT)
        if left is None or not Gtk.cairo_should_draw_window(cr, left):
            return result
        cr.save()
        try:
            Gtk.cairo_transform_to_window(cr, self, left)
            self._draw_visible_line_numbers(cr)
        finally:
            cr.restore()
        return result

    def _draw_visible_line_numbers(self, cr) -> None:
        visible = self.get_visible_rect()
        result = self.get_line_at_y(visible.y)
        it = result[0] if isinstance(result, tuple) else result
        it.set_line_offset(0)
        visible_bottom = visible.y + visible.height

        context = self.get_style_context()
        layout = self.create_pango_layout("")
        layout.set_alignment(Pango.Alignment.RIGHT)
        width = self.get_border_window_size(Gtk.TextWindowType.LEFT)

        # Viewport-bounded iteration only. Wrapped display-line
        # continuations intentionally receive no additional logical line number.
        while True:
            line_y, line_height = self.get_line_yrange(it)
            if line_y > visible_bottom:
                break
            if line_y + line_height >= visible.y:
                layout.set_text(str(it.get_line() + 1), -1)
                text_w, text_h = layout.get_pixel_size()
                _wx, window_y = self.buffer_to_window_coords(
                    Gtk.TextWindowType.LEFT, 0, line_y
                )
                x = max(
                    self.GUTTER_PADDING_LEFT,
                    width - self.GUTTER_PADDING_RIGHT - text_w,
                )
                y = window_y + max(0, min(2, (line_height - text_h) // 2))
                Gtk.render_layout(context, cr, x, y, layout)
            if not it.forward_line():
                break
